from django import forms
from django.db import models

class ArchivoClasificacion(models.Model):
    archivo = models.FileField(upload_to='archivos_xml/')
    cargado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Archivo {self.archivo.name} cargado en {self.cargado_en}'

