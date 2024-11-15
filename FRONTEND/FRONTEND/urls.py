from django import views
from django.contrib import admin
from django.urls import path

#from FRONTEND.webapp.views import bienvenido
from webapp.views import bienvenido, cargar_archivo, despedida, mostrar_respuesta, resetear_bd, mostrar_datos

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', bienvenido),
    path('despedida.html', despedida),
    #path('cargar_archivo.html', cargar_archivo),
    path('cargar/', cargar_archivo, name='cargar_archivo'),
    path('bienvenido/', bienvenido, name='bienvenido'),  # Nombre de la URL sin .html
    path('mostrar_respuesta/', mostrar_respuesta, name='mostrar_respuesta'),
    path('resetear_bd/', resetear_bd, name='resetear_bd'),
    path('filtrar/', mostrar_respuesta, name='filtrar'),
    #path('cargar_prueba/', cargar_archivo_prueba, name='cargar_prueba'),
    path('datos/', mostrar_datos, name='datos'),
]
