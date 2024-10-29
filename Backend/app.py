from flask import Flask, request, jsonify, send_file
import xml.etree.ElementTree as ET
from collections import defaultdict
import logging
import os
import re
from flask_cors import CORS
from xml.dom import minidom

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# Clase para manejar el análisis de mensajes
class AnalizadorSentimientos:
    def __init__(self):
        self.sentimientos_positivos = []
        self.sentimientos_negativos = []
        self.empresas_servicios = {}
        self.base_datos_path = 'base_de_datos.xml'
        self.load_existing_data()

    def load_existing_data(self):
        """Carga los datos existentes de base_de_datos.xml si existe."""
        if os.path.exists(self.base_datos_path):
            try:
                tree = ET.parse(self.base_datos_path)
                root = tree.getroot()
                # Procesar el contenido existente según tu lógica
                for respuesta in root.findall('respuesta'):
                    # Aquí puedes agregar lógica para manejar los datos existentes
                    pass
                logging.info("Existing data loaded successfully.")
            except ET.ParseError:
                logging.error("Error parsing existing XML data.")

    def save_to_database(self, analisis_por_fecha):
        """Guarda el análisis en el archivo base_de_datos.xml."""
        if not os.path.exists(self.base_datos_path):
            # Si el archivo no existe, creamos la estructura base
            root = ET.Element('lista_respuestas')
        else:
            # Si ya existe, lo cargamos
            tree = ET.parse(self.base_datos_path)
            root = tree.getroot()

        # Añadir nuevas respuestas al XML
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

        # Guardar cambios en el archivo base_de_datos.xml
        self.pretty_save(root)

    def pretty_save(self, root):
        """Guarda el XML en formato legible."""
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        # Usar minidom para formatear el XML
        parsed = minidom.parseString(xml_str)
        pretty_xml_str = parsed.toprettyxml(indent="  ")

        with open(self.base_datos_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_str)

        logging.info(f"Data saved to database at: {self.base_datos_path}")

    def process_file(self, file):
        try:
            tree = ET.parse(file)
            root = tree.getroot()

            self.process_dictionary(root.find('diccionario'))
            mensajes = root.find('lista_mensajes').findall('mensaje')
            analisis_por_fecha = self.process_messages(mensajes)

            # Guardar en la base de datos
            self.save_to_database(analisis_por_fecha)

            logging.info("File processed successfully")
            return {"status": "success"}
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
