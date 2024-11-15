
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from xml.etree import ElementTree as ET

from webapp.ListaEnlazada import ListaEnlazadaArchivos
from .forms import CargarArchivoForm
import requests

lista_archivos = ListaEnlazadaArchivos()
def bienvenido(request):
    return render(request, 'bienvenido.html')

def despedida(request):
    return HttpResponse("Hasta luego, nos vemos en la próxima ocasión!")


def cargar_archivo(request):
    if request.method == 'POST':
        form = CargarArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            archivos = request.FILES.getlist('archivo')
            
            url_flask = 'http://127.0.0.1:5000/procesar_datos'
            resultados = []
            contenidos = []

            # Enviar cada archivo directamente a la API de Flask
            for archivo in archivos:
                archivo_para_enviar = {'archivo': archivo}
                respuesta = requests.post(url_flask, files=archivo_para_enviar)

                if respuesta.status_code == 201:
                    resultados_api = respuesta.json().get('resultados', []) # Obtener los resultados de la API
                    for resultado in resultados_api:
                        if 'contenido_xml' in resultado:
                            lista_archivos.agregar_archivo(resultado['contenido_xml'])  # Guardar el contenido del archivo procesado
                            contenidos.append(resultado['contenido_xml'])  # Guardar el contenido en una lista para mostrarlo
                        resultados.append(f"{resultado['archivo']}: {resultado['mensaje']}")
                else:
                    resultados.append(f"Error al procesar el archivo {archivo.name}")
            
            contenidos = lista_archivos.obtener_contenidos()
            
            return render(request, 'bienvenido.html', {
                'contenido_archivo': contenidos,  # Mostrar los contenidos de todos los archivos procesados
                'mensaje': ' | '.join(resultados)  # Mostrar los resultados de los archivos
            })

        else:
            return HttpResponse("Error al procesar el formulario", status=400)

    else:
        form = CargarArchivoForm()

    return render(request, 'cargar_archivo.html', {'form': form}) 



#----------------------------------------------archivo de salida-----------------------------------------------------
#recibir la respuesta de la API de Flask y mostrarla en el frontend    
def mostrar_respuesta(request):
    xml_respuesta = ""
    mensaje = ""

    if request.method == 'POST' or request.method == 'GET':
        opcion = request.POST.get('select')

        # Opción: Consultar datos
        if opcion == 'consultar_datos':
            try:
                response = requests.get('http://127.0.0.1:5000/enviar_respuesta')
                response.raise_for_status()
                if response.status_code == 200:
                    xml_respuesta = response.text
                    mensaje = "Datos consultados correctamente."
                else:
                    mensaje = "Error al obtener el archivo."
            except Exception as e:
                mensaje = f"Error: {str(e)}"
            # Se retorna al formulario con los datos consultados
            return render(request, 'bienvenido.html', {'xml_respuesta': xml_respuesta, 'mensaje': mensaje})

#----------------------------------------------Opción: Resumen de clasificación por fecha (redirecciona al formulario)
        elif opcion == 'resumen_clasificacion_fechas':
            return render(request, 'formulario_filtro.html')

        # Opción: Filtrar información por fecha
        elif opcion == 'filtrar_por_fecha':
            fecha = request.POST.get('fecha')
            empresa = request.POST.get('empresa') or "todas"

            # Preparar la solicitud para Flask
            url_flask = 'http://127.0.0.1:5000/filtrar_por_fecha'
            payload = {
                'fecha': fecha,
                'empresa': empresa
            }
            
            try:
                response = requests.post(url_flask, json=payload)
                data = response.json()
                
                if response.status_code == 200:
                    return render(request, 'resumen.html', {
                        'total_mensajes': data['total_mensajes'],
                        'positivos': data['positivos'],
                        'negativos': data['negativos'],
                        'neutros': data['neutros'],
                        'fecha': fecha,
                        'empresa': empresa,
                    })
                else:
                    error_message = data.get('error', 'Error al generar el resumen')
                    return render(request, 'formulario_filtro.html', {
                        'error': error_message,
                    })
            except requests.exceptions.RequestException as e:
                return JsonResponse({'error': f'Error de conexión: {str(e)}'}, status=500)
            
