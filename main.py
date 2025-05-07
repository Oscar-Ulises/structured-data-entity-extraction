import os
import json

from ocr import *
from extractorAvaluos import *
from marshmallow import Schema, fields
from flasgger import Swagger, Schema, fields
from flask import Flask, flash, jsonify, redirect, request

UPLOAD_FOLDER = 'pdf_files'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SWAGGER'] = {'title': 'Extracción Avalúos', 'uiversion': 3}
swag = Swagger(app, config={
    'openapi': '3.0.1',
    'specs': [{'endpoint': 'swagger', 'route': '/swagger.json/'}],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/v1/"
})

@swag.definition('AvalResult')
class AvalResult(Schema):
    isAvaluo = fields.String()
    isBarcode = fields.String()
    isLegible = fields.String()
    calleNumero = fields.String()
    colonia = fields.String()
    municipio = fields.String()
    estado = fields.String()
    isValor = fields.String()
    valor = fields.String()
    opcionFirma = fields.String()
    fechaAvaluo = fields.String()
    barcode = fields.String()
    isBarcodeOk = fields.String()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/Avaluo/SearchFromFile", methods=['POST'])
def SearchFromFile():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Extraer texto con OCR
            api_key = "e1810c717b1449b1962236c537df2cb3"
            ocr_url = "https://techhub-ai-cv.cognitiveservices.azure.com/vision/v3.2/read/analyze"
            texto = extraer_texto_azure_ocr(ocr_url, api_key, app.config['UPLOAD_FOLDER'], file.filename, paginas="todas")
            
            # Ejecutar extractor con el PDF y el texto extraído
            resultado = extractor(filepath, texto)
            
            return jsonify(resultado), 200
        else:
            return jsonify({"error": "File type not allowed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__': 
    app.run(debug=True)
