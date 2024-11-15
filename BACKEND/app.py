import base64
from datetime import datetime
from io import BytesIO
import os
import re
from flask import Flask, Response, request, jsonify
import xml.etree.ElementTree as ET
from xml.dom import minidom
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from unidecode import unidecode

app = Flask(__name__)

@app.route('/procesar_datos', methods=['POST'])
def procesar_datos():
    if 'archivo' not in request.files:
        return jsonify({'mensaje': 'No se encontró ningún archivo en la solicitud'}), 400

    archivos = request.files.getlist('archivo')  # Obtener lista de archivos

    if len(archivos) == 0:
        return jsonify({'mensaje': 'No se ha seleccionado ningún archivo'}), 400

    resultados = []
    
    for archivo in archivos:
        if archivo.filename == '':
            resultados.append({'archivo': archivo.filename, 'mensaje': 'Archivo sin nombre'})
            continue
        
        try:
            print("Comenzando el procesamiento del archivo...")
            contenido = archivo.read().decode('utf-8')
            print(f"Contenido del archivo: {contenido}")

            # Procesar el contenido del archivo
            root = ET.fromstring(contenido)
            print(f"Elemento raíz: {root.tag}")

            # Extraer datos del archivo
            diccionario = extraer_datos_xml(root)
            data = extraer_datos_xml(root)
            print(f"Diccionario extraído: {diccionario}")

            if diccionario is None:
                resultados.append({'archivo': archivo.filename, 'mensaje': 'Error al procesar el archivo'})
                continue  # Si hay un error en este archivo, pasa al siguiente
            guardar_datos_xml(data)
            print("Guardando datos XML...")
            generar_respuesta_xml(diccionario) 
            print("Generando respuesta XML...")

            resultados.append({
                'archivo': archivo.filename, 
                'mensaje': 'Archivo procesado exitosamente',
                'contenido_xml': contenido  # Aquí se incluye el contenido XML para enviarlo al frontend
            })
            
        except ET.ParseError:
            resultados.append({'archivo': archivo.filename, 'mensaje': 'Error al procesar el archivo'})
        except Exception as e:
            print(f"Error en procesar_datos: {e}")
            resultados.append({'archivo': archivo.filename, 'mensaje': 'Error inesperado'})

    return jsonify({'resultados': resultados}), 201


#-----------------------------------------------base de datos--------------------------------------------------------
def guardar_datos_xml(data):
    try:
        # Abrir el archivo existente o crear uno nuevo si no existe
        try:
            tree = ET.parse("base_datos.xml")
            solicitud_clasificacion = tree.getroot()
        except FileNotFoundError:
            solicitud_clasificacion = ET.Element("solicitud_clasificacion")
            
        #diccionario = extraer_datos_xml(data)
        diccionario = solicitud_clasificacion.find("diccionario")
        if diccionario is None:
            diccionario = ET.SubElement(solicitud_clasificacion, "diccionario")

        # Sentimientos positivos
        sentimientos_positivos = diccionario.find("sentimientos_positivos")
        if sentimientos_positivos is None:
            sentimientos_positivos = ET.SubElement(diccionario, "sentimientos_positivos")
        for palabra in data['sentimientos_positivos']:
            palabra_elemento = ET.SubElement(sentimientos_positivos, "palabra")
            palabra_elemento.text = palabra

        # Sentimientos negativos
        sentimientos_negativos = diccionario.find("sentimientos_negativos")
        if sentimientos_negativos is None:
            sentimientos_negativos = ET.SubElement(diccionario, "sentimientos_negativos")
        for palabra in data['sentimientos_negativos']:
            palabra_elemento = ET.SubElement(sentimientos_negativos, "palabra")
            palabra_elemento.text = palabra

        # Empresas a analizar
        empresas_analizar = diccionario.find("empresas_analizar")
        if empresas_analizar is None:
            empresas_analizar = ET.SubElement(diccionario, "empresas_analizar")

        for empresa in data['empresas']:
            empresa_element = ET.SubElement(empresas_analizar, "empresa")
            nombre_empresa_elemento = ET.SubElement(empresa_element, "nombre")
            nombre_empresa_elemento.text = empresa['nombre']

            servicios_elemento = ET.SubElement(empresa_element, "servicios")
            for servicio in empresa['servicios']:
                servicio_elemento = ET.SubElement(servicios_elemento, "servicio", nombre=servicio['nombre'])
                for alias in servicio['alias']:
                    alias_elemento = ET.SubElement(servicio_elemento, "alias")
                    alias_elemento.text = alias

        # Agregar lista de mensajes
        lista_mensajes_element = solicitud_clasificacion.find("lista_mensajes")
        if lista_mensajes_element is None:
            lista_mensajes_element = ET.SubElement(solicitud_clasificacion, "lista_mensajes")

        for mensaje in data['mensajes']:
            mensaje_element = ET.SubElement(lista_mensajes_element, "mensaje")
            mensaje_element.text = mensaje

        # Convertir a cadena XML bonita
        xml_string = ET.tostring(solicitud_clasificacion, encoding='utf-8', method='xml')
        parsed_xml = minidom.parseString(xml_string)
        pretty_xml_as_string = parsed_xml.toprettyxml(indent="  ")
        pretty_xml_as_string = "\n".join(line for line in pretty_xml_as_string.splitlines() if line.strip())

        # Guardar o sobrescribir el archivo con los nuevos datos
        with open("base_datos.xml", "w", encoding='utf-8') as f:
            f.write(pretty_xml_as_string)
            print("Base de datos actualizada exitosamente")
        return "Archivo guardado exitosamente"

    except Exception as e:
        print(f"Error al guardar el archivo XML: {e}")
        return "Error al guardar el archivo XML"