#----------------------------------------------------- Opción: Resumen por rango de fechas (redirecciona al formulario)
        elif opcion == 'resumen_rango_fecha':
            return render(request, 'formulario_rango_fecha.html')
        
        # Opción: Filtrar información por rango de fechas
        elif opcion == 'filtrar_por_rango_fecha':
            fecha_inicio = request.POST.get('fecha_inicio')
            fecha_fin = request.POST.get('fecha_fin')
            empresa = request.POST.get('empresa', '')

            payload = {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'empresa': empresa
            }

            try:
                response = requests.post('http://127.0.0.1:5000/filtrar_por_rango', json=payload)
                data = response.json()
                print("Informacion recibida desde back: ", data)

                if response.status_code == 200:
                    return render(request, 'resumen_rango_fecha.html', {'resultados': data['resultados'], 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'empresa': empresa})
                else:
                    error_message = data.get('mensaje', 'Error al generar el resumen')
                    return render(request, 'formulario_rango_fecha.html', {'error': error_message})

            except requests.exceptions.RequestException as e:
                return JsonResponse({'error': f'Error de conexión: {str(e)}'}, status=500)


#------------------------------------------------------ Opción: Reporte en PDF
        if opcion == 'reporte_pdf':
            response = requests.post('http://127.0.0.1:5000/generar_pdf')

            #print("Estado de la respuesta:", response.status_code)  # Depuración
            #print("Contenido de la respuesta:", response.text)  # Imprime el contenido

            if response.status_code == 200:
                pdf_base64 = response.json().get('pdf')
                return render(request, 'mostrar_pdf.html', {'pdf_data': pdf_base64})
            else:
                error_message = response.json().get('mensaje', 'Error al generar el reporte')
                return render(request, 'mostrar_pdf.html', {'error': error_message})
            
#-------------------------------------------------Prueba de mensaje -----------------------------------------------------
    # Opción: Prueba de mensaje
    
    
    
    # Si no se seleccionó una opción o no es POST, se retorna al formulario inicial
    return render(request, 'bienvenido.html', {'xml_respuesta': xml_respuesta, 'mensaje': mensaje})


#----------------------------------------------Recetear informacion-----------------------------------------------------
def resetear_bd(request):
    if request.method == 'POST':
        # URL del backend Flask
        url_flask = 'http://127.0.0.1:5000/resetear'
        
        try:
            # Enviar la solicitud POST a Flask
            response = requests.post(url_flask)
            response_data = response.json()
            
            # Verificar si el reseteo fue exitoso
            if response.status_code == 200 and response_data.get("status") == "success":
                
                # Redirigir con un mensaje de éxito
                lista_archivos.vaciar()
                return render(request, 'bienvenido.html', {
                    "xml_respuesta": "",
                    "mensaje": "Base de datos reseteada correctamente"})
            else:
                # Manejar error
                return JsonResponse({"message": "Error al resetear la base de datos"}, status=500)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"message": f"Error al conectar con Flask: {str(e)}"}, status=500)
    
    return render(request, 'bienvenido.html')

        
#-----------------------------------------mostrar datos-----------------------------------------------------

def mostrar_datos(request):
    opcion = request.POST.get('select')
    if opcion == 'datos_estudiante':
        return render(request, 'datos_estudiante.html')
    
    elif opcion == 'documentacion':
        try:
            response = requests.post('http://127.0.0.1:5000/documentacion')

            # Verificar el contenido de la respuesta
            if response.status_code == 200:
                try:
                    data = response.json()  # Intentar decodificar JSON
                    pdf_base64 = data.get('pdf')
                    return render(request, 'mostrar_pdf_documentacio.html', {'pdf_data': pdf_base64})
                except ValueError:
                   
                    return render(request, 'mostrar_pdf_documentacio.html', {'error': 'Respuesta inválida del servidor.'})
            else:
                
                error_message = response.json().get('mensaje', 'Error desconocido')
                return render(request, 'mostrar_pdf_documentacio.html', {'error': error_message})
        except requests.exceptions.RequestException as e:
            # Si ocurre un error de conexión
            return render(request, 'mostrar_pdf_documentacio.html', {'error': f'Error de conexión: {str(e)}'})