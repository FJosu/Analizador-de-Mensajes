from flask import Flask, request, jsonify, send_file
import xml.etree.ElementTree as ET
from collections import defaultdict
import logging
import os
from datetime import datetime
import re
from flask_cors import CORS
from xml.dom import minidom
import unicodedata


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

    def remove_accents(self, text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
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
        self.sentimientos_positivos = [self.remove_accents(p.text.strip().lower()) for p in diccionario.find('sentimientos_positivos').findall('palabra')]
        self.sentimientos_negativos = [self.remove_accents(p.text.strip().lower()) for p in diccionario.find('sentimientos_negativos').findall('palabra')]

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
            texto_mensaje = self.remove_accents(mensaje.text.strip().lower())
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
        return ET.tostring(root, encoding='UTF-8', method='xml')

    def analizar_mensaje_individual(self, mensaje_texto):
        mensaje_texto = self.remove_accents(mensaje_texto.strip().lower())

        # Extraer fecha, usuario, y red social del mensaje
        fecha = self.extract_date_from_message(mensaje_texto)
        usuario = self.extract_user_from_message(mensaje_texto)
        red_social = self.extract_social_media_from_message(mensaje_texto)

        # Inicializa el análisis de sentimientos
        positivos = sum(1 for p in self.sentimientos_positivos if p in mensaje_texto)
        negativos = sum(1 for n in self.sentimientos_negativos if n in mensaje_texto)
        total_palabras = positivos + negativos

        # Determina el sentimiento general
        tipo_sentimiento = 'neutro'
        if positivos > negativos:
            tipo_sentimiento = 'positivo'
        elif negativos > positivos:
            tipo_sentimiento = 'negativo'

        # Calcula el porcentaje de sentimientos
        porcentaje_positivo = (positivos / total_palabras * 100) if total_palabras > 0 else 0
        porcentaje_negativo = (negativos / total_palabras * 100) if total_palabras > 0 else 0

        # Detecta empresas y servicios mencionados
        empresas_mencionadas = []
        for empresa, servicios in self.empresas_servicios.items():
            for servicio, alias in servicios.items():
                if any(a in mensaje_texto for a in alias):
                    empresas_mencionadas.append({"nombre": empresa, "servicio": servicio})

        # Genera la estructura XML en el formato solicitado
        respuesta = ET.Element('respuesta')
        ET.SubElement(respuesta, 'fecha').text = fecha
        ET.SubElement(respuesta, 'red_social').text = red_social
        ET.SubElement(respuesta, 'usuario').text = usuario

        empresas_elem = ET.SubElement(respuesta, 'empresas')
        for empresa_data in empresas_mencionadas:
            empresa_elem = ET.SubElement(empresas_elem, 'empresa', nombre=empresa_data["nombre"])
            ET.SubElement(empresa_elem, 'servicio').text = empresa_data["servicio"]

        ET.SubElement(respuesta, 'palabras_positivas').text = str(positivos)
        ET.SubElement(respuesta, 'palabras_negativas').text = str(negativos)
        ET.SubElement(respuesta, 'sentimiento_positivo').text = f"{porcentaje_positivo:.2f}%"
        ET.SubElement(respuesta, 'sentimiento_negativo').text = f"{porcentaje_negativo:.2f}%"
        ET.SubElement(respuesta, 'sentimiento_analizado').text = tipo_sentimiento

        # Retorna el XML como cadena de texto
        return ET.tostring(respuesta, encoding='UTF-8', method='xml').decode('UTF-8')

    def extract_date_from_message(self, mensaje):
        fecha_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', mensaje)
        return fecha_match.group(0) if fecha_match else "Fecha desconocida"

    def extract_user_from_message(self, mensaje):
        usuario_match = re.search(r'usuario:\s+([\w\.\@\d]+)', mensaje)
        return usuario_match.group(1) if usuario_match else "Usuario desconocido"

    def extract_social_media_from_message(self, mensaje):
        red_social_match = re.search(r'red social:\s+([A-Za-z]+)', mensaje)
        return red_social_match.group(1) if red_social_match else "Red social desconocida"


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
        print("se envió el archivo")
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Error sending file'}), 500


@app.route('/submit-data', methods=['POST'])
def obtener_datos():
    data = request.get_json()
    fecha_solicitada = data.get('fecha')
    empresa_solicitada = data.get('empresa')
    print(fecha_solicitada)
    print(empresa_solicitada)
    
    try:
        # Cargar y parsear el archivo XML
        tree = ET.parse('resultado_analisis.xml')
        root = tree.getroot()
        print("Archivo XML cargado correctamente")
    except FileNotFoundError:
        return jsonify({"error": "Archivo XML no encontrado"}), 500
    except ET.ParseError:
        return jsonify({"error": "Error al parsear el archivo XML"}), 500

    # Buscar la respuesta que coincide con la fecha solicitada o el último análisis
    respuestas = sorted(
        root.findall('respuesta'),
        key=lambda r: datetime.strptime(r.find('fecha').text, "%d/%m/%Y"),
        reverse=True
    )
    
    for respuesta in respuestas:
        fecha = respuesta.find('fecha').text
        if fecha == fecha_solicitada or fecha_solicitada == 'ultimo':
            if empresa_solicitada.lower() == "todas":
                total_positivos = 0
                total_negativos = 0
                total_neutros = 0

                for empresa in respuesta.find('analisis').findall('empresa'):
                    mensajes = empresa.find('mensajes')
                    total_positivos += int(mensajes.find('positivos').text)
                    total_negativos += int(mensajes.find('negativos').text)
                    total_neutros += int(mensajes.find('neutros').text)

                return jsonify({
                    'positivo': total_positivos,
                    'negativo': total_negativos,
                    'neutro': total_neutros
                })

            for empresa in respuesta.find('analisis').findall('empresa'):
                if empresa.get('nombre') == empresa_solicitada:
                    mensajes = empresa.find('mensajes')
                    positivos = int(mensajes.find('positivos').text)
                    negativos = int(mensajes.find('negativos').text)
                    neutros = int(mensajes.find('neutros').text)

                    return jsonify({
                        'positivo': positivos,
                        'negativo': negativos,
                        'neutro': neutros
                    })

    # Error si no se encuentra la fecha o empresa solicitada
    print("Fecha o empresa no encontrada en el archivo XML")
    return jsonify({'error': 'No se encontraron datos para la fecha o empresa especificada.'}), 404



@app.route('/fetch-range-data', methods=['POST'])
def fetch_range_data():
    data = request.json
    start_date = datetime.strptime(data['fecha_inicio'], "%d/%m/%Y")
    end_date = datetime.strptime(data['fecha_fin'], "%d/%m/%Y")
    empresa = data['empresa']
    tree = ET.parse('resultado_analisis.xml')
    root = tree.getroot()

    resultados = []

    for respuesta in root.findall('respuesta'):
        fecha = datetime.strptime(respuesta.find('fecha').text, "%d/%m/%Y")
        if start_date <= fecha <= end_date:
            if empresa == "todas":
                # Agrega los datos de todas las empresas en la fecha especificada
                for empresa_node in respuesta.find('analisis').findall('empresa'):
                    resultados.append(obtener_datos_empresa(fecha, empresa_node))
            else:
                # Agrega los datos solo de la empresa seleccionada
                empresa_node = respuesta.find(f".//empresa[@nombre='{empresa}']")
                if empresa_node:
                    resultados.append(obtener_datos_empresa(fecha, empresa_node))

    return jsonify(resultados)

def obtener_datos_empresa(fecha, empresa_node):
    return {
        "fecha": fecha.strftime("%d/%m/%Y"),
        "empresa": empresa_node.attrib['nombre'],
        "total": int(empresa_node.find('mensajes/total').text),
        "positivo": int(empresa_node.find('mensajes/positivos').text),
        "negativo": int(empresa_node.find('mensajes/negativos').text),
        "neutro": int(empresa_node.find('mensajes/neutros').text)
    }
    
@app.route('/analizar-mensaje', methods=['POST'])
def analizar_mensaje():
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    if not mensaje:
        return jsonify({"error": "No message provided"}), 400

    xml_resultado = analizador.analizar_mensaje_individual(mensaje)
    return xml_resultado, 200, {'Content-Type': 'application/xml'}

@app.route('/delete-file', methods=['DELETE'])
def delete_file_content():
    file_path = 'base_de_datos.xml'  # Especifica la ruta de tu archivo
    
    # Verificar si el archivo existe
    if os.path.exists(file_path):
        # Abrir el archivo en modo de escritura para vaciarlo
        with open(file_path, 'w') as file:
            file.write("")  # Escribe una cadena vacía para borrar el contenido
        return jsonify({"message": "Contenido del archivo eliminado"}), 200
    else:
        return jsonify({"error": "Archivo no encontrado"}), 404

    
if __name__ == '__main__':
    app.run(debug=True)