#-----------------------------------------------extraer datos xml--------------------------------------------------------
def extraer_datos_xml(root):
    data = {
        'sentimientos_positivos': [],
        'sentimientos_negativos': [],
        'empresas': [],
        'mensajes': []           
    }     

    try:
        # Extraer sentimientos positivos
        sentimientos_positivos = root.find('.//sentimientos_positivos')
        if sentimientos_positivos is not None:
            for palabra in sentimientos_positivos.findall('palabra'):
                if palabra.text:
                    data['sentimientos_positivos'].append(palabra.text.strip())

        # Extraer sentimientos negativos
        sentimientos_negativos = root.find('.//sentimientos_negativos')
        if sentimientos_negativos is not None:
            for palabra in sentimientos_negativos.findall('palabra'):
                if palabra.text:
                    data['sentimientos_negativos'].append(palabra.text.strip())

        # Extraer empresas
        for empresa in root.findall('.//empresa'):
            nombre_empresa = empresa.find('nombre').text.strip() if empresa.find('nombre') is not None else ''
            servicios = []
            # Cambiar el recorrido para obtener los nodos de servicio
            for servicio in empresa.findall('servicios/servicio'):
                nombre_servicio = servicio.attrib.get('nombre', '')
                alias = [alias.text.strip() for alias in servicio.findall('alias') if alias.text]
                servicios.append({'nombre': nombre_servicio, 'alias': alias})
            data['empresas'].append({'nombre': nombre_empresa, 'servicios': servicios})

        # Extraer mensajes
        for mensaje in root.findall('.//mensaje'):
            if mensaje.text:
                data['mensajes'].append(mensaje.text.strip())

        return data
    except Exception as e:
        print(f"Error al procesar el XML: {e}")
        return None



#----------------------------------------extraar fecha-----------------------------------------------------------------
def extraer_fecha(mensaje):
    fecha_patron = r"Lugar y fecha:\s+[A-Za-z]+,\s+(\d{2}/\d{2}/\d{4})" # Expresión regular para extraer la fecha
    coincidencia = re.search(fecha_patron, mensaje) # Buscar coincidencias en el mensaje
    
    if coincidencia:
        return coincidencia.group(1)
    else:
        return None

#----------------------------------------------generar respuesta--------------------------------------------------------
# Variables acumulativas para los totales
totales_acumulados = {
    'total_mensajes': 0,
    'positivos': 0,
    'negativos': 0,
    'neutros': 0
}

