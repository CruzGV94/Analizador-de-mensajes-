from django import forms


class CargarArchivoForm(forms.Form):
    archivo = forms.FileField(label="Selecciona un archivo XML")
    
class CargarArchivoPruebForm(forms.Form):
    archivo = forms.FileField(label="Selecciona un archivo XML")