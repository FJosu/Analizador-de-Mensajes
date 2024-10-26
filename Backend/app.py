from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
import logging
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)

class XMLDatabase:
    def save_sales_data(self, file):
        try:
            # Leer y guardar el archivo XML sin procesamiento
            tree = ET.parse(file)
            root = tree.getroot()
            
            # Generar el XML para guardarlo como base de datos
            xml_response = ET.tostring(root, encoding='utf8', method='xml')
            
            # Guardar el archivo XML en la base de datos
            xml_file_path = os.path.join(os.getcwd(), './Backend/database.xml')
            with open(xml_file_path, 'wb') as f:
                f.write(xml_response)
                
            logging.info(f"XML file saved at: {xml_file_path}")
            return {'message': 'XML data saved successfully'}
        
        except ET.ParseError:
            logging.error("Invalid XML file")
            return {'error': 'Invalid XML file'}
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return {'error': 'Unexpected error'}

# Instancia de la clase XMLDatabase
xml_database = XMLDatabase()

# Endpoint para cargar y guardar el archivo XML
@app.route('/upload-file', methods=['POST'])
def upload_sales():
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        logging.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    result = xml_database.save_sales_data(file)
    return jsonify(result), 200 if 'message' in result else 400

if __name__ == '__main__':
    app.run(debug=True)