def generar_respuesta_xml(diccionario):
    global totales_acumulados
    print("Iniciando generación de respuesta XML")
    
    
    try:
        
        tree = ET.parse('base_datos.xml') 
        root = tree.getroot()

       
        resultados_por_fecha = {}

        # Recorrer los mensajes
        for mensaje in root.findall('.//mensaje'):
            texto_mensaje = mensaje.text
            fecha = extraer_fecha(texto_mensaje)  
            
            # Si no hay fecha en el mensaje, continuar
            if not fecha:
                continue
            
            # Contar los sentimientos
            """if es_positivo(texto_mensaje, diccionario):
                sentimiento = 'positivo'
                totales_acumulados['positivos'] += 1
            elif es_negativo(texto_mensaje, diccionario):
                sentimiento = 'negativo'
                totales_acumulados['negativos'] += 1
            else:
                sentimiento = 'neutro'
                totales_acumulados['neutros'] += 1"""
                
            sentimiento = clasificar_sentimiento(texto_mensaje, diccionario)
            
            # Agregar resultados al diccionario por fecha
            if fecha not in resultados_por_fecha:
                resultados_por_fecha[fecha] = {
                    'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0,
                    'empresas': {}
                }
            
            resultados_por_fecha[fecha]['total'] += 1
            if sentimiento == 'positivo':
                resultados_por_fecha[fecha]['positivos'] += 1
            elif sentimiento == 'negativo':
                resultados_por_fecha[fecha]['negativos'] += 1
            else:
                resultados_por_fecha[fecha]['neutros'] += 1

            # Actualizar el análisis de empresas y servicios
            for empresa in diccionario['empresas']:
                nombre_empresa = normalizar_texto(empresa['nombre'])
                if nombre_empresa not in resultados_por_fecha[fecha]['empresas']:
                    resultados_por_fecha[fecha]['empresas'][nombre_empresa] = {
                        'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0,
                        'servicios': {}
                    }
                
                resultados_por_fecha[fecha]['empresas'][nombre_empresa]['total'] += 1

                # Contar sentimientos por empresa
                if sentimiento == 'positivo':
                    resultados_por_fecha[fecha]['empresas'][nombre_empresa]['positivos'] += 1
                elif sentimiento == 'negativo':
                    resultados_por_fecha[fecha]['empresas'][nombre_empresa]['negativos'] += 1
                else:
                    resultados_por_fecha[fecha]['empresas'][nombre_empresa]['neutros'] += 1

                # Contar por servicios
                for servicio in empresa['servicios']:
                    nombre_servicio = normalizar_texto(servicio['nombre'])
                    if nombre_servicio not in resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios']:
                        resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios'][nombre_servicio] = {
                            'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0
                        }

                    resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios'][nombre_servicio]['total'] += 1

                    # Asignar sentimientos
                    if sentimiento == 'positivo':
                        resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios'][nombre_servicio]['positivos'] += 1
                    elif sentimiento == 'negativo':
                        resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios'][nombre_servicio]['negativos'] += 1
                    else:
                        resultados_por_fecha[fecha]['empresas'][nombre_empresa]['servicios'][nombre_servicio]['neutros'] += 1
                        
                        print(f"Mensaje procesado: {texto_mensaje}", "Fecha: ", fecha, "Sentimiento: ", sentimiento)

        # Crear o abrir el archivo existente
        if os.path.exists("respuesta.xml") and os.path.getsize("respuesta.xml") > 0:
            try:
                tree = ET.parse("respuesta.xml")
                lista_respuestas = tree.getroot()
                lista_respuestas.clear()  # Eliminar respuestas anteriores
            except ET.ParseError:
                print("Archivo XML corrupto, creando uno nuevo.")
                lista_respuestas = ET.Element("lista_respuestas")
        else:
            lista_respuestas = ET.Element("lista_respuestas")

        # Generar respuestas para cada fecha
        for fecha, resultados in resultados_por_fecha.items():
            respuesta = ET.SubElement(lista_respuestas, "respuesta")
            fecha_element = ET.SubElement(respuesta, "fecha")
            fecha_element.text = fecha
            
            mensajes_element = ET.SubElement(respuesta, "mensajes")
            ET.SubElement(mensajes_element, "total").text = str(resultados['total'])
            ET.SubElement(mensajes_element, "positivos").text = str(resultados['positivos'])
            ET.SubElement(mensajes_element, "negativos").text = str(resultados['negativos'])
            ET.SubElement(mensajes_element, "neutros").text = str(resultados['neutros'])

            analisis_element = ET.SubElement(respuesta, "analisis")
            for nombre_empresa, datos_empresa in resultados['empresas'].items():
                empresa_element = ET.SubElement(analisis_element, "empresa", nombre=nombre_empresa)
                
                mensajes_empresa_element = ET.SubElement(empresa_element, "mensajes")
                ET.SubElement(mensajes_empresa_element, "total").text = str(datos_empresa['total'])
                ET.SubElement(mensajes_empresa_element, "positivos").text = str(datos_empresa['positivos'])
                ET.SubElement(mensajes_empresa_element, "negativos").text = str(datos_empresa['negativos'])
                ET.SubElement(mensajes_empresa_element, "neutros").text = str(datos_empresa['neutros'])

                servicios_element = ET.SubElement(empresa_element, "servicios")
                for nombre_servicio, datos_servicio in datos_empresa['servicios'].items():
                    servicio_element = ET.SubElement(servicios_element, "servicio", nombre=nombre_servicio)
                    
                    mensajes_servicio_element = ET.SubElement(servicio_element, "mensajes")
                    ET.SubElement(mensajes_servicio_element, "total").text = str(datos_servicio['total'])
                    ET.SubElement(mensajes_servicio_element, "positivos").text = str(datos_servicio['positivos'])
                    ET.SubElement(mensajes_servicio_element, "negativos").text = str(datos_servicio['negativos'])
                    ET.SubElement(mensajes_servicio_element, "neutros").text = str(datos_servicio['neutros'])

        # Convertir el árbol XML a cadena formateada
        xml_string = ET.tostring(lista_respuestas, encoding='utf-8', method='xml')
        parsed_xml = minidom.parseString(xml_string)
        pretty_xml_as_string = parsed_xml.toprettyxml(indent="  ")
        pretty_xml_as_string = "\n".join(line for line in pretty_xml_as_string.splitlines() if line.strip())

        # Guardar el archivo
        with open("respuesta.xml", "w", encoding='utf-8') as f:
            f.write(pretty_xml_as_string)
            print("Respuesta XML generada exitosamente")
        return "Archivo guardado exitosamente"

    except ET.ParseError as parse_error:
        print(f"Error de análisis XML: {parse_error}")
        return "Error al analizar el archivo XML"
    except Exception as e:
        print(f"Error al generar la respuesta XML: {e}")
        return "Error al generar la respuesta XML"
    


