from django.shortcuts import render
import requests
from django.http import HttpResponse
from .forms import FileForm


endpoint = 'http://localhost:5000/'
def index(request):
    return render(request, 'index.html')

def main(request):
    return render(request , 'main.html')

def uploadfile(request):
    return render(request, 'uploadfile.html')

def peticion(request):
    return render(request, 'peticion.html')

def consultar(request):
    return render(request, 'consultar.html')

def studentdata(request):
    return render(request, 'studentdata.html')


def bydate(request):
    return render(request, 'bydate.html')

def rangebydate(request):
    return render(request, 'rangebydate.html')

def message(request):
    return render(request,'message.html')

def pdf(request):
    return render(request,'pdf.html')


context = {
    'file_content':None,
    'file_binary':None,
    'mensaje_error': None,
    'mensaje_exito': None,
    'process': None,
    'mensaje':None
}


def index(request):
    return render(request, 'index.html')

def uploadXML(request):
    try:
        if request.method == 'POST':
            form = FileForm(request.POST, request.FILES)
            if form.is_valid():
                archivo = request.FILES['file']
                contenido = archivo.read()
                contenido_xml = contenido.decode('utf-8')
                context['file_content'] = contenido_xml
                context['file_binary'] = contenido
                context['mensaje_exito'] = 'Archivo cargado al sistema'
                return render(request, 'uploadfile.html', context)
    except:
        context['mensaje_error'] = 'Error al cargar el archivo'
        return render(request, 'uploadfile.html', context)
 
def CloseAlerts(request):
    context['mensaje_error'] = None
    context['mensaje_exito'] = None
    return render(request, 'uploadfile.html', context)

def SendXML(request):
    try:
        if request.method == 'POST':
            file = context['file_binary']
            if file is None:
                context['mensaje_exito'] = None
                context['mensaje_error'] = 'El archivo es nulo'
                return render(request, 'uploadfile.html', context)
            
            # Enviar archivo como binario
            response = requests.post(endpoint + '/upload-sentimientos', files={'file': file})
            # Procesar la respuesta
            tempresponse = response.json()

            context['file_binary'] = None
            context['file_content'] = None
            context['mensaje_error'] = None
            context['mensaje_exito'] = "Procesado Éxitosamente"
            return render(request, 'uploadfile.html', context)

    except Exception as e:
        context['mensaje_exito'] = None
        context['mensaje_error'] = f'Error al enviar el archivo: {str(e)}'
        return render(request, 'uploadfile.html', context)


def getFile(request):
    try:
        if request.method == 'GET':
            # Realiza una petición GET al endpoint para obtener el archivo
            response = requests.get(f"{endpoint}/get_file", stream=True)
            
            if response.status_code == 404:
                context['mensaje_error'] = 'Archivo no encontrado en el servidor'
                return render(request, 'consultar.html', context)
            
            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                response_content = response.content
                context['file_content'] = response_content.decode('utf-8') 
                
                return render(request, 'consultar.html', context)
            else:
                context['mensaje_error'] = 'Error al obtener el archivo'
                return render(request, 'consultar.html', context)

    except Exception as e:
        context['mensaje_error'] = f'Error al obtener el archivo: {str(e)}'
        return render(request, 'consultar.html', context)

def delete_file_content(request):
    """
    Método para borrar el contenido de un archivo a través de un endpoint DELETE.
    """
    try:
        # Realizar petición DELETE al endpoint
        response = requests.delete(f"{endpoint}/delete-file")
        
        # Verificar el estado de la respuesta
        if response.status_code == 200:
            context['mensaje_exito'] = 'Contenido del archivo eliminado correctamente'
        elif response.status_code == 404:
            context['mensaje_error'] = 'Archivo no encontrado en el servidor'
        else:
            context['mensaje_error'] = 'Error al intentar eliminar el contenido del archivo'
        
    except Exception as e:
        context['mensaje_error'] = f'Error al conectar con el servidor: {str(e)}'

    return render(request, 'consultar.html', context)


