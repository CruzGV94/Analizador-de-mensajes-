class NodoArchivo:
    def __init__(self, contenido):
        self.contenido = contenido
        self.siguiente = None

class ListaEnlazadaArchivos:
    def __init__(self):
        self.cabeza = None

    def agregar_archivo(self, contenido):
        nuevo_nodo = NodoArchivo(contenido)
        if not self.cabeza:
            self.cabeza = nuevo_nodo
        else:
            actual = self.cabeza
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo

    
    def obtener_contenidos(self):
        archivos = ""
        actual = self.cabeza
        while actual:
            archivos += actual.contenido + "\n"  
            actual = actual.siguiente
        return archivos.strip() 
    
    def vaciar(self):
        self.cabeza = None 