"""def es_positivo(mensaje, diccionario):
    #palabras = mensaje.lower().split()
    palabras = normalizar_texto(mensaje).split() 
    return any(palabra in diccionario['sentimientos_positivos'] for palabra in palabras)

def es_negativo(mensaje, diccionario):
    #palabras = mensaje.lower().split()
    palabras = normalizar_texto(mensaje).split() 
    return any(palabra in diccionario['sentimientos_negativos'] for palabra in palabras)"""

"""def es_positivo(mensaje, diccionario):
    palabras = normalizar_texto(mensaje).split() 
    palabras_positivas = [normalizar_texto(p) for p in diccionario['sentimientos_positivos']]
    return any(palabra in palabras_positivas for palabra in palabras)

def es_negativo(mensaje, diccionario):
    palabras = normalizar_texto(mensaje).split() 
    palabras_negativas = [normalizar_texto(p) for p in diccionario['sentimientos_negativos']]
    return any(palabra in palabras_negativas for palabra in palabras)"""

def clasificar_sentimiento(mensaje, diccionario):
    palabras = normalizar_texto(mensaje).split()
    
    # Contadores para palabras positivas y negativas
    contador_positivos = sum(1 for palabra in palabras if palabra in diccionario['sentimientos_positivos']) # Contar palabras positivas, 1 for es un generador de lista
    contador_negativos = sum(1 for palabra in palabras if palabra in diccionario['sentimientos_negativos'])
    
    # Determinar el sentimiento
    if contador_positivos > contador_negativos:
        return 'positivo'
    elif contador_negativos > contador_positivos:
        return 'negativo'
    else:
        return 'neutro'


def normalizar_texto(texto):
    texto = unidecode(texto)
    # Eliminar caracteres especiales y convertir a minúsculas
    return re.sub(r'[^\w\s]', '', texto).lower()



#----------------------------------------------enviar respuesta a frontend----------------------------------------------
@app.route('/enviar_respuesta', methods=['GET'])
def enviar_respuesta():
    print("Enviando respuesta al frontend")
    try:
        if os.path.exists("respuesta.xml"):
            with open("respuesta.xml", "r", encoding='utf-8') as f:
                contenido = f.read()
            #print(contenido)  # Imprimir para verificar si se está leyendo bien
            return Response(contenido, mimetype='application/xml')
        else:
            return Response("Archivo no encontrado", status=404)
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)
    
