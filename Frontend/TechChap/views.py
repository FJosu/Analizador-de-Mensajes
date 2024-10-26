from django.shortcuts import render
import requests
from .forms import FileForm

# Create your views here.

endpoint = 'http://localhost:5000/'
def index(request):
    return render(request, 'index.html')


def main(request):
    return render(request, 'main.html')

def studentdata(request):
    return render(request,'studentdata.html')

def uploadfile(request):
    return render(request,'uploadfile.html')

def uploadXML(request):
    if request.method == 'POST':
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['file']
            try:
                # Enviar archivo como binario al backend
                response = requests.post(endpoint + '/upload-file', files={'file': archivo})
                
                # Verificar que la respuesta sea exitosa (código 200)
                if response.status_code == 200:
                    return render(request, 'uploadfile.html', {'mensaje_exito': 'Archivo enviado exitosamente'})
                else:
                    return render(request, 'uploadfile.html', {'mensaje_error': 'Error en el envío al backend'})
            
            except Exception as e:
                return render(request, 'uploadfile.html', {'mensaje_error': f'Error al enviar el archivo: {str(e)}'})
    
    # Renderizar el formulario si no es una solicitud POST o si el formulario no es válido
    return render(request, 'uploadfile.html')