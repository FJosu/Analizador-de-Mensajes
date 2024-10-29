from flask import Flask, request, jsonify, send_file
import xml.etree.ElementTree as ET
from collections import defaultdict
import logging
import os
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# Clase para manejar el análisis de mensajes
class AnalizadorSentimientos:
    def __init__(self):
        self.sentimientos_positivos = []
        self.sentimientos_negativos = []
        self.empresas_servicios = {}

    def process_file(self, file):
        try:
            tree = ET.parse(file)
            root = tree.getroot()

            # Procesar el diccionario de sentimientos y empresas
            self.process_dictionary(root.find('diccionario'))
            
            # Procesar y clasificar los mensajes
            mensajes = root.find('lista_mensajes').findall('mensaje')
            analisis_por_fecha = self.process_messages(mensajes)
            
            logging.info("File processed successfully")

            # Generar el XML de salida
            xml_response = self.generate_output_xml(analisis_por_fecha)
            
            # Guardar el archivo XML de salida
            xml_file_path = os.path.join(os.getcwd(), 'resultado_analisis.xml')
            with open(xml_file_path, 'wb') as f:
                f.write(xml_response)

            logging.info(f"XML file saved at: {xml_file_path}")
            return {"status": "success", "file_path": xml_file_path}
        except ET.ParseError:
            logging.error("Invalid XML file")
            return {'error': 'Invalid XML file'}
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return {'error': 'Unexpected error'}

    def process_dictionary(self, diccionario):
        # Obtener sentimientos positivos y negativos
        self.sentimientos_positivos = [p.text.strip().lower() for p in diccionario.find('sentimientos_positivos').findall('palabra')]
        self.sentimientos_negativos = [p.text.strip().lower() for p in diccionario.find('sentimientos_negativos').findall('palabra')]

        # Obtener empresas y sus servicios
        empresas = diccionario.find('empresas_analizar').findall('empresa')
        for empresa in empresas:
            nombre_empresa = empresa.find('nombre').text.strip()
            servicios = empresa.find('servicios').findall('servicio')
            self.empresas_servicios[nombre_empresa] = {}
            for servicio in servicios:
                nombre_servicio = servicio.get('nombre').strip().lower()
                alias_servicios = [alias.text.strip().lower() for alias in servicio.findall('alias')]
                self.empresas_servicios[nombre_empresa][nombre_servicio] = alias_servicios

    def process_messages(self, mensajes):
        analisis_por_fecha = defaultdict(lambda: {
            'mensajes': {'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0},
            'empresas': defaultdict(lambda: {
                'mensajes': {'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0},
                'servicios': defaultdict(lambda: {'total': 0, 'positivos': 0, 'negativos': 0, 'neutros': 0})
            })
        })

        for mensaje in mensajes:
            texto_mensaje = mensaje.text.strip().lower()
            fecha = self.extract_date_from_message(texto_mensaje)
            
            # Inicializar contadores para el mensaje
            positivos, negativos = 0, 0

            # Detectar sentimientos en el mensaje
            for sentimiento in self.sentimientos_positivos:
                if sentimiento in texto_mensaje:
                    positivos += 1
            for sentimiento in self.sentimientos_negativos:
                if sentimiento in texto_mensaje:
                    negativos += 1

            # Clasificar el sentimiento general del mensaje
            if positivos > negativos:
                tipo_sentimiento = 'positivos'
            elif negativos > positivos:
                tipo_sentimiento = 'negativos'
            else:
                tipo_sentimiento = 'neutros'

            analisis_por_fecha[fecha]['mensajes']['total'] += 1
            analisis_por_fecha[fecha]['mensajes'][tipo_sentimiento] += 1

            # Detectar empresas y servicios mencionados
            for empresa, servicios in self.empresas_servicios.items():
                for servicio, alias in servicios.items():
                    if any(a in texto_mensaje for a in alias):
                        analisis_por_fecha[fecha]['empresas'][empresa]['mensajes']['total'] += 1
                        analisis_por_fecha[fecha]['empresas'][empresa]['mensajes'][tipo_sentimiento] += 1
                        analisis_por_fecha[fecha]['empresas'][empresa]['servicios'][servicio]['total'] += 1
                        analisis_por_fecha[fecha]['empresas'][empresa]['servicios'][servicio][tipo_sentimiento] += 1

        return analisis_por_fecha

    def extract_date_from_message(self, mensaje):
        # Buscar la fecha en el formato DD/MM/YYYY utilizando una expresión regular
        fecha_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', mensaje)
        if fecha_match:
            return fecha_match.group(0)  # Retorna la fecha encontrada
        return "Fecha desconocida"

    def generate_output_xml(self, analisis_por_fecha):
        root = ET.Element('lista_respuestas')
        
        for fecha, datos in analisis_por_fecha.items():
            respuesta_elem = ET.SubElement(root, 'respuesta')
            ET.SubElement(respuesta_elem, 'fecha').text = fecha

            # Datos de mensajes totales en la fecha
            mensajes_elem = ET.SubElement(respuesta_elem, 'mensajes')
            for tipo, cantidad in datos['mensajes'].items():
                ET.SubElement(mensajes_elem, tipo).text = str(cantidad)

            # Análisis por empresa y servicio
            analisis_elem = ET.SubElement(respuesta_elem, 'analisis')
            for empresa, empresa_datos in datos['empresas'].items():
                empresa_elem = ET.SubElement(analisis_elem, 'empresa', nombre=empresa)
                
                empresa_mensajes_elem = ET.SubElement(empresa_elem, 'mensajes')
                for tipo, cantidad in empresa_datos['mensajes'].items():
                    ET.SubElement(empresa_mensajes_elem, tipo).text = str(cantidad)

                servicios_elem = ET.SubElement(empresa_elem, 'servicios')
                for servicio, servicio_datos in empresa_datos['servicios'].items():
                    servicio_elem = ET.SubElement(servicios_elem, 'servicio', nombre=servicio)
                    servicio_mensajes_elem = ET.SubElement(servicio_elem, 'mensajes')
                    for tipo, cantidad in servicio_datos.items():
                        ET.SubElement(servicio_mensajes_elem, tipo).text = str(cantidad)

        # Indentación para hacer el XML legible
        ET.indent(root, space="  ", level=0)
        return ET.tostring(root, encoding='utf8', method='xml')

# Instancia del analizador
analizador = AnalizadorSentimientos()

# Endpoint para cargar el archivo XML de sentimientos
@app.route('/upload-sentimientos', methods=['POST'])
def upload_sentimientos():
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        logging.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    result = analizador.process_file(file)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result), 200

@app.route('/get_file', methods=['GET'])
def get_file():
    file_path = 'resultado_analisis.xml'  # Especifica la ruta del archivo XML

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return jsonify({'error': 'File not found'}), 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Error sending file'}), 500

if __name__ == '__main__':
    app.run(debug=True)