#----------------------------------------------resetear base de datos-----------------------------------------------------
@app.route('/resetear', methods=['POST'])
def resetear():
    try:
        resultado = resetear_base_datos()
        return jsonify({"status": "success", "message": resultado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def resetear_base_datos():
    archivos_bd = ['respuesta.xml', 'base_datos.xml']  # Lista de archivos a reiniciar
    elementos_raiz = {
        'respuesta.xml': ET.Element('lista_respuestas'),
        'base_datos.xml': ET.Element('base_datos')
    }
    
    for archivo in archivos_bd:
        try:
            # Obtener el elemento raíz correspondiente
            raiz = elementos_raiz.get(archivo)

            # Crear el árbol de elementos y guardar el archivo
            tree = ET.ElementTree(raiz)
            with open(archivo, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)

            print(f"Base de datos {archivo} reiniciada correctamente.")
        except Exception as e:
            print(f"Error al reiniciar la base de datos {archivo}: {str(e)}")
            return f"Error al reiniciar la base de datos {archivo}: {str(e)}"

    return "Base de datos reiniciada correctamente para ambos archivos."


    
#-------------------------------------------------filtrar por fecha-----------------------------------------------------
@app.route('/filtrar_por_fecha', methods=['POST'])
def filtrar_por_fecha():
    data = request.get_json()
    print(f"Datos recibidos del frontend: {data}")  # Imprime los datos recibidos

    fecha_filtrada = data['fecha']
    fecha_convertida = datetime.strptime(fecha_filtrada, '%Y-%m-%d').strftime('%d/%m/%Y')

    print(f"Fecha filtrada convertida: {fecha_convertida}")  # Imprime la fecha convertida

    try:
        # Cargar el archivo XML que contiene las respuestas
        tree = ET.parse('respuesta.xml')
        root_respuestas = tree.getroot()

        total_mensajes = 0
        positivos = 0
        negativos = 0
        neutros = 0

        # Filtrar respuestas por fecha
        for respuesta in root_respuestas.findall('respuesta'):
            fecha_respuesta = respuesta.find('fecha').text.strip()
            mensajes = respuesta.find('mensajes')

            if fecha_respuesta == fecha_convertida:
                total_mensajes += int(mensajes.find('total').text)
                positivos += int(mensajes.find('positivos').text)
                negativos += int(mensajes.find('negativos').text)
                neutros += int(mensajes.find('neutros').text)

        # Imprimir resultados antes de enviarlos al frontend
        #print(f"Total mensajes: {total_mensajes}, Positivos: {positivos}, Negativos: {negativos}, Neutros: {neutros}")

        if total_mensajes == 0:
            return jsonify({
                'mensaje': 'No se encontraron mensajes para la fecha especificada.',
                'total_mensajes': total_mensajes,
                'positivos': positivos,
                'negativos': negativos,
                'neutros': neutros
            })

        response = {
            'mensaje': f'Mensajes encontrados para la fecha {fecha_filtrada}:',
            'total_mensajes': total_mensajes,
            'positivos': positivos,
            'negativos': negativos,
            'neutros': neutros
        }
        
        print(f"Respuesta enviada al frontend: {response}")  # Imprime la respuesta final

        return jsonify(response)

    except ET.ParseError:
        return jsonify({'error': 'Error al procesar el archivo XML. No se ha enviado ningun mensaje'}), 500
    except Exception as e:
        print(f"Error en el procesamiento: {e}")  # Imprime cualquier error
        return jsonify({'error': str(e)}), 500

#--------------------------------------------------Resumen por rango de fechas-------------------------------------------
@app.route('/filtrar_por_rango', methods=['POST'])
def filtrar_por_rango():
    data = request.get_json()
    print(f"Datos recibidos del frontend: {data}")

    fecha_inicio = data['fecha_inicio']
    fecha_fin = data['fecha_fin']
    empresa = data.get('empresa', 'todas')  # Si 'empresa' no se proporciona, asumimos 'todas'

    # Convertir las fechas al formato deseado
    fecha_inicio_convertida = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
    fecha_fin_convertida = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')

    print(f"Fechas convertidas: {fecha_inicio_convertida} - {fecha_fin_convertida}")

    try:
        # Cargar el archivo XML
        tree = ET.parse('respuesta.xml')
        root_respuestas = tree.getroot()

        print(f"Filtrando respuestas entre: {fecha_inicio_convertida} y {fecha_fin_convertida}")

        # Variables para almacenar los resultados
        resultados = []  # Almacena los mensajes encontrados por fecha

        # Filtrar respuestas por rango de fechas
        for respuesta in root_respuestas.findall('respuesta'):
            fecha_respuesta_text = respuesta.find('fecha').text.strip()

            # Convertir la fecha del XML a objeto datetime
            fecha_respuesta_obj = datetime.strptime(fecha_respuesta_text, '%d/%m/%Y')
            fecha_inicio_obj = datetime.strptime(fecha_inicio_convertida, '%d/%m/%Y')
            fecha_fin_obj = datetime.strptime(fecha_fin_convertida, '%d/%m/%Y')

            # Verificar si fecha_respuesta cae en el rango
            if fecha_inicio_obj <= fecha_respuesta_obj <= fecha_fin_obj:
                print(f"Fecha en rango: {fecha_respuesta_text}")

                # Procesar los datos si están en el rango
                mensajes = respuesta.find('mensajes')

                # Verificar que los mensajes no estén vacíos y acumular
                if mensajes is not None:
                    total = int(mensajes.find('total').text) if mensajes.find('total') is not None else 0
                    positivos = int(mensajes.find('positivos').text) if mensajes.find('positivos') is not None else 0
                    negativos = int(mensajes.find('negativos').text) if mensajes.find('negativos') is not None else 0
                    neutros = int(mensajes.find('neutros').text) if mensajes.find('neutros') is not None else 0

                    # Almacenar el resultado para esa fecha
                    resultados.append({
                        'fecha': fecha_respuesta_text,
                        'total_mensajes': total,
                        'positivos': positivos,
                        'negativos': negativos,
                        'neutros': neutros
                    })
            else:
                print(f"Fecha fuera de rango: {fecha_respuesta_text}")

        # Verificar si se encontraron resultados
        if resultados:
            return jsonify({
                'mensaje': 'Mensajes encontrados en el rango de fechas:',
                'resultados': resultados
            })
        else:
            return jsonify({'mensaje': 'No se encontraron mensajes en el rango de fechas especificado.'}), 404

    except ET.ParseError:
        return jsonify({'error': 'Error al procesar el archivo XML.'}), 500
    except Exception as e:
        print(f"Error en el procesamiento: {e}")
        return jsonify({'error': str(e)}), 500
    
#--------------------------------------------------generar reporte PDF-----------------------------------------------------
@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    try:
        # Leer el archivo XML
        tree = ET.parse('respuesta.xml')
        data = tree.getroot()

        # Crear un buffer para el PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Título del reporte
        p.setFont("Helvetica-Bold", 16)
        p.drawString(72, height - 72, "Reporte de Mensajes")

        # Fecha de generación
        p.setFont("Helvetica", 12)
        p.drawString(72, height - 100, f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d')}")

        # Resumen
        p.drawString(72, height - 130, "Detalles de Mensajes:")

        y_position = height - 150
        # Iterar sobre las respuestas en el XML
        for respuesta in data.findall('respuesta'):
            fecha = respuesta.find('fecha').text
            total = respuesta.find('mensajes/total').text
            positivos = respuesta.find('mensajes/positivos').text
            negativos = respuesta.find('mensajes/negativos').text
            neutros = respuesta.find('mensajes/neutros').text

            line = (f"Fecha: {fecha} | Total: {total} | "
                    f"Positivos: {positivos} | Negativos: {negativos} | "
                    f"Neutros: {neutros}")
            p.drawString(72, y_position, line)
            y_position -= 20  # Espaciado entre líneas

        # Finalizar el PDF
        p.showPage()
        p.save()

        try:
            
            buffer.seek(0)
            # Codificar el PDF a base64
            pdf_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            # Enviar el PDF como respuesta JSON
            response_data = {'pdf': pdf_base64}
            #print("Respuesta JSON:", response_data) 
            return jsonify(response_data)

        except Exception as e:
            #print("Error al generar el PDF:", str(e))  # Manejo de errores
            return jsonify({'mensaje': 'Error al generar el reporte'}), 500

    except Exception as e:
       
        return jsonify({'mensaje': f'Error al generar el reporte: {str(e)}'}), 500
    

#-------------------------------------------enviar documentacion---------------------------------------------------------

@app.route('/documentacion', methods=['POST'])
def documentacion():
    try:
        pdf_path = 'documentacion.pdf'
        if not os.path.exists(pdf_path):
            return jsonify({'mensaje': 'Archivo no encontrado'}), 404

        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
            
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        response_data = {'pdf': pdf_base64}
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'mensaje': f'Error al enviar la documentación: {str(e)}'}), 500




    

if __name__ == '__main__':
  app.run(debug=True)