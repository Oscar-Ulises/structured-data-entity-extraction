import re
import os
import glob
import time
import requests
import pytesseract

import pandas as pd

from PIL import Image
from tika import parser 
from collections import Counter
from pyzbar.pyzbar import decode
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def paginas_con_texto(documento):
    ruta = 'D:/Work/DocSolutions/Avaluos/Avaluos'
    pdf_path = os.path.join(ruta, documento)
    paginas = convert_from_path(pdf_path)
    paginas_con_texto = []

    for i, pagina in enumerate(paginas, start=1):
        texto = pytesseract.image_to_string(pagina)
        if len(texto.strip()) > 50:
            paginas_con_texto.append(i)

    return paginas_con_texto

def extraer_texto_azure_ocr(documento, paginas):
    
    api_key = "e1810c717b1449b1962236c537df2cb3"
    ocr_url = "https://techhub-ai-cv.cognitiveservices.azure.com/vision/v3.2/read/analyze"
    
    ruta = 'D:/Work/DocSolutions/Avaluos/Avaluos'
    ruta_documento = os.path.join(ruta, documento)
    
    with open(ruta_documento, "rb") as file:
        documento_pdf = file.read()
    
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Content-Type': 'application/pdf'
    }
    
    params = {
        'language': 'es',
        'pages': ','.join(map(str, paginas))
    }
    
    response = requests.post(ocr_url, headers=headers, params=params, data=documento_pdf)
    
    if response.status_code != 202:
        raise Exception(f"Error en la solicitud a Azure OCR: {response.status_code}, {response.text}")
    
    operation_location = response.headers['Operation-Location']
    
    while True:
        resultado = requests.get(operation_location, headers={'Ocp-Apim-Subscription-Key': api_key})
        resultado_json = resultado.json()
        
        if 'status' in resultado_json and resultado_json['status'] in ['succeeded', 'failed']:
            break
        
        time.sleep(2)
    
    if resultado_json['status'] == 'failed':
        raise Exception("La operación de OCR falló.")
    
    texto_extraido = "\n".join(
        line['text'] for region in resultado_json['analyzeResult']['readResults']
        for line in region.get('lines', [])
    )
    
    return texto_extraido

def quitar_tildes(texto):
    
    texto = texto.replace('Á','A')
    texto = texto.replace('É','E')
    texto = texto.replace('Í','I')
    texto = texto.replace('Ó','O')
    texto = texto.replace('Ú','U')
    
    return texto

def validez(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto)
        
        avaluos_comerciales = []
        avaluos = [ r"avalúo comercial", r"avaluo comercial", r"valuadora", r"entidad valuadora", r"avalúo", r"avaluo" ]

        for palabra in avaluos:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo, re.IGNORECASE)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.start() - 10) 
                fin = min(len(texto), coincidencia.end() + 10) 
                contexto = parrafo[inicio:fin]
                avaluos_comerciales.append(contexto)
        
        if len(avaluos_comerciales) == 0:
            return 'NO'
        else:
            return 'SI'
            
    except Exception as e:
        return '' 
    
def opcion_de_firma(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto)
        
        avaluos_digitales = []
        avaluos = [ r"avalúo digital", r"digital", r"notario" ]

        for palabra in avaluos:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo, re.IGNORECASE)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.start() - 10) 
                fin = min(len(texto), coincidencia.end() + 10) 
                contexto = parrafo[inicio:fin]
                avaluos_digitales.append(contexto)
        
        if len(avaluos_digitales) == 0:
            return 'FÍSICA'
        else:
            return 'ELECTRÓNICA'
            
    except Exception as e:
        return 'NINGUNA' 

def legibilidad(texto):
    
    el_municipio = municipio(texto)
        
    if el_municipio == '':
        return 'NO'
    else:
        return 'SI'
    
def codigo_de_barras_decode(image):
    try:
        image_gray = image.convert('L')
        barcodes = decode(image_gray)
        codigos = []  

        for barcode in barcodes:
            codigo = barcode.data.decode('utf-8')
            codigos.append(codigo)

        codigos = list(set(codigos))

        return codigos[-1] if codigos else ''
    except:
        return ''

def codigo_de_barras(pdf_url):
    try:
        images = convert_from_path(pdf_url)  
        booleano = 'NO'
        
        for i, image in enumerate(images):
            temp_image_path = f"temp_page_{i}.png"
            image.save(temp_image_path)

            with Image.open(temp_image_path) as img:
                codigo = codigo_de_barras_decode(img)
                if codigo:
                    os.remove(temp_image_path)
                    return codigo, 'SI'
            
            os.remove(temp_image_path)
        
        return '', booleano  
    except Exception as e:
        return '', 'NO'
    
def pre_estado(input_string):
    
    input_string = input_string.replace(r'[', '')
    input_string = input_string.replace(r']', '')

    patrones_estados = {
        'AGUASCA': 'AGUASCALIENTES',
        'BAJA CALI': 'BAJA CALIFORNIA',
        'NIA SUR': 'BAJA CALIFORNIA SUR',
        'CAMPE': 'CAMPECHE',
        'CHIAP': 'CHIAPAS',
        'CHIHUA': 'CHIHUAHUA',
        'COAHUI': 'COAHUILA',
        'COLIM': 'COLIMA',
        'DURANG': 'DURANGO',
        'GUANA': 'GUANAJUATO',
        'GUERRER': 'GUERRERO',
        'HIDAL': 'HIDALGO',
        'JALI': 'JALISCO',
        'CIUDAD DE ME': 'CIUDAD DE MEXICO',
        'CIUDAD DE MÉ': 'CIUDAD DE MEXICO',
        'ESTADO DE ME': 'ESTADO DE MEXICO',
        'ESTADO DE MÉ': 'ESTADO DE MEXICO',
        'MICHO': 'MICHOACAN',
        'MORELOS': 'MORELOS',
        'NAYAR': 'NAYARIT',
        'NUEVO LE': 'NUEVO LEON',
        'OAXA': 'OAXACA',
        'PUEBLA': 'PUEBLA',
        'QUERE': 'QUERETARO',
        'QUERÉ': 'QUERETARO',
        'ANA ROO': 'QUINTANA ROO',
        'SAN LUIS PO': 'SAN LUIS POTOSI',
        'SINAL': 'SINALOA',
        'SONOR': 'SONORA',
        'TABAS': 'TABASCO',
        'TAMAUL': 'TAMAULIPAS',
        'TLAXC': 'TLAXCALA',
        'VERAC': 'VERACRUZ',
        'YUCAT': 'YUCATAN',
        'ZACA': 'ZACATECAS'
    }

    for patron, estado in patrones_estados.items():
        if patron == input_string.upper():
            return quitar_tildes(estado)

    return ''

def estados_digitos(texto):
    
    estados_mexico = { '01': "AGUASCALIENTES", '02': "BAJA CALIFORNIA", '03': "BAJA CALIFORNIA SUR", '04': "CAMPECHE",
                       '05': "CHIAPAS", '06': "CHIHUAHUA", '07': "CIUDAD DE MEXICO", '08': "COAHUILA", '09': "COLIMA", 
                       '10': "DURANGO",  '11': "GUANAJUATO", '12': "GUERRERO", '13': "HIDALGO", '14': "JALISCO", 
                       '15': "ESTADO DE MEXICO", '16': "MICHOACAN", '17': "MORELOS", '18': "NAYARIT", '19': "NUEVO LEON",
                       '20': "OAXACA", '21': "PUEBLA", '22': "QUERÉTARO", '23': "QUINTANA ROO", '24': "SAN LUIS POTOSI", 
                       '25': "SINALOA", '26': "SONORA", '27': "TABASCO", '28': "TAMAULIPAS", '29': "TLAXCALA", '30': "VERACRUZ", 
                       '31': "YUCATAN", '32': "ZACATECAS" }
    
    
    numeros = re.findall(r'\d+', texto)
    
    numeros_filtrados = [num for num in numeros if len(num) == 2]
    
    if numeros_filtrados:
        numero = numeros_filtrados[0]  
        return estados_mexico.get(numero, '') 
    return ''

def estado(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto).upper()
        
        entidades_federativas = []
        coincidencias = re.finditer(r"ENTIDAD FED", parrafo)
        
        for coincidencia in coincidencias:
            inicio = coincidencia.end()
            fin = min(len(parrafo), inicio + 100)
            contexto = parrafo[inicio:fin]
            entidades_federativas.append(contexto)
            
        entidad_federativa = ' '.join(entidades_federativas)
        
        estados_clave = [
            r'AGUASCA', r'BAJA CALI', r'NIA SUR', r'CAMPE', r'CHIAP', r'CHIHUA', r'COAHUI', 
            r'COLIM', r'DURANG', r'GUANA', r'GUERRER', r'HIDAL', r'JALI', r'CIUDAD DE ME', r'CIUDAD DE MÉ'
            r'ESTADO DE ME', r'ESTADO DE MÉ', r'MICHO', r'MORELOS', r'NAYAR', r'NUEVO LE', r'OAXA', r'PUEBLA', 
            r'QUERE', r'QUERÉ', r'ANA ROO', r'SAN LUIS PO', r'SINAL', r'SONOR', r'TABAS', r'TAMAUL', 
            r'TLAXC', r'VERAC', r'YUCAT', r'ZACA' ]

        for palabra in estados_clave:
            coincidencia = re.search(palabra, entidad_federativa)
            if coincidencia:
                estado_seleccionado = coincidencia.group()  
                
        return pre_estado(estado_seleccionado)
    except Exception as e:
        return estados_digitos(entidad_federativa)
    
def ciudades_regex(texto, ciudades_clave, patrones_ciudades):
    try:
        parrafo = texto.upper()
        ciudades_seleccionadas = []

        for palabra in ciudades_clave:
            coincidencias = re.finditer(palabra, parrafo)
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.start() - 10)
                fin = min(len(parrafo), coincidencia.end() + 10)
                contexto = parrafo[inicio:fin]
                ciudades_seleccionadas.append(contexto)

        texto_resultante = "\n\n".join(ciudades_seleccionadas)

        frecuencias = Counter()
        for palabra in ciudades_clave:
            coincidencias = re.findall(palabra, texto_resultante)
            frecuencias[palabra] = len(coincidencias)

        if not frecuencias or all(f == 0 for f in frecuencias.values()):
            return ''

        ciudad_mas_repetida = max(frecuencias, key=frecuencias.get)
        ciudad_mas_repetida = ciudad_mas_repetida.replace('[', '').replace(']', '')

        for patron, ciudad in patrones_ciudades.items():
            if re.fullmatch(patron, ciudad_mas_repetida, re.IGNORECASE):
                return quitar_tildes(ciudad)

        return ''
    except:
        return ''

def pre_municipio(parrafo_municipio, estado_republica):
    try:
        parrafo_municipio = re.sub(r'[\r\n]+', ' ', re.sub(r'\s+', ' ', parrafo_municipio)).strip().upper()
        
        if len(estado_republica) == 0:
            return ''
 
        if re.search(r'AGUAS', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['MUNICIPIO DE AGUASCALIENTES', 'CIUDAD DE AGUASCALIENTES', 'ASIENTOS', 'CALVILLO', 'COS[IÍ]O', 'JES[UÚ]S MAR[IÍ]A', 'PABELL[OÓ]N DE ARTEAGA', 'RINC[OÓ]N DE ROMOS', 'SAN JOS[EÉ] DE GRACIA', 'TEPEZAL[AÁ]', 'EL LLANO', 'SAN FRANCISCO DE LOS ROMO', 'AGUASCALIENTES']
            patrones_ciudades = { 'MUNICIPIO DE AGUASCALIENTES': 'CIUDAD DE AGUASCALIENTES' ,'CIUDAD DE AGUASCALIENTES': 'CIUDAD DE AGUASCALIENTES', 'ASIENTOS': 'ASIENTOS', 'CALVILLO': 'CALVILLO', 'COSIÍO': 'COSÍO', 'JESUÚS MARIÍA': 'JESÚS MARÍA', 'PABELLOÓN DE ARTEAGA': 'PABELLÓN DE ARTEAGA', 'RINCOÓN DE ROMOS': 'RINCÓN DE ROMOS', 'SAN JOSEÉ DE GRACIA': 'SAN JOSÉ DE GRACIA', 'TEPEZALAÁ': 'TEPEZALÁ', 'EL LLANO': 'EL LLANO', 'SAN FRANCISCO DE LOS ROMO': 'SAN FRANCISCO DE LOS ROMO', 'AGUASCALIENTES': 'AGUASCALIENTES'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado
            
        elif re.search(r'SUR', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['COMOND[UÚ]', 'MULEG[EÉ]', 'LA PAZ', 'LOS CABOS', 'LORETO']
            patrones_ciudades = {'COMONDUÚ': 'COMONDÚ', 'MULEGEÉ': 'MULEGÉ', 'LA PAZ': 'LA PAZ', 'LOS CABOS': 'LOS CABOS', 'LORETO': 'LORETO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado
        
        elif re.search(r'BAJA', estado_republica, re.IGNORECASE) and not re.search(r'SUR', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ENSENADA', 'MEXICALI', 'TECATE', 'TIJUANA', 'PLAYAS DE ROSARITO', 'SAN QUINT[IÍ]N', 'SAN FELIPE']
            patrones_ciudades = {'ENSENADA': 'ENSENADA', 'MEXICALI': 'MEXICALI', 'TECATE': 'TECATE', 'TIJUANA': 'TIJUANA', 'PLAYAS DE ROSARITO': 'PLAYAS DE ROSARITO', 'SAN QUINTIÍN': 'SAN QUINTÍN', 'SAN FELIPE.': 'SAN FELIPE.'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado
            
        elif re.search(r'CAMPE', estado_republica, re.IGNORECASE):  
            ciudades_clave = [ 'FRANCISCO DE CAMPECHE', 'MUNICIPIO DE CAMPECHE', 'CALKIN[IÍ]', 'CIUDAD DE CAMPECHE', 'CARMEN', 'CHAMPOT[OÓ]N', 'HECELCHAK[AÁ]N', 'HOPELCH[EÉ]N', 'PALIZADA', 'TENABO', 'ESC[AÁ]RCEGA', 'CALAKMUL', 'CANDELARIA', 'SEYBAPLAYA', 'DZITBALCH[EÉ]', 'CAMPECHE']
            patrones_ciudades = { 'FRANCISCO DE CAMPECHE': 'CIUDAD DE CAMPECHE', 'MUNICIPIO DE CAMPECHE': 'CIUDAD DE CAMPECHE', 'CALKINIÍ': 'CALKINÍ', 'CIUDAD DE CAMPECHE': 'CIUDAD DE CAMPECHE', 'CARMEN': 'CARMEN', 'CHAMPOTOÓN': 'CHAMPOTÓN', 'HECELCHAKAÁN': 'HECELCHAKÁN', 'HOPELCHEÉN': 'HOPELCHÉN', 'PALIZADA': 'PALIZADA', 'TENABO': 'TENABO', 'ESCAÁRCEGA': 'ESCÁRCEGA', 'CALAKMUL': 'CALAKMUL', 'CANDELARIA': 'CANDELARIA', 'SEYBAPLAYA': 'SEYBAPLAYA', 'DZITBALCHEÉ': 'DZITBALCHÉ', 'CAMPECHE': 'CAMPECHE'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado
            
        elif re.search(r'CHIAP', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACACOYAGUA', 'ACALA', 'ACAPETAHUA', 'ALTAMIRANO', 'AMAT[AÁ]N', 'AMATENANGO DE LA FRONTERA', 'AMATENANGO DEL VALLE', '[AÁ]NGEL ALBINO CORZO', 'ARRIAGA', 'BEJUCAL DE OCAMPO', 'BELLA VISTA', 'BERRIOZ[AÁ]BAL', 'BOCHIL', 'EL BOSQUE', 'CACAHOAT[AÁ]N', 'CATAZAJ[AÁ]', 'CINTALAPA', 'COAPILLA', 'COMIT[AÁ]N DE DOM[IÍ]NGUEZ', 'LA CONCORDIA', 'COPAINAL[AÁ]', 'CHALCHIHUIT[AÁ]N', 'CHAMULA', 'CHANAL', 'CHAPULTENANGO', 'CHENALH[OÓ]', 'CHIAPA DE CORZO', 'CHIAPILLA', 'CHICOAS[EÉ]N', 'CHICOMUSELO', 'CHIL[OÓ]N', 'ESCUINTLA', 'FRANCISCO LE[OÓ]N', 'FRONTERA COMALAPA', 'FRONTERA HIDALGO', 'LA GRANDEZA', 'HUEHUET[AÁ]N', 'HUIXT[AÁ]N', 'HUITIUP[AÁ]N', 'HUIXTLA', 'LA INDEPENDENCIA', 'IXHUAT[AÁ]N', 'IXTACOMIT[AÁ]N', 'IXTAPA', 'IXTAPANGAJOYA', 'JIQUIPILAS', 'JITOTOL', 'JU[AÁ]REZ', 'LARR[AÁ]INZAR', 'LA LIBERTAD', 'MAPASTEPEC', 'LAS MARGARITAS', 'MAZAPA DE MADERO', 'MAZAT[AÁ]N', 'METAPA', 'MITONTIC', 'MOTOZINTLA', 'NICOL[AÁ]S RU[IÍ]Z', 'OCOSINGO', 'OCOTEPEC', 'OCOZOCOAUTLA DE ESPINOSA', 'OSTUAC[AÁ]N', 'OSUMACINTA', 'OXCHUC', 'PALENQUE', 'PANTELH[OÓ]', 'PANTEPEC', 'PICHUCALCO', 'PIJIJIAPAN', 'EL PORVENIR', 'VILLA COMALTITL[AÁ]N', 'PUEBLO NUEVO SOLISTAHUAC[AÁ]N', 'RAY[OÓ]N', 'REFORMA', 'LAS ROSAS', 'SABANILLA', 'SALTO DE AGUA', 'SAN CRIST[OÓ]BAL DE LAS CASAS', 'SAN FERNANDO', 'SILTEPEC', 'SIMOJOVEL', 'SITAL[AÁ]', 'SOCOLTENANGO', 'SOLOSUCHIAPA', 'SOYAL[OÓ]', 'SUCHIAPA', 'SUCHIATE', 'SUNUAPA', 'TAPACHULA', 'TAPALAPA', 'TAPILULA', 'TECPAT[AÁ]N', 'TENEJAPA', 'TEOPISCA', 'TILA', 'TONAL[AÁ]', 'TOTOLAPA', 'LA TRINITARIA', 'TUMBAL[AÁ]', 'TUXTLA GUTI[EÉ]RREZ', 'TUXTLA CHICO', 'TUZANT[AÁ]N', 'TZIMOL', 'UNI[OÓ]N JU[AÁ]REZ', 'VENUSTIANO CARRANZA', 'VILLA CORZO', 'VILLAFLORES', 'YAJAL[OÓ]N', 'SAN LUCAS', 'ZINACANT[AÁ]N', 'SAN JUAN CANCUC', 'ALDAMA', 'BENEM[EÉ]RITO DE LAS AM[EÉ]RICAS', 'MARAVILLA TENEJAPA', 'MARQU[EÉ]S DE COMILLAS', 'MONTECRISTO DE GUERRERO', 'SAN ANDR[EÉ]S DURAZNAL', 'SANTIAGO EL PINAR', 'CAPIT[AÁ]N LUIS [AÁ]NGEL VIDAL', 'RINC[OÓ]N CHAMULA SAN PEDRO', 'EL PARRAL', 'EMILIANO ZAPATA', 'MEZCALAPA', 'HONDURAS DE LA SIERRA']
            patrones_ciudades = {'ACACOYAGUA': 'ACACOYAGUA', 'ACALA': 'ACALA', 'ACAPETAHUA': 'ACAPETAHUA', 'ALTAMIRANO': 'ALTAMIRANO', 'AMATAÁN': 'AMATÁN', 'AMATENANGO DE LA FRONTERA': 'AMATENANGO DE LA FRONTERA', 'AMATENANGO DEL VALLE': 'AMATENANGO DEL VALLE', 'AÁNGEL ALBINO CORZO': 'ÁNGEL ALBINO CORZO', 'ARRIAGA': 'ARRIAGA', 'BEJUCAL DE OCAMPO': 'BEJUCAL DE OCAMPO', 'BELLA VISTA': 'BELLA VISTA', 'BERRIOZAÁBAL': 'BERRIOZÁBAL', 'BOCHIL': 'BOCHIL', 'EL BOSQUE': 'EL BOSQUE', 'CACAHOATAÁN': 'CACAHOATÁN', 'CATAZAJAÁ': 'CATAZAJÁ', 'CINTALAPA': 'CINTALAPA', 'COAPILLA': 'COAPILLA', 'COMITAÁN DE DOMIÍNGUEZ': 'COMITÁN DE DOMÍNGUEZ', 'LA CONCORDIA': 'LA CONCORDIA', 'COPAINALAÁ': 'COPAINALÁ', 'CHALCHIHUITAÁN': 'CHALCHIHUITÁN', 'CHAMULA': 'CHAMULA', 'CHANAL': 'CHANAL', 'CHAPULTENANGO': 'CHAPULTENANGO', 'CHENALHOÓ': 'CHENALHÓ', 'CHIAPA DE CORZO': 'CHIAPA DE CORZO', 'CHIAPILLA': 'CHIAPILLA', 'CHICOASEÉN': 'CHICOASÉN', 'CHICOMUSELO': 'CHICOMUSELO', 'CHILOÓN': 'CHILÓN', 'ESCUINTLA': 'ESCUINTLA', 'FRANCISCO LEOÓN': 'FRANCISCO LEÓN', 'FRONTERA COMALAPA': 'FRONTERA COMALAPA', 'FRONTERA HIDALGO': 'FRONTERA HIDALGO', 'LA GRANDEZA': 'LA GRANDEZA', 'HUEHUETAÁN': 'HUEHUETÁN', 'HUIXTAÁN': 'HUIXTÁN', 'HUITIUPAÁN': 'HUITIUPÁN', 'HUIXTLA': 'HUIXTLA', 'LA INDEPENDENCIA': 'LA INDEPENDENCIA', 'IXHUATAÁN': 'IXHUATÁN', 'IXTACOMITAÁN': 'IXTACOMITÁN', 'IXTAPA': 'IXTAPA', 'IXTAPANGAJOYA': 'IXTAPANGAJOYA', 'JIQUIPILAS': 'JIQUIPILAS', 'JITOTOL': 'JITOTOL', 'JUAÁREZ': 'JUÁREZ', 'LARRAÁINZAR': 'LARRÁINZAR', 'LA LIBERTAD': 'LA LIBERTAD', 'MAPASTEPEC': 'MAPASTEPEC', 'LAS MARGARITAS': 'LAS MARGARITAS', 'MAZAPA DE MADERO': 'MAZAPA DE MADERO', 'MAZATAÁN': 'MAZATÁN', 'METAPA': 'METAPA', 'MITONTIC': 'MITONTIC', 'MOTOZINTLA': 'MOTOZINTLA', 'NICOLAÁS RUIÍZ': 'NICOLÁS RUÍZ', 'OCOSINGO': 'OCOSINGO', 'OCOTEPEC': 'OCOTEPEC', 'OCOZOCOAUTLA DE ESPINOSA': 'OCOZOCOAUTLA DE ESPINOSA', 'OSTUACAÁN': 'OSTUACÁN', 'OSUMACINTA': 'OSUMACINTA', 'OXCHUC': 'OXCHUC', 'PALENQUE': 'PALENQUE', 'PANTELHOÓ': 'PANTELHÓ', 'PANTEPEC': 'PANTEPEC', 'PICHUCALCO': 'PICHUCALCO', 'PIJIJIAPAN': 'PIJIJIAPAN', 'EL PORVENIR': 'EL PORVENIR', 'VILLA COMALTITLAÁN': 'VILLA COMALTITLÁN', 'PUEBLO NUEVO SOLISTAHUACAÁN': 'PUEBLO NUEVO SOLISTAHUACÁN', 'RAYOÓN': 'RAYÓN', 'REFORMA': 'REFORMA', 'LAS ROSAS': 'LAS ROSAS', 'SABANILLA': 'SABANILLA', 'SALTO DE AGUA': 'SALTO DE AGUA', 'SAN CRISTOÓBAL DE LAS CASAS': 'SAN CRISTÓBAL DE LAS CASAS', 'SAN FERNANDO': 'SAN FERNANDO', 'SILTEPEC': 'SILTEPEC', 'SIMOJOVEL': 'SIMOJOVEL', 'SITALAÁ': 'SITALÁ', 'SOCOLTENANGO': 'SOCOLTENANGO', 'SOLOSUCHIAPA': 'SOLOSUCHIAPA', 'SOYALOÓ': 'SOYALÓ', 'SUCHIAPA': 'SUCHIAPA', 'SUCHIATE': 'SUCHIATE', 'SUNUAPA': 'SUNUAPA', 'TAPACHULA': 'TAPACHULA', 'TAPALAPA': 'TAPALAPA', 'TAPILULA': 'TAPILULA', 'TECPATAÁN': 'TECPATÁN', 'TENEJAPA': 'TENEJAPA', 'TEOPISCA': 'TEOPISCA', 'TILA': 'TILA', 'TONALAÁ': 'TONALÁ', 'TOTOLAPA': 'TOTOLAPA', 'LA TRINITARIA': 'LA TRINITARIA', 'TUMBALAÁ': 'TUMBALÁ', 'TUXTLA GUTIEÉRREZ': 'TUXTLA GUTIÉRREZ', 'TUXTLA CHICO': 'TUXTLA CHICO', 'TUZANTAÁN': 'TUZANTÁN', 'TZIMOL': 'TZIMOL', 'UNIOÓN JUAÁREZ': 'UNIÓN JUÁREZ', 'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA', 'VILLA CORZO': 'VILLA CORZO', 'VILLAFLORES': 'VILLAFLORES', 'YAJALOÓN': 'YAJALÓN', 'SAN LUCAS': 'SAN LUCAS', 'ZINACANTAÁN': 'ZINACANTÁN', 'SAN JUAN CANCUC': 'SAN JUAN CANCUC', 'ALDAMA': 'ALDAMA', 'BENEMEÉRITO DE LAS AMEÉRICAS': 'BENEMÉRITO DE LAS AMÉRICAS', 'MARAVILLA TENEJAPA': 'MARAVILLA TENEJAPA', 'MARQUEÉS DE COMILLAS': 'MARQUÉS DE COMILLAS', 'MONTECRISTO DE GUERRERO': 'MONTECRISTO DE GUERRERO', 'SAN ANDREÉS DURAZNAL': 'SAN ANDRÉS DURAZNAL', 'SANTIAGO EL PINAR': 'SANTIAGO EL PINAR', 'CAPITAÁN LUIS AÁNGEL VIDAL': 'CAPITÁN LUIS ÁNGEL VIDAL', 'RINCOÓN CHAMULA SAN PEDRO': 'RINCÓN CHAMULA SAN PEDRO', 'EL PARRAL': 'EL PARRAL', 'EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'MEZCALAPA': 'MEZCALAPA', 'HONDURAS DE LA SIERRA': 'HONDURAS DE LA SIERRA'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'CHIHUA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['MUNICIPIO DE JU', 'MUNICIPIO DE CHIHUA', 'AHUMADA', 'ALDAMA', 'ALLENDE', 'AQUILES SERD[AÁ]N', 'ASCENSI[OÓ]N', 'BACH[IÍ]NIVA', 'BALLEZA', 'BATOPILAS DE MANUEL G[OÓ]MEZ MOR[IÍ]N', 'BOCOYNA', 'BUENAVENTURA', 'CAMARGO', 'CARICH[IÍ]', 'CASAS GRANDES', 'CORONADO', 'COYAME DEL SOTOL', 'LA CRUZ', 'CUAUHT[EÉ]MOC', 'CUSIHUIRIACHI', 'CIUDAD DE CHIHUAHUA', 'CH[IÍ]NIPAS', 'DELICIAS', 'DR. BELISARIO DOM[IÍ]NGUEZ', 'GALEANA', 'SANTA ISABEL', 'G[OÓ]MEZ FAR[IÍ]AS', 'GRAN MORELOS', 'GUACHOCHI', 'GUADALUPE', 'GUADALUPE Y CALVO', 'GUAZAPARES', 'GUERRERO', 'HIDALGO DEL PARRAL', 'HUEJOTIT[AÁ]N', 'IGNACIO ZARAGOZA', 'JANOS', 'JIM[EÉ]NEZ', 'CIUDAD JU[AÁ]REZ', 'JULIMES', 'L[OÓ]PEZ', 'MADERA', 'MAGUARICHI', 'MANUEL BENAVIDES', 'MATACH[IÍ]', 'MATAMOROS', 'MEOQUI', 'MORELOS', 'MORIS', 'NAMIQUIPA', 'NONOAVA', 'NUEVO CASAS GRANDES', 'OCAMPO', 'OJINAGA', 'PRAXEDIS G. GUERRERO', 'RIVA PALACIO', 'ROSALES', 'ROSARIO', 'SAN FRANCISCO DE BORJA', 'SAN FRANCISCO DE CONCHOS', 'SAN FRANCISCO DEL ORO', 'SANTA B[AÁ]RBARA', 'SATEV[OÓ]', 'SAUCILLO', 'TEM[OÓ]SACHIC', 'EL TULE', 'URIQUE', 'URUACHI', 'VALLE DE ZARAGOZA', 'CHIHUAHUA', 'JU[AÁ]']
            patrones_ciudades = {'MUNICIPIO DE JU': 'CIUDAD JUÁREZ', 'MUNICIPIO DE CHIHUA': 'CHIHUAHUA', 'AHUMADA': 'AHUMADA', 'ALDAMA': 'ALDAMA', 'ALLENDE': 'ALLENDE', 'AQUILES SERDAÁN': 'AQUILES SERDÁN', 'ASCENSIOÓN': 'ASCENSIÓN', 'BACHIÍNIVA': 'BACHÍNIVA', 'BALLEZA': 'BALLEZA', 'BATOPILAS DE MANUEL GOÓMEZ MORIÍN': 'BATOPILAS DE MANUEL GÓMEZ MORÍN', 'BOCOYNA': 'BOCOYNA', 'BUENAVENTURA': 'BUENAVENTURA', 'CAMARGO': 'CAMARGO', 'CARICHIÍ': 'CARICHÍ', 'CASAS GRANDES': 'CASAS GRANDES', 'CORONADO': 'CORONADO', 'COYAME DEL SOTOL': 'COYAME DEL SOTOL', 'LA CRUZ': 'LA CRUZ', 'CUAUHTEÉMOC': 'CUAUHTÉMOC', 'CUSIHUIRIACHI': 'CUSIHUIRIACHI', 'CIUDAD DE CHIHUAHUA': 'CHIHUAHUA', 'CHIÍNIPAS': 'CHÍNIPAS', 'DELICIAS': 'DELICIAS', 'DR. BELISARIO DOMIÍNGUEZ': 'DR. BELISARIO DOMÍNGUEZ', 'GALEANA': 'GALEANA', 'SANTA ISABEL': 'SANTA ISABEL', 'GOÓMEZ FARIÍAS': 'GÓMEZ FARÍAS', 'GRAN MORELOS': 'GRAN MORELOS', 'GUACHOCHI': 'GUACHOCHI', 'GUADALUPE': 'GUADALUPE', 'GUADALUPE Y CALVO': 'GUADALUPE Y CALVO', 'GUAZAPARES': 'GUAZAPARES', 'GUERRERO': 'GUERRERO', 'HIDALGO DEL PARRAL': 'HIDALGO DEL PARRAL', 'HUEJOTITAÁN': 'HUEJOTITÁN', 'IGNACIO ZARAGOZA': 'IGNACIO ZARAGOZA', 'JANOS': 'JANOS', 'JIMEÉNEZ': 'JIMÉNEZ', 'CIUDAD JUAÁREZ': 'CIUDAD JUÁREZ', 'JULIMES': 'JULIMES', 'LOÓPEZ': 'LÓPEZ', 'MADERA': 'MADERA', 'MAGUARICHI': 'MAGUARICHI', 'MANUEL BENAVIDES': 'MANUEL BENAVIDES', 'MATACHIÍ': 'MATACHÍ', 'MATAMOROS': 'MATAMOROS', 'MEOQUI': 'MEOQUI', 'MORELOS': 'MORELOS', 'MORIS': 'MORIS', 'NAMIQUIPA': 'NAMIQUIPA', 'NONOAVA': 'NONOAVA', 'NUEVO CASAS GRANDES': 'NUEVO CASAS GRANDES', 'OCAMPO': 'OCAMPO', 'OJINAGA': 'OJINAGA', 'PRAXEDIS G. GUERRERO': 'PRAXEDIS G. GUERRERO', 'RIVA PALACIO': 'RIVA PALACIO', 'ROSALES': 'ROSALES', 'ROSARIO': 'ROSARIO', 'SAN FRANCISCO DE BORJA': 'SAN FRANCISCO DE BORJA', 'SAN FRANCISCO DE CONCHOS': 'SAN FRANCISCO DE CONCHOS', 'SAN FRANCISCO DEL ORO': 'SAN FRANCISCO DEL ORO', 'SANTA BAÁRBARA': 'SANTA BÁRBARA', 'SATEVOÓ': 'SATEVÓ', 'SAUCILLO': 'SAUCILLO', 'TEMOÓSACHIC': 'TEMÓSACHIC', 'EL TULE': 'EL TULE', 'URIQUE': 'URIQUE', 'URUACHI': 'URUACHI', 'VALLE DE ZARAGOZA': 'VALLE DE ZARAGOZA', 'CHIHUAHUA': 'CHIHUAHUA', 'JUAÁ': 'JUÁREZ'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'CIUDAD', estado_republica, re.IGNORECASE) or re.search(r'ESTADO', estado_republica, re.IGNORECASE):  
            ciudades_clave = [  'VARO OBREG', 'AZCAPO', 'BENITO JU[AÁ]R', 'COYOAC', 'CUAJIMALPA DE', 'CUAUHT', 'GUSTAVO A', 'IZTACAL', 'ITZTAPALA', 'MAGDALENA CONTRE', 'MIGUEL', 'MILPA ALTA', 'TL[AÁ]HUAC', 'VENUSTIANO CARRA', 'XOCHIMILC', 'ACAMBAY DE RU[IÍ]Z CASTAÑEDA', 'ACOLMAN', 'ACULCO', 'ALMOLOYA DE ALQUISIRAS', 'ALMOLOYA DE JU[AÁ]REZ', 'ALMOLOYA DEL R[IÍ]O', 'AMANALCO', 'AMATEPEC', 'AMECAMECA', 'APAXCO', 'ATENCO', 'ATIZAP[AÁ]N', 'ATIZAP[AÁ]N DE ZARAGOZA', 'ATLACOMULCO', 'ATLAUTLA', 'AXAPUSCO', 'AYAPANGO', 'CALIMAYA', 'CAPULHUAC', 'COACALCO DE BERRIOZ[AÁ]BAL', 'COATEPEC HARINAS', 'COCOTITL[AÁ]N', 'COYOTEPEC', 'CUAUTITL[AÁ]N', 'CHALCO', 'CHAPA DE MOTA', 'CHAPULTEPEC', 'CHIAUTLA', 'CHICOLOAPAN', 'CHICONCUAC', 'CHIMALHUAC[AÁ]N', 'DONATO GUERRA', 'ECATEPEC', 'ECATZINGO', 'HUEHUETOCA', 'HUEYPOXTLA', 'HUIXQUILUCAN', 'ISIDRO FABELA', 'IXTAPALUCA', 'IXTAPAN DE LA SAL', 'IXTAPAN DEL ORO', 'IXTLAHUACA', 'XALATLACO', 'JALTENCO', 'JILOTEPEC', 'JILOTZINGO', 'JIQUIPILCO', 'JOCOTITL[AÁ]N', 'JOQUICINGO', 'JUCHITEPEC', 'LERMA', 'MALINALCO', 'MELCHOR OCAMPO', 'METEPEC', 'MEXICALTZINGO', 'CIUDAD DE MORELOS', 'MUNICIPIO DE MORELOS', 'NAUCALPAN DE JU[AÁ]REZ', 'NEZAHUALC[OÓ]YOTL', 'NEXTLALPAN', 'NICOL[AÁ]S ROMERO', 'NOPALTEPEC', 'OCOYOACAC', 'OCUILAN', 'EL ORO', 'OTUMBA', 'OTZOLOAPAN', 'OTZOLOTEPEC', 'OZUMBA', 'PAPALOTLA', 'LA PAZ', 'POLOTITL[AÁ]N', 'RAY[OÓ]N', 'SAN ANTONIO LA ISLA', 'SAN FELIPE DEL PROGRESO', 'SAN MART[IÍ]N DE LAS PIR[AÁ]MIDES', 'SAN MATEO ATENCO', 'SAN SIM[OÓ]N DE GUERRERO', 'SANTO TOM[AÁ]S', 'SOYANIQUILPAN DE JU[AÁ]REZ', 'SULTEPEC', 'TEC[AÁ]MAC', 'TEJUPILCO', 'TEMAMATLA', 'TEMASCALAPA', 'TEMASCALCINGO', 'TEMASCALTEPEC', 'TEMOAYA', 'TENANCINGO', 'TENANGO DEL AIRE', 'TENANGO DEL VALLE', 'TEOLOYUCAN', 'TEOTIHUAC[AÁ]N', 'TEPETLAOXTOC', 'TEPETLIXPA', 'TEPOTZOTL[AÁ]N', 'TEQUIXQUIAC', 'TEXCALTITL[AÁ]N', 'TEXCALYACAC', 'TEXCOCO', 'TEZOYUCA', 'TIANGUISTENCO', 'TIMILPAN', 'TLALMANALCO', 'TLALNEPANTLA DE BAZ', 'TLATLAYA', 'TOLUCA', 'TONATICO', 'TULTEPEC', 'TULTITL[AÁ]N', 'VALLE DE BRAVO', 'VILLA DE ALLENDE', 'VILLA DEL CARB[OÓ]N', 'VILLA GUERRERO', 'VILLA VICTORIA', 'XONACATL[AÁ]N', 'ZACAZONAPAN', 'ZACUALPAN', 'ZINACANTEPEC', 'ZUMPAHUAC[AÁ]N', 'ZUMPANGO', 'CUAUTITL[AÁ]N IZCALLI', 'VALLE DE CHALCO SOLIDARIDAD', 'LUVIANOS', 'SAN JOS[EÉ] DEL RINC[OÓ]N', 'TONANITLA', r'TLALPAN']
            patrones_ciudades = {  'VARO OBREG': 'ÁLVARO OBREGÓN', 'AZCAPO': 'AZCAPOTZALCO', 'BENITO JUAÁR': 'BENITO JUÁREZ', 'COYOAC': 'COYOACÁN', 'CUAJIMALPA DE': 'CUAJIMALPA DE MORELOS', 'CUAUHT': 'CUAUHTÉMOC', 'GUSTAVO A': 'GUSTAVO A. MADERO', 'IZTACAL': 'IZTACALCO', 'ITZTAPALA': 'IZTAPALAPA', 'MAGDALENA CONTRE': 'LA MAGDALENA CONTRERAS', 'MIGUEL': 'MIGUEL HIDALGO', 'MILPA ALTA': 'MILPA ALTA', 'TLAÁHUAC': 'TLÁHUAC', 'VENUSTIANO CARRA': 'VENUSTIANO CARRANZA', 'XOCHIMILC': 'XOCHIMILCO','ACAMBAY DE RUIÍZ CASTAÑEDA': 'ACAMBAY DE RUÍZ CASTAÑEDA', 'ACOLMAN': 'ACOLMAN', 'ACULCO': 'ACULCO', 'ALMOLOYA DE ALQUISIRAS': 'ALMOLOYA DE ALQUISIRAS', 'ALMOLOYA DE JUAÁREZ': 'ALMOLOYA DE JUÁREZ', 'ALMOLOYA DEL RIÍO': 'ALMOLOYA DEL RÍO', 'AMANALCO': 'AMANALCO', 'AMATEPEC': 'AMATEPEC', 'AMECAMECA': 'AMECAMECA', 'APAXCO': 'APAXCO', 'ATENCO': 'ATENCO', 'ATIZAPAÁN': 'ATIZAPÁN', 'ATIZAPAÁN DE ZARAGOZA': 'ATIZAPÁN DE ZARAGOZA', 'ATLACOMULCO': 'ATLACOMULCO', 'ATLAUTLA': 'ATLAUTLA', 'AXAPUSCO': 'AXAPUSCO', 'AYAPANGO': 'AYAPANGO', 'CALIMAYA': 'CALIMAYA', 'CAPULHUAC': 'CAPULHUAC', 'COACALCO DE BERRIOZAÁBAL': 'COACALCO DE BERRIOZÁBAL', 'COATEPEC HARINAS': 'COATEPEC HARINAS', 'COCOTITLAÁN': 'COCOTITLÁN', 'COYOTEPEC': 'COYOTEPEC', 'CUAUTITLAÁN': 'CUAUTITLÁN', 'CHALCO': 'CHALCO', 'CHAPA DE MOTA': 'CHAPA DE MOTA', 'CHAPULTEPEC': 'CHAPULTEPEC', 'CHIAUTLA': 'CHIAUTLA', 'CHICOLOAPAN': 'CHICOLOAPAN', 'CHICONCUAC': 'CHICONCUAC', 'CHIMALHUACAÁN': 'CHIMALHUACÁN', 'DONATO GUERRA': 'DONATO GUERRA', 'ECATEPEC': 'ECATEPEC DE MORELOS', 'ECATZINGO': 'ECATZINGO', 'HUEHUETOCA': 'HUEHUETOCA', 'HUEYPOXTLA': 'HUEYPOXTLA', 'HUIXQUILUCAN': 'HUIXQUILUCAN', 'ISIDRO FABELA': 'ISIDRO FABELA', 'IXTAPALUCA': 'IXTAPALUCA', 'IXTAPAN DE LA SAL': 'IXTAPAN DE LA SAL', 'IXTAPAN DEL ORO': 'IXTAPAN DEL ORO', 'IXTLAHUACA': 'IXTLAHUACA', 'XALATLACO': 'XALATLACO', 'JALTENCO': 'JALTENCO', 'JILOTEPEC': 'JILOTEPEC', 'JILOTZINGO': 'JILOTZINGO', 'JIQUIPILCO': 'JIQUIPILCO', 'JOCOTITLAÁN': 'JOCOTITLÁN', 'JOQUICINGO': 'JOQUICINGO', 'JUCHITEPEC': 'JUCHITEPEC', 'LERMA': 'LERMA', 'MALINALCO': 'MALINALCO', 'MELCHOR OCAMPO': 'MELCHOR OCAMPO', 'METEPEC': 'METEPEC', 'MEXICALTZINGO': 'MEXICALTZINGO', 'CIUDAD DE MORELOS': 'MORELOS', 'MUNICIPIO DE MORELOS': 'MORELOS', 'NAUCALPAN DE JUAÁREZ': 'NAUCALPAN DE JUÁREZ', 'NEZAHUALCOÓYOTL': 'NEZAHUALCÓYOTL', 'NEXTLALPAN': 'NEXTLALPAN', 'NICOLAÁS ROMERO': 'NICOLÁS ROMERO', 'NOPALTEPEC': 'NOPALTEPEC', 'OCOYOACAC': 'OCOYOACAC', 'OCUILAN': 'OCUILAN', 'EL ORO': 'EL ORO', 'OTUMBA': 'OTUMBA', 'OTZOLOAPAN': 'OTZOLOAPAN', 'OTZOLOTEPEC': 'OTZOLOTEPEC', 'OZUMBA': 'OZUMBA', 'PAPALOTLA': 'PAPALOTLA', 'LA PAZ': 'LA PAZ', 'POLOTITLAÁN': 'POLOTITLÁN', 'RAYOÓN': 'RAYÓN', 'SAN ANTONIO LA ISLA': 'SAN ANTONIO LA ISLA', 'SAN FELIPE DEL PROGRESO': 'SAN FELIPE DEL PROGRESO', 'SAN MARTIÍN DE LAS PIRAÁMIDES': 'SAN MARTÍN DE LAS PIRÁMIDES', 'SAN MATEO ATENCO': 'SAN MATEO ATENCO', 'SAN SIMOÓN DE GUERRERO': 'SAN SIMÓN DE GUERRERO', 'SANTO TOMAÁS': 'SANTO TOMÁS', 'SOYANIQUILPAN DE JUAÁREZ': 'SOYANIQUILPAN DE JUÁREZ', 'SULTEPEC': 'SULTEPEC', 'TECAÁMAC': 'TECÁMAC', 'TEJUPILCO': 'TEJUPILCO', 'TEMAMATLA': 'TEMAMATLA', 'TEMASCALAPA': 'TEMASCALAPA', 'TEMASCALCINGO': 'TEMASCALCINGO', 'TEMASCALTEPEC': 'TEMASCALTEPEC', 'TEMOAYA': 'TEMOAYA', 'TENANCINGO': 'TENANCINGO', 'TENANGO DEL AIRE': 'TENANGO DEL AIRE', 'TENANGO DEL VALLE': 'TENANGO DEL VALLE', 'TEOLOYUCAN': 'TEOLOYUCAN', 'TEOTIHUACAÁN': 'TEOTIHUACÁN', 'TEPETLAOXTOC': 'TEPETLAOXTOC', 'TEPETLIXPA': 'TEPETLIXPA', 'TEPOTZOTLAÁN': 'TEPOTZOTLÁN', 'TEQUIXQUIAC': 'TEQUIXQUIAC', 'TEXCALTITLAÁN': 'TEXCALTITLÁN', 'TEXCALYACAC': 'TEXCALYACAC', 'TEXCOCO': 'TEXCOCO', 'TEZOYUCA': 'TEZOYUCA', 'TIANGUISTENCO': 'TIANGUISTENCO', 'TIMILPAN': 'TIMILPAN', 'TLALMANALCO': 'TLALMANALCO', 'TLALNEPANTLA DE BAZ': 'TLALNEPANTLA DE BAZ', 'TLATLAYA': 'TLATLAYA', 'TOLUCA': 'TOLUCA', 'TONATICO': 'TONATICO', 'TULTEPEC': 'TULTEPEC', 'TULTITLAÁN': 'TULTITLÁN', 'VALLE DE BRAVO': 'VALLE DE BRAVO', 'VILLA DE ALLENDE': 'VILLA DE ALLENDE', 'VILLA DEL CARBOÓN': 'VILLA DEL CARBÓN', 'VILLA GUERRERO': 'VILLA GUERRERO', 'VILLA VICTORIA': 'VILLA VICTORIA', 'XONACATLAÁN': 'XONACATLÁN', 'ZACAZONAPAN': 'ZACAZONAPAN', 'ZACUALPAN': 'ZACUALPAN', 'ZINACANTEPEC': 'ZINACANTEPEC', 'ZUMPAHUACAÁN': 'ZUMPAHUACÁN', 'ZUMPANGO': 'ZUMPANGO', 'CUAUTITLAÁN IZCALLI': 'CUAUTITLÁN IZCALLI', 'VALLE DE CHALCO SOLIDARIDAD': 'VALLE DE CHALCO SOLIDARIDAD', 'LUVIANOS': 'LUVIANOS', 'SAN JOSEÉ DEL RINCOÓN': 'SAN JOSÉ DEL RINCÓN', 'TONANITLA': 'TONANITLA', 'TLALPAN': 'TLALPAN'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'COAH', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ABASOLO', 'ACUÑA', 'ALLENDE', 'ARTEAGA', 'CANDELA', 'CASTAÑOS', 'CUATRO CI[EÉ]NEGAS', 'ESCOBEDO', 'FRANCISCO I. MADERO', 'FRONTERA', 'GENERAL CEPEDA', 'GUERRERO', 'CIUDAD DE HIDALGO', 'MUNICIPIO DE HIDALGO', 'JIM[EÉ]NEZ', 'JU[AÁ]REZ', 'LAMADRID', 'MATAMOROS', 'MONCLOVA', 'MORELOS', 'M[UÚ]ZQUIZ', 'NADADORES', 'NAVA', 'OCAMPO', 'PARRAS', 'PIEDRAS NEGRAS', 'PROGRESO', 'RAMOS ARIZPE', 'SACRAMENTO', 'SALTILLO', 'SAN BUENAVENTURA', 'JUAN', 'SAN PEDRO', 'SIERRA MOJADA', 'TORRE[OÓ]N', 'VIESCA', 'VILLA UNI[OÓ]N', 'ZARAGOZA', 'SABINAS']
            patrones_ciudades = {'ABASOLO': 'ABASOLO', 'ACUÑA': 'ACUÑA', 'ALLENDE': 'ALLENDE', 'ARTEAGA': 'ARTEAGA', 'CANDELA': 'CANDELA', 'CASTAÑOS': 'CASTAÑOS', 'CUATRO CIEÉNEGAS': 'CUATRO CIÉNEGAS', 'ESCOBEDO': 'ESCOBEDO', 'FRANCISCO I. MADERO': 'FRANCISCO I. MADERO', 'FRONTERA': 'FRONTERA', 'GENERAL CEPEDA': 'GENERAL CEPEDA', 'GUERRERO': 'GUERRERO', 'CIUDAD DE HIDALGO': 'MUNICIPIO DE HIDALGO', 'HIDALGO': 'HIDALGO', 'JIMEÉNEZ': 'JIMÉNEZ', 'JUAÁREZ': 'JUÁREZ', 'LAMADRID': 'LAMADRID', 'MATAMOROS': 'MATAMOROS', 'MONCLOVA': 'MONCLOVA', 'MORELOS': 'MORELOS', 'MUÚZQUIZ': 'MÚZQUIZ', 'NADADORES': 'NADADORES', 'NAVA': 'NAVA', 'OCAMPO': 'OCAMPO', 'PARRAS': 'PARRAS', 'PIEDRAS NEGRAS': 'PIEDRAS NEGRAS', 'PROGRESO': 'PROGRESO', 'RAMOS ARIZPE': 'RAMOS ARIZPE', 'SACRAMENTO': 'SACRAMENTO', 'SALTILLO': 'SALTILLO', 'SAN BUENAVENTURA': 'SAN BUENAVENTURA', 'JUAN': 'SAN JUAN DE SABINAS', 'SAN PEDRO': 'SAN PEDRO', 'SIERRA MOJADA': 'SIERRA MOJADA', 'TORREOÓN': 'TORREÓN', 'VIESCA': 'VIESCA', 'VILLA UNIOÓN': 'VILLA UNIÓN', 'ZARAGOZA': 'ZARAGOZA', 'SABINAS': 'SABINAS'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'COLI', estado_republica, re.IGNORECASE):  
            ciudades_clave = [ 'MUNICIPIO DE COLIMA','ARMER[IÍ]A', 'CIUDAD DE COLIMA', 'COMALA', 'COQUIMATL[AÁ]N', 'CUAUHT[EÉ]MOC', 'IXTLAHUAC[AÁ]N', 'MANZANILLO', 'MINATITL[AÁ]N', 'TECOM[AÁ]N', 'VILLA DE [AÁ]LVAREZ', 'COLIMA']
            patrones_ciudades = { 'MUNICIPIO DE COLIMA': 'CIUDAD DE COLIMA', 'ARMERIÍA': 'ARMERÍA', 'CIUDAD DE COLIMA': 'CIUDAD DE COLIMA', 'COMALA': 'COMALA', 'COQUIMATLAÁN': 'COQUIMATLÁN', 'CUAUHTEÉMOC': 'CUAUHTÉMOC', 'IXTLAHUACAÁN': 'IXTLAHUACÁN', 'MANZANILLO': 'MANZANILLO', 'MINATITLAÁN': 'MINATITLÁN', 'TECOMAÁN': 'TECOMÁN', 'VILLA DE AÁLVAREZ': 'VILLA DE ÁLVAREZ', 'COLIMA': 'COLIMA'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'DURAN', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['CANATL[AÁ]N', 'CANELAS', 'CONETO DE COMONFORT', 'CUENCAM[EÉ]', 'MUNICIPIO DE DURANGO', 'CIUDAD DE DURANGO', 'GENERAL SIM[OÓ]N BOL[IÍ]VAR', 'G[OÓ]MEZ PALACIO', 'GUADALUPE VICTORIA', 'GUANACEV[IÍ]', 'HIDALGO', 'IND[EÉ]', 'LERDO', 'MAPIM[IÍ]', 'MEZQUITAL', 'NAZAS', 'NOMBRE DE DIOS', 'OCAMPO', 'EL ORO', 'OT[AÁ]EZ', 'P[AÁ]NUCO DE CORONADO', 'PEÑ[OÓ]N BLANCO', 'POANAS', 'PUEBLO NUEVO', 'RODEO', 'SAN BERNARDO', 'SAN DIMAS', 'SAN JUAN DE GUADALUPE', 'SAN JUAN DEL R[IÍ]O', 'SAN LUIS DEL CORDERO', 'SAN PEDRO DEL GALLO', 'SANTA CLARA', 'SANTIAGO PAPASQUIARO', 'S[UÚ]CHIL', 'TAMAZULA', 'TEPEHUANES', 'TLAHUALILO', 'TOPIA', 'VICENTE GUERRERO', 'NUEVO IDEAL', 'DURANGO']
            patrones_ciudades = {'CANATLAÁN': 'CANATLÁN', 'CANELAS': 'CANELAS', 'CONETO DE COMONFORT': 'CONETO DE COMONFORT', 'CUENCAMEÉ': 'CUENCAMÉ', 'MUNICIPIO DE DURANGO': 'CIUDAD DE DURANGO', 'CIUDAD DE DURANGO': 'CIUDAD DE DURANGO', 'GENERAL SIMOÓN BOLIÍVAR': 'GENERAL SIMÓN BOLÍVAR', 'GOÓMEZ PALACIO': 'GÓMEZ PALACIO', 'GUADALUPE VICTORIA': 'GUADALUPE VICTORIA', 'GUANACEVIÍ': 'GUANACEVÍ', 'HIDALGO': 'HIDALGO', 'INDEÉ': 'INDÉ', 'LERDO': 'LERDO', 'MAPIMIÍ': 'MAPIMÍ', 'MEZQUITAL': 'MEZQUITAL', 'NAZAS': 'NAZAS', 'NOMBRE DE DIOS': 'NOMBRE DE DIOS', 'OCAMPO': 'OCAMPO', 'EL ORO': 'EL ORO', 'OTAÁEZ': 'OTÁEZ', 'PAÁNUCO DE CORONADO': 'PÁNUCO DE CORONADO', 'PEÑOÓN BLANCO': 'PEÑÓN BLANCO', 'POANAS': 'POANAS', 'PUEBLO NUEVO': 'PUEBLO NUEVO', 'RODEO': 'RODEO', 'SAN BERNARDO': 'SAN BERNARDO', 'SAN DIMAS': 'SAN DIMAS', 'SAN JUAN DE GUADALUPE': 'SAN JUAN DE GUADALUPE', 'SAN JUAN DEL RIÍO': 'SAN JUAN DEL RÍO', 'SAN LUIS DEL CORDERO': 'SAN LUIS DEL CORDERO', 'SAN PEDRO DEL GALLO': 'SAN PEDRO DEL GALLO', 'SANTA CLARA': 'SANTA CLARA', 'SANTIAGO PAPASQUIARO': 'SANTIAGO PAPASQUIARO', 'SUÚCHIL': 'SÚCHIL', 'TAMAZULA': 'TAMAZULA', 'TEPEHUANES': 'TEPEHUANES', 'TLAHUALILO': 'TLAHUALILO', 'TOPIA': 'TOPIA', 'VICENTE GUERRERO': 'VICENTE GUERRERO', 'NUEVO IDEAL': 'NUEVO IDEAL', 'DURANGO': 'DURANGO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'GUANA', estado_republica, re.IGNORECASE):  
            ciudades_clave = [ 'MUNICIPIO DE GUANAJUATO', 'ABASOLO', 'AC[AÁ]MBARO', 'SAN MIGUEL DE ALLENDE', 'APASEO EL ALTO', 'APASEO EL GRANDE', 'ATARJEA', 'CELAYA', 'MANUEL DOBLADO', 'COMONFORT', 'CORONEO', 'CORTAZAR', 'CUER[AÁ]MARO', 'DOCTOR MORA', 'DOLORES HIDALGO CUNA DE LA INDEPENDENCIA NACIONAL', 'CIUDAD DE GUANAJUATO', 'HUAN[IÍ]MARO', 'IRAPUATO', 'JARAL DEL PROGRESO', 'JER[EÉ]CUARO', 'LE[OÓ]N', 'MOROLE[OÓ]N', 'OCAMPO', 'P[EÉ]NJAMO', 'PUEBLO NUEVO', 'PUR[IÍ]SIMA DEL RINC[OÓ]N', 'ROMITA', 'SALAMANCA', 'SALVATIERRA', 'SAN DIEGO DE LA UNI[OÓ]N', 'SAN FELIPE', 'SAN FRANCISCO DEL RINC[OÓ]N', 'SAN JOS[EÉ] ITURBIDE', 'SAN LUIS DE LA PAZ', 'SANTA CATARINA', 'SANTA CRUZ DE JUVENTINO ROSAS', 'SANTIAGO MARAVAT[IÍ]O', 'SILAO DE LA VICTORIA', 'TARANDACUAO', 'TARIMORO', 'TIERRA BLANCA', 'URIANGATO', 'VALLE DE SANTIAGO', 'VICTORIA', 'VILLAGR[AÁ]N', 'XICH[UÚ]', 'YURIRIA', 'GUANAJUATO']
            patrones_ciudades = { 'MUNICIPIO DE GUANAJUATO': 'CIUDAD DE GUANAJUATO','ABASOLO': 'ABASOLO', 'ACAÁMBARO': 'ACÁMBARO', 'SAN MIGUEL DE ALLENDE': 'SAN MIGUEL DE ALLENDE', 'APASEO EL ALTO': 'APASEO EL ALTO', 'APASEO EL GRANDE': 'APASEO EL GRANDE', 'ATARJEA': 'ATARJEA', 'CELAYA': 'CELAYA', 'MANUEL DOBLADO': 'MANUEL DOBLADO', 'COMONFORT': 'COMONFORT', 'CORONEO': 'CORONEO', 'CORTAZAR': 'CORTAZAR', 'CUERAÁMARO': 'CUERÁMARO', 'DOCTOR MORA': 'DOCTOR MORA', 'DOLORES HIDALGO CUNA DE LA INDEPENDENCIA NACIONAL': 'DOLORES HIDALGO CUNA DE LA INDEPENDENCIA NACIONAL', 'CIUDAD DE GUANAJUATO': 'CIUDAD DE GUANAJUATO', 'HUANIÍMARO': 'HUANÍMARO', 'IRAPUATO': 'IRAPUATO', 'JARAL DEL PROGRESO': 'JARAL DEL PROGRESO', 'JEREÉCUARO': 'JERÉCUARO', 'LEOÓN': 'LEÓN', 'MOROLEOÓN': 'MOROLEÓN', 'OCAMPO': 'OCAMPO', 'PEÉNJAMO': 'PÉNJAMO', 'PUEBLO NUEVO': 'PUEBLO NUEVO', 'PURIÍSIMA DEL RINCOÓN': 'PURÍSIMA DEL RINCÓN', 'ROMITA': 'ROMITA', 'SALAMANCA': 'SALAMANCA', 'SALVATIERRA': 'SALVATIERRA', 'SAN DIEGO DE LA UNIOÓN': 'SAN DIEGO DE LA UNIÓN', 'SAN FELIPE': 'SAN FELIPE', 'SAN FRANCISCO DEL RINCOÓN': 'SAN FRANCISCO DEL RINCÓN', 'SAN JOSEÉ ITURBIDE': 'SAN JOSÉ ITURBIDE', 'SAN LUIS DE LA PAZ': 'SAN LUIS DE LA PAZ', 'SANTA CATARINA': 'SANTA CATARINA', 'SANTA CRUZ DE JUVENTINO ROSAS': 'SANTA CRUZ DE JUVENTINO ROSAS', 'SANTIAGO MARAVATIÍO': 'SANTIAGO MARAVATÍO', 'SILAO DE LA VICTORIA': 'SILAO DE LA VICTORIA', 'TARANDACUAO': 'TARANDACUAO', 'TARIMORO': 'TARIMORO', 'TIERRA BLANCA': 'TIERRA BLANCA', 'URIANGATO': 'URIANGATO', 'VALLE DE SANTIAGO': 'VALLE DE SANTIAGO', 'VICTORIA': 'VICTORIA', 'VILLAGRAÁN': 'VILLAGRÁN', 'XICHUÚ': 'XICHÚ', 'YURIRIA': 'YURIRIA', 'GUANAJUATO': 'GUANAJUATO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'GUERR', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACAPULCO DE JU[AÁ]REZ', 'AHUACUOTZINGO', 'AJUCHITL[AÁ]N DEL PROGRESO', 'ALCOZAUCA DE GUERRERO', 'ALPOYECA', 'APAXTLA', 'ARCELIA', 'ATENANGO DEL R[IÍ]O', 'ATLAMAJALCINGO DEL MONTE', 'ATLIXTAC', 'ATOYAC DE [AÁ]LVAREZ', 'AYUTLA DE LOS LIBRES', 'AZOY[UÚ]', 'BENITO JU[AÁ]REZ', 'BUENAVISTA DE CU[EÉ]LLAR', 'COAHUAYUTLA DE JOS[EÉ] MAR[IÍ]A IZAZAGA', 'COCULA', 'COPALA', 'COPALILLO', 'COPANATOYAC', 'COYUCA DE BEN[IÍ]TEZ', 'COYUCA DE CATAL[AÁ]N', 'CUAJINICUILAPA', 'CUAL[AÁ]C', 'CUAUTEPEC', 'CUETZALA DEL PROGRESO', 'CUTZAMALA DE PINZ[OÓ]N', 'CHILAPA DE [AÁ]LVAREZ', 'CHILPANCINGO DE LOS BRAVO', 'FLORENCIO VILLARREAL', 'GENERAL CANUTO A. NERI', 'GENERAL HELIODORO CASTILLO', 'HUAMUXTITL[AÁ]N', 'HUITZUCO DE LOS FIGUEROA', 'IGUALA DE LA INDEPENDENCIA', 'IGUALAPA', 'IXCATEOPAN DE CUAUHT[EÉ]MOC', 'ZIHUATANEJO DE AZUETA', 'JUAN R. ESCUDERO', 'LEONARDO BRAVO', 'MALINALTEPEC', 'M[AÁ]RTIR DE CUILAPAN', 'METLAT[OÓ]NOC', 'MOCHITL[AÁ]N', 'OLINAL[AÁ]', 'OMETEPEC', 'PEDRO ASCENCIO ALQUISIRAS', 'PETATL[AÁ]N', 'PILCAYA', 'PUNGARABATO', 'QUECHULTENANGO', 'SAN LUIS ACATL[AÁ]N', 'SAN MARCOS', 'SAN MIGUEL TOTOLAPAN', 'TAXCO DE ALARC[OÓ]N', 'TECOANAPA', 'T[EÉ]CPAN DE GALEANA', 'TELOLOAPAN', 'TEPECOACUILCO DE TRUJANO', 'TETIPAC', 'TIXTLA DE GUERRERO', 'TLACOACHISTLAHUACA', 'TLACOAPA', 'TLALCHAPA', 'TLALIXTAQUILLA DE MALDONADO', 'TLAPA DE COMONFORT', 'TLAPEHUALA', 'LA UNI[OÓ]N DE ISIDORO MONTES DE OCA', 'XALPATL[AÁ]HUAC', 'XOCHIHUEHUETL[AÁ]N', 'XOCHISTLAHUACA', 'ZAPOTITL[AÁ]N TABLAS', 'ZIR[AÁ]NDARO', 'ZITLALA', 'EDUARDO NERI', 'ACATEPEC', 'MARQUELIA', 'COCHOAPA EL GRANDE', 'JOS[EÉ] JOAQU[IÍ]N DE HERRERA', 'JUCHIT[AÁ]N', 'ILIATENCO']
            patrones_ciudades = {'ACAPULCO DE JUAÁREZ': 'ACAPULCO DE JUÁREZ', 'AHUACUOTZINGO': 'AHUACUOTZINGO', 'AJUCHITLAÁN DEL PROGRESO': 'AJUCHITLÁN DEL PROGRESO', 'ALCOZAUCA DE GUERRERO': 'ALCOZAUCA DE GUERRERO', 'ALPOYECA': 'ALPOYECA', 'APAXTLA': 'APAXTLA', 'ARCELIA': 'ARCELIA', 'ATENANGO DEL RIÍO': 'ATENANGO DEL RÍO', 'ATLAMAJALCINGO DEL MONTE': 'ATLAMAJALCINGO DEL MONTE', 'ATLIXTAC': 'ATLIXTAC', 'ATOYAC DE AÁLVAREZ': 'ATOYAC DE ÁLVAREZ', 'AYUTLA DE LOS LIBRES': 'AYUTLA DE LOS LIBRES', 'AZOYUÚ': 'AZOYÚ', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'BUENAVISTA DE CUEÉLLAR': 'BUENAVISTA DE CUÉLLAR', 'COAHUAYUTLA DE JOSEÉ MARIÍA IZAZAGA': 'COAHUAYUTLA DE JOSÉ MARÍA IZAZAGA', 'COCULA': 'COCULA', 'COPALA': 'COPALA', 'COPALILLO': 'COPALILLO', 'COPANATOYAC': 'COPANATOYAC', 'COYUCA DE BENIÍTEZ': 'COYUCA DE BENÍTEZ', 'COYUCA DE CATALAÁN': 'COYUCA DE CATALÁN', 'CUAJINICUILAPA': 'CUAJINICUILAPA', 'CUALAÁC': 'CUALÁC', 'CUAUTEPEC': 'CUAUTEPEC', 'CUETZALA DEL PROGRESO': 'CUETZALA DEL PROGRESO', 'CUTZAMALA DE PINZOÓN': 'CUTZAMALA DE PINZÓN', 'CHILAPA DE AÁLVAREZ': 'CHILAPA DE ÁLVAREZ', 'CHILPANCINGO DE LOS BRAVO': 'CHILPANCINGO DE LOS BRAVO', 'FLORENCIO VILLARREAL': 'FLORENCIO VILLARREAL', 'GENERAL CANUTO A. NERI': 'GENERAL CANUTO A. NERI', 'GENERAL HELIODORO CASTILLO': 'GENERAL HELIODORO CASTILLO', 'HUAMUXTITLAÁN': 'HUAMUXTITLÁN', 'HUITZUCO DE LOS FIGUEROA': 'HUITZUCO DE LOS FIGUEROA', 'IGUALA DE LA INDEPENDENCIA': 'IGUALA DE LA INDEPENDENCIA', 'IGUALAPA': 'IGUALAPA', 'IXCATEOPAN DE CUAUHTEÉMOC': 'IXCATEOPAN DE CUAUHTÉMOC', 'ZIHUATANEJO DE AZUETA': 'ZIHUATANEJO DE AZUETA', 'JUAN R. ESCUDERO': 'JUAN R. ESCUDERO', 'LEONARDO BRAVO': 'LEONARDO BRAVO', 'MALINALTEPEC': 'MALINALTEPEC', 'MAÁRTIR DE CUILAPAN': 'MÁRTIR DE CUILAPAN', 'METLATOÓNOC': 'METLATÓNOC', 'MOCHITLAÁN': 'MOCHITLÁN', 'OLINALAÁ': 'OLINALÁ', 'OMETEPEC': 'OMETEPEC', 'PEDRO ASCENCIO ALQUISIRAS': 'PEDRO ASCENCIO ALQUISIRAS', 'PETATLAÁN': 'PETATLÁN', 'PILCAYA': 'PILCAYA', 'PUNGARABATO': 'PUNGARABATO', 'QUECHULTENANGO': 'QUECHULTENANGO', 'SAN LUIS ACATLAÁN': 'SAN LUIS ACATLÁN', 'SAN MARCOS': 'SAN MARCOS', 'SAN MIGUEL TOTOLAPAN': 'SAN MIGUEL TOTOLAPAN', 'TAXCO DE ALARCOÓN': 'TAXCO DE ALARCÓN', 'TECOANAPA': 'TECOANAPA', 'TEÉCPAN DE GALEANA': 'TÉCPAN DE GALEANA', 'TELOLOAPAN': 'TELOLOAPAN', 'TEPECOACUILCO DE TRUJANO': 'TEPECOACUILCO DE TRUJANO', 'TETIPAC': 'TETIPAC', 'TIXTLA DE GUERRERO': 'TIXTLA DE GUERRERO', 'TLACOACHISTLAHUACA': 'TLACOACHISTLAHUACA', 'TLACOAPA': 'TLACOAPA', 'TLALCHAPA': 'TLALCHAPA', 'TLALIXTAQUILLA DE MALDONADO': 'TLALIXTAQUILLA DE MALDONADO', 'TLAPA DE COMONFORT': 'TLAPA DE COMONFORT', 'TLAPEHUALA': 'TLAPEHUALA', 'LA UNIOÓN DE ISIDORO MONTES DE OCA': 'LA UNIÓN DE ISIDORO MONTES DE OCA', 'XALPATLAÁHUAC': 'XALPATLÁHUAC', 'XOCHIHUEHUETLAÁN': 'XOCHIHUEHUETLÁN', 'XOCHISTLAHUACA': 'XOCHISTLAHUACA', 'ZAPOTITLAÁN TABLAS': 'ZAPOTITLÁN TABLAS', 'ZIRAÁNDARO': 'ZIRÁNDARO', 'ZITLALA': 'ZITLALA', 'EDUARDO NERI': 'EDUARDO NERI', 'ACATEPEC': 'ACATEPEC', 'MARQUELIA': 'MARQUELIA', 'COCHOAPA EL GRANDE': 'COCHOAPA EL GRANDE', 'JOSEÉ JOAQUIÍN DE HERRERA': 'JOSÉ JOAQUÍN DE HERRERA', 'JUCHITAÁN': 'JUCHITÁN', 'ILIATENCO': 'ILIATENCO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'HIDAL', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACATL[AÁ]N', 'ACAXOCHITL[AÁ]N', 'ACTOPAN', 'AGUA BLANCA DE ITURBIDE', 'AJACUBA', 'ALFAJAYUCAN', 'ALMOLOYA', 'APAN', 'EL ARENAL', 'ATITALAQUIA', 'ATLAPEXCO', 'ATOTONILCO EL GRANDE', 'ATOTONILCO DE TULA', 'CALNALI', 'CARDONAL', 'CUAUTEPEC DE HINOJOSA', 'CHAPANTONGO', 'CHAPULHUAC[AÁ]N', 'CHILCUAUTLA', 'ELOXOCHITL[AÁ]N', 'EMILIANO ZAPATA', 'EPAZOYUCAN', 'FRANCISCO I. MADERO', 'HUASCA DE OCAMPO', 'HUAUTLA', 'HUAZALINGO', 'HUEHUETLA', 'HUEJUTLA DE REYES', 'HUICHAPAN', 'IXMIQUILPAN', 'JACALA DE LEDEZMA', 'JALTOC[AÁ]N', 'JU[AÁ]REZ HIDALGO', 'LOLOTLA', 'METEPEC', 'SAN AGUST[IÍ]N METZQUITITL[AÁ]N', 'METZTITL[AÁ]N', 'MINERAL DEL CHICO', 'MINERAL DEL MONTE', 'LA MISI[OÓ]N', 'MIXQUIAHUALA DE JU[AÁ]REZ', 'MOLANGO DE ESCAMILLA', 'NICOL[AÁ]S FLORES', 'NOPALA DE VILLAGR[AÁ]N', 'OMITL[AÁ]N DE JU[AÁ]REZ', 'SAN FELIPE ORIZATL[AÁ]N', 'PACULA', 'PACHUCA DE SOTO', 'PISAFLORES', 'PROGRESO DE OBREG[OÓ]N', 'MINERAL DE LA REFORMA', 'SAN AGUST[IÍ]N TLAXIACA', 'SAN BARTOLO TUTOTEPEC', 'SAN SALVADOR', 'SANTIAGO DE ANAYA', 'SANTIAGO TULANTEPEC DE LUGO GUERRERO', 'SINGUILUCAN', 'TASQUILLO', 'TECOZAUTLA', 'TENANGO DE DORIA', 'TEPEAPULCO', 'TEPEHUAC[AÁ]N DE GUERRERO', 'TEPEJI DEL R[IÍ]O DE OCAMPO', 'TEPETITL[AÁ]N', 'TETEPANGO', 'VILLA DE TEZONTEPEC', 'TEZONTEPEC DE ALDAMA', 'TIANGUISTENGO', 'TIZAYUCA', 'TLAHUELILPAN', 'TLAHUILTEPA', 'TLANALAPA', 'TLANCHINOL', 'TLAXCOAPAN', 'TOLCAYUCA', 'TULA DE ALLENDE', 'TULANCINGO DE BRAVO', 'XOCHIATIPAN', 'XOCHICOATL[AÁ]N', 'YAHUALICA', 'ZACUALTIP[AÁ]N DE [AÁ]NGELES', 'ZAPOTL[AÁ]N DE JU[AÁ]REZ', 'ZEMPOALA', 'ZIMAP[AÁ]N']
            patrones_ciudades = {'ACATLAÁN': 'ACATLÁN', 'ACAXOCHITLAÁN': 'ACAXOCHITLÁN', 'ACTOPAN': 'ACTOPAN', 'AGUA BLANCA DE ITURBIDE': 'AGUA BLANCA DE ITURBIDE', 'AJACUBA': 'AJACUBA', 'ALFAJAYUCAN': 'ALFAJAYUCAN', 'ALMOLOYA': 'ALMOLOYA', 'APAN': 'APAN', 'EL ARENAL': 'EL ARENAL', 'ATITALAQUIA': 'ATITALAQUIA', 'ATLAPEXCO': 'ATLAPEXCO', 'ATOTONILCO EL GRANDE': 'ATOTONILCO EL GRANDE', 'ATOTONILCO DE TULA': 'ATOTONILCO DE TULA', 'CALNALI': 'CALNALI', 'CARDONAL': 'CARDONAL', 'CUAUTEPEC DE HINOJOSA': 'CUAUTEPEC DE HINOJOSA', 'CHAPANTONGO': 'CHAPANTONGO', 'CHAPULHUACAÁN': 'CHAPULHUACÁN', 'CHILCUAUTLA': 'CHILCUAUTLA', 'ELOXOCHITLAÁN': 'ELOXOCHITLÁN', 'EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'EPAZOYUCAN': 'EPAZOYUCAN', 'FRANCISCO I. MADERO': 'FRANCISCO I. MADERO', 'HUASCA DE OCAMPO': 'HUASCA DE OCAMPO', 'HUAUTLA': 'HUAUTLA', 'HUAZALINGO': 'HUAZALINGO', 'HUEHUETLA': 'HUEHUETLA', 'HUEJUTLA DE REYES': 'HUEJUTLA DE REYES', 'HUICHAPAN': 'HUICHAPAN', 'IXMIQUILPAN': 'IXMIQUILPAN', 'JACALA DE LEDEZMA': 'JACALA DE LEDEZMA', 'JALTOCAÁN': 'JALTOCÁN', 'JUAÁREZ HIDALGO': 'JUÁREZ HIDALGO', 'LOLOTLA': 'LOLOTLA', 'METEPEC': 'METEPEC', 'SAN AGUSTIÍN METZQUITITLAÁN': 'SAN AGUSTÍN METZQUITITLÁN', 'METZTITLAÁN': 'METZTITLÁN', 'MINERAL DEL CHICO': 'MINERAL DEL CHICO', 'MINERAL DEL MONTE': 'MINERAL DEL MONTE', 'LA MISIOÓN': 'LA MISIÓN', 'MIXQUIAHUALA DE JUAÁREZ': 'MIXQUIAHUALA DE JUÁREZ', 'MOLANGO DE ESCAMILLA': 'MOLANGO DE ESCAMILLA', 'NICOLAÁS FLORES': 'NICOLÁS FLORES', 'NOPALA DE VILLAGRAÁN': 'NOPALA DE VILLAGRÁN', 'OMITLAÁN DE JUAÁREZ': 'OMITLÁN DE JUÁREZ', 'SAN FELIPE ORIZATLAÁN': 'SAN FELIPE ORIZATLÁN', 'PACULA': 'PACULA', 'PACHUCA DE SOTO': 'PACHUCA DE SOTO', 'PISAFLORES': 'PISAFLORES', 'PROGRESO DE OBREGOÓN': 'PROGRESO DE OBREGÓN', 'MINERAL DE LA REFORMA': 'MINERAL DE LA REFORMA', 'SAN AGUSTIÍN TLAXIACA': 'SAN AGUSTÍN TLAXIACA', 'SAN BARTOLO TUTOTEPEC': 'SAN BARTOLO TUTOTEPEC', 'SAN SALVADOR': 'SAN SALVADOR', 'SANTIAGO DE ANAYA': 'SANTIAGO DE ANAYA', 'SANTIAGO TULANTEPEC DE LUGO GUERRERO': 'SANTIAGO TULANTEPEC DE LUGO GUERRERO', 'SINGUILUCAN': 'SINGUILUCAN', 'TASQUILLO': 'TASQUILLO', 'TECOZAUTLA': 'TECOZAUTLA', 'TENANGO DE DORIA': 'TENANGO DE DORIA', 'TEPEAPULCO': 'TEPEAPULCO', 'TEPEHUACAÁN DE GUERRERO': 'TEPEHUACÁN DE GUERRERO', 'TEPEJI DEL RIÍO DE OCAMPO': 'TEPEJI DEL RÍO DE OCAMPO', 'TEPETITLAÁN': 'TEPETITLÁN', 'TETEPANGO': 'TETEPANGO', 'VILLA DE TEZONTEPEC': 'VILLA DE TEZONTEPEC', 'TEZONTEPEC DE ALDAMA': 'TEZONTEPEC DE ALDAMA', 'TIANGUISTENGO': 'TIANGUISTENGO', 'TIZAYUCA': 'TIZAYUCA', 'TLAHUELILPAN': 'TLAHUELILPAN', 'TLAHUILTEPA': 'TLAHUILTEPA', 'TLANALAPA': 'TLANALAPA', 'TLANCHINOL': 'TLANCHINOL', 'TLAXCOAPAN': 'TLAXCOAPAN', 'TOLCAYUCA': 'TOLCAYUCA', 'TULA DE ALLENDE': 'TULA DE ALLENDE', 'TULANCINGO DE BRAVO': 'TULANCINGO DE BRAVO', 'XOCHIATIPAN': 'XOCHIATIPAN', 'XOCHICOATLAÁN': 'XOCHICOATLÁN', 'YAHUALICA': 'YAHUALICA', 'ZACUALTIPAÁN DE AÁNGELES': 'ZACUALTIPÁN DE ÁNGELES', 'ZAPOTLAÁN DE JUAÁREZ': 'ZAPOTLÁN DE JUÁREZ', 'ZEMPOALA': 'ZEMPOALA', 'ZIMAPAÁN': 'ZIMAPÁN'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'JALI', estado_republica, re.IGNORECASE): 
            ciudades_clave = ['ACATIC', 'ACATL[AÁ]N DE JU[AÁ]REZ', 'AHUALULCO DE MERCADO', 'AMACUECA', 'AMATIT[AÁ]N', 'AMECA', 'SAN JUANITO DE ESCOBEDO', 'ARANDAS', 'EL ARENAL', 'ATEMAJAC DE BRIZUELA', 'ATENGO', 'ATENGUILLO', 'ATOTONILCO EL ALTO', 'ATOYAC', 'AUTL[AÁ]N DE NAVARRO', 'AYOTL[AÁ]N', 'AYUTLA', 'LA BARCA', 'BOLAÑOS', 'CABO CORRIENTES', 'CASIMIRO CASTILLO', 'CIHUATL[AÁ]N', 'ZAPOTL[AÁ]N EL GRANDE', 'COCULA', 'COLOTL[AÁ]N', 'CONCEPCI[OÓ]N DE BUENOS AIRES', 'CUAUTITL[AÁ]N DE GARC[IÍ]A BARRAG[AÁ]N', 'CUAUTLA', 'CUQU[IÍ]O', 'CHAPALA', 'CHIMALTIT[AÁ]N', 'CHIQUILISTL[AÁ]N', 'DEGOLLADO', 'EJUTLA', 'ENCARNACI[OÓ]N DE D[IÍ]AZ', 'ETZATL[AÁ]N', 'EL GRULLO', 'GUACHINANGO', 'GUADALAJARA', 'HOSTOTIPAQUILLO', 'HUEJ[UÚ]CAR', 'HUEJUQUILLA EL ALTO', 'LA HUERTA', 'IXTLAHUAC[AÁ]N DE LOS MEMBRILLOS', 'IXTLAHUAC[AÁ]N DEL R[IÍ]O', 'JALOSTOTITL[AÁ]N', 'JAMAY', 'JES[UÚ]S MAR[IÍ]A', 'JILOTL[AÁ]N DE LOS DOLORES', 'JOCOTEPEC', 'JUANACATL[AÁ]N', 'JUCHITL[AÁ]N', 'LAGOS DE MORENO', 'EL LIM[OÓ]N', 'MAGDALENA', 'SANTA MAR[IÍ]A DEL ORO', 'LA MANZANILLA DE LA PAZ', 'MASCOTA', 'MAZAMITLA', 'MEXTICAC[AÁ]N', 'MEZQUITIC', 'MIXTL[AÁ]N', 'OCOTL[AÁ]N', 'OJUELOS DE JALISCO', 'PIHUAMO', 'PONCITL[AÁ]N', 'PUERTO VALLARTA', 'VILLA PURIFICACI[OÓ]N', 'QUITUPAN', 'EL SALTO', 'SAN CRIST[OÓ]BAL DE LA BARRANCA', 'SAN DIEGO DE ALEJANDR[IÍ]A', 'SAN JUAN DE LOS LAGOS', 'SAN JULI[AÁ]N', 'SAN MARCOS', 'SAN MART[IÍ]N DE BOLAÑOS', 'SAN MART[IÍ]N HIDALGO', 'SAN MIGUEL EL ALTO', 'G[OÓ]MEZ FAR[IÍ]AS', 'SAN SEBASTI[AÁ]N DEL OESTE', 'SANTA MAR[IÍ]A DE LOS [AÁ]NGELES', 'SAYULA', 'TALA', 'TALPA DE ALLENDE', 'TAMAZULA DE GORDIANO', 'TAPALPA', 'TECALITL[AÁ]N', 'TECHALUTA DE MONTENEGRO', 'TECOLOTL[AÁ]N', 'TENAMAXTL[AÁ]N', 'TEOCALTICHE', 'TEOCUITATL[AÁ]N DE CORONA', 'TEPATITL[AÁ]N DE MORELOS', 'TEQUILA', 'TEUCHITL[AÁ]N', 'TIZAP[AÁ]N EL ALTO', 'TLAJOMULCO', 'SAN PEDRO TLAQUEPAQUE', 'TOLIM[AÁ]N', 'TOMATL[AÁ]N', 'TONAL[AÁ]', 'TONAYA', 'TONILA', 'TOTATICHE', 'TOTOTL[AÁ]N', 'TUXCACUESCO', 'TUXCUECA', 'TUXPAN', 'UNI[OÓ]N DE SAN ANTONIO', 'UNI[OÓ]N DE TULA', 'VALLE DE GUADALUPE', 'VALLE DE JU[AÁ]REZ', 'SAN GABRIEL', 'VILLA CORONA', 'VILLA GUERRERO', 'VILLA HIDALGO', 'CAÑADAS DE OBREG[OÓ]N', 'YAHUALICA DE GONZ[AÁ]LEZ GALLO', 'ZACOALCO DE TORRES', 'ZAPOPAN', 'ZAPOTILTIC', 'ZAPOTITL[AÁ]N DE VADILLO', 'ZAPOTL[AÁ]N DEL REY', 'ZAPOTLANEJO', 'SAN IGNACIO CERRO GORDO']
            patrones_ciudades = {'ACATIC': 'ACATIC', 'ACATLAÁN DE JUAÁREZ': 'ACATLÁN DE JUÁREZ', 'AHUALULCO DE MERCADO': 'AHUALULCO DE MERCADO', 'AMACUECA': 'AMACUECA', 'AMATITAÁN': 'AMATITÁN', 'AMECA': 'AMECA', 'SAN JUANITO DE ESCOBEDO': 'SAN JUANITO DE ESCOBEDO', 'ARANDAS': 'ARANDAS', 'EL ARENAL': 'EL ARENAL', 'ATEMAJAC DE BRIZUELA': 'ATEMAJAC DE BRIZUELA', 'ATENGO': 'ATENGO', 'ATENGUILLO': 'ATENGUILLO', 'ATOTONILCO EL ALTO': 'ATOTONILCO EL ALTO', 'ATOYAC': 'ATOYAC', 'AUTLAÁN DE NAVARRO': 'AUTLÁN DE NAVARRO', 'AYOTLAÁN': 'AYOTLÁN', 'AYUTLA': 'AYUTLA', 'LA BARCA': 'LA BARCA', 'BOLAÑOS': 'BOLAÑOS', 'CABO CORRIENTES': 'CABO CORRIENTES', 'CASIMIRO CASTILLO': 'CASIMIRO CASTILLO', 'CIHUATLAÁN': 'CIHUATLÁN', 'ZAPOTLAÁN EL GRANDE': 'ZAPOTLÁN EL GRANDE', 'COCULA': 'COCULA', 'COLOTLAÁN': 'COLOTLÁN', 'CONCEPCIOÓN DE BUENOS AIRES': 'CONCEPCIÓN DE BUENOS AIRES', 'CUAUTITLAÁN DE GARCIÍA BARRAGAÁN': 'CUAUTITLÁN DE GARCÍA BARRAGÁN', 'CUAUTLA': 'CUAUTLA', 'CUQUIÍO': 'CUQUÍO', 'CHAPALA': 'CHAPALA', 'CHIMALTITAÁN': 'CHIMALTITÁN', 'CHIQUILISTLAÁN': 'CHIQUILISTLÁN', 'DEGOLLADO': 'DEGOLLADO', 'EJUTLA': 'EJUTLA', 'ENCARNACIOÓN DE DIÍAZ': 'ENCARNACIÓN DE DÍAZ', 'ETZATLAÁN': 'ETZATLÁN', 'EL GRULLO': 'EL GRULLO', 'GUACHINANGO': 'GUACHINANGO', 'GUADALAJARA': 'GUADALAJARA', 'HOSTOTIPAQUILLO': 'HOSTOTIPAQUILLO', 'HUEJUÚCAR': 'HUEJÚCAR', 'HUEJUQUILLA EL ALTO': 'HUEJUQUILLA EL ALTO', 'LA HUERTA': 'LA HUERTA', 'IXTLAHUACAÁN DE LOS MEMBRILLOS': 'IXTLAHUACÁN DE LOS MEMBRILLOS', 'IXTLAHUACAÁN DEL RIÍO': 'IXTLAHUACÁN DEL RÍO', 'JALOSTOTITLAÁN': 'JALOSTOTITLÁN', 'JAMAY': 'JAMAY', 'JESUÚS MARIÍA': 'JESÚS MARÍA', 'JILOTLAÁN DE LOS DOLORES': 'JILOTLÁN DE LOS DOLORES', 'JOCOTEPEC': 'JOCOTEPEC', 'JUANACATLAÁN': 'JUANACATLÁN', 'JUCHITLAÁN': 'JUCHITLÁN', 'LAGOS DE MORENO': 'LAGOS DE MORENO', 'EL LIMOÓN': 'EL LIMÓN', 'MAGDALENA': 'MAGDALENA', 'SANTA MARIÍA DEL ORO': 'SANTA MARÍA DEL ORO', 'LA MANZANILLA DE LA PAZ': 'LA MANZANILLA DE LA PAZ', 'MASCOTA': 'MASCOTA', 'MAZAMITLA': 'MAZAMITLA', 'MEXTICACAÁN': 'MEXTICACÁN', 'MEZQUITIC': 'MEZQUITIC', 'MIXTLAÁN': 'MIXTLÁN', 'OCOTLAÁN': 'OCOTLÁN', 'OJUELOS DE JALISCO': 'OJUELOS DE JALISCO', 'PIHUAMO': 'PIHUAMO', 'PONCITLAÁN': 'PONCITLÁN', 'PUERTO VALLARTA': 'PUERTO VALLARTA', 'VILLA PURIFICACIOÓN': 'VILLA PURIFICACIÓN', 'QUITUPAN': 'QUITUPAN', 'EL SALTO': 'EL SALTO', 'SAN CRISTOÓBAL DE LA BARRANCA': 'SAN CRISTÓBAL DE LA BARRANCA', 'SAN DIEGO DE ALEJANDRIÍA': 'SAN DIEGO DE ALEJANDRÍA', 'SAN JUAN DE LOS LAGOS': 'SAN JUAN DE LOS LAGOS', 'SAN JULIAÁN': 'SAN JULIÁN', 'SAN MARCOS': 'SAN MARCOS', 'SAN MARTIÍN DE BOLAÑOS': 'SAN MARTÍN DE BOLAÑOS', 'SAN MARTIÍN HIDALGO': 'SAN MARTÍN HIDALGO', 'SAN MIGUEL EL ALTO': 'SAN MIGUEL EL ALTO', 'GOÓMEZ FARIÍAS': 'GÓMEZ FARÍAS', 'SAN SEBASTIAÁN DEL OESTE': 'SAN SEBASTIÁN DEL OESTE', 'SANTA MARIÍA DE LOS AÁNGELES': 'SANTA MARÍA DE LOS ÁNGELES', 'SAYULA': 'SAYULA', 'TALA': 'TALA', 'TALPA DE ALLENDE': 'TALPA DE ALLENDE', 'TAMAZULA DE GORDIANO': 'TAMAZULA DE GORDIANO', 'TAPALPA': 'TAPALPA', 'TECALITLAÁN': 'TECALITLÁN', 'TECHALUTA DE MONTENEGRO': 'TECHALUTA DE MONTENEGRO', 'TECOLOTLAÁN': 'TECOLOTLÁN', 'TENAMAXTLAÁN': 'TENAMAXTLÁN', 'TEOCALTICHE': 'TEOCALTICHE', 'TEOCUITATLAÁN DE CORONA': 'TEOCUITATLÁN DE CORONA', 'TEPATITLAÁN DE MORELOS': 'TEPATITLÁN DE MORELOS', 'TEQUILA': 'TEQUILA', 'TEUCHITLAÁN': 'TEUCHITLÁN', 'TIZAPAÁN EL ALTO': 'TIZAPÁN EL ALTO', 'TLAJOMULCO': 'TLAJOMULCO DE ZÚÑIGA', 'SAN PEDRO TLAQUEPAQUE': 'SAN PEDRO TLAQUEPAQUE', 'TOLIMAÁN': 'TOLIMÁN', 'TOMATLAÁN': 'TOMATLÁN', 'TONALAÁ': 'TONALÁ', 'TONAYA': 'TONAYA', 'TONILA': 'TONILA', 'TOTATICHE': 'TOTATICHE', 'TOTOTLAÁN': 'TOTOTLÁN', 'TUXCACUESCO': 'TUXCACUESCO', 'TUXCUECA': 'TUXCUECA', 'TUXPAN': 'TUXPAN', 'UNIOÓN DE SAN ANTONIO': 'UNIÓN DE SAN ANTONIO', 'UNIOÓN DE TULA': 'UNIÓN DE TULA', 'VALLE DE GUADALUPE': 'VALLE DE GUADALUPE', 'VALLE DE JUAÁREZ': 'VALLE DE JUÁREZ', 'SAN GABRIEL': 'SAN GABRIEL', 'VILLA CORONA': 'VILLA CORONA', 'VILLA GUERRERO': 'VILLA GUERRERO', 'VILLA HIDALGO': 'VILLA HIDALGO', 'CAÑADAS DE OBREGOÓN': 'CAÑADAS DE OBREGÓN', 'YAHUALICA DE GONZAÁLEZ GALLO': 'YAHUALICA DE GONZÁLEZ GALLO', 'ZACOALCO DE TORRES': 'ZACOALCO DE TORRES', 'ZAPOPAN': 'ZAPOPAN', 'ZAPOTILTIC': 'ZAPOTILTIC', 'ZAPOTITLAÁN DE VADILLO': 'ZAPOTITLÁN DE VADILLO', 'ZAPOTLAÁN DEL REY': 'ZAPOTLÁN DEL REY', 'ZAPOTLANEJO': 'ZAPOTLANEJO', 'SAN IGNACIO CERRO GORDO': 'SAN IGNACIO CERRO GORDO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'MICHO', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACUITZIO', 'AGUILILLA', '[AÁ]LVARO OBREG[OÓ]N', 'ANGAMACUTIRO', 'ANGANGUEO', 'APATZING[AÁ]N', 'APORO', 'AQUILA', 'ARIO', 'ARTEAGA', 'BRISEÑAS', 'BUENAVISTA', 'CAR[AÁ]CUARO', 'COAHUAYANA', 'COALCOM[AÁ]N DE V[AÁ]ZQUEZ PALLARES', 'COENEO', 'CONTEPEC', 'COP[AÁ]NDARO', 'COTIJA', 'CUITZEO', 'CHARAPAN', 'CHARO', 'CHAVINDA', 'CHER[AÁ]N', 'CHILCHOTA', 'CHINICUILA', 'CHUC[AÁ]NDIRO', 'CHURINTZIO', 'CHURUMUCO', 'ECUANDUREO', 'EPITACIO HUERTA', 'ERONGAR[IÍ]CUARO', 'GABRIEL ZAMORA', 'HIDALGO', 'LA HUACANA', 'HUANDACAREO', 'HUANIQUEO', 'HUETAMO', 'HUIRAMBA', 'INDAPARAPEO', 'IRIMBO', 'IXTL[AÁ]N', 'JACONA', 'JIM[EÉ]NEZ', 'JIQUILPAN', 'JU[AÁ]REZ', 'JUNGAPEO', 'LAGUNILLAS', 'MADERO', 'MARAVAT[IÍ]O', 'MARCOS CASTELLANOS', 'L[AÁ]ZARO C[AÁ]RDENAS', 'MORELIA', 'MORELOS', 'M[UÚ]GICA', 'NAHUATZEN', 'NOCUP[EÉ]TARO', 'NUEVO PARANGARICUTIRO', 'NUEVO URECHO', 'NUMAR[AÁ]N', 'OCAMPO', 'PAJACUAR[AÁ]N', 'PANIND[IÍ]CUARO', 'PAR[AÁ]CUARO', 'PARACHO', 'P[AÁ]TZCUARO', 'PENJAMILLO', 'PERIB[AÁ]N', 'LA PIEDAD', 'PUR[EÉ]PERO', 'PURU[AÁ]NDIRO', 'QUER[EÉ]NDARO', 'QUIROGA', 'COJUMATL[AÁ]N DE R[EÉ]GULES', 'LOS REYES', 'SAHUAYO', 'SAN LUCAS', 'SANTA ANA MAYA', 'SALVADOR ESCALANTE', 'SENGUIO', 'SUSUPUATO', 'TAC[AÁ]MBARO', 'TANC[IÍ]TARO', 'TANGAMANDAPIO', 'TANGANC[IÍ]CUARO', 'TANHUATO', 'TARETAN', 'TAR[IÍ]MBARO', 'TEPALCATEPEC', 'TINGAMBATO', 'TINGÜIND[IÍ]N', 'TIQUICHEO DE NICOL[AÁ]S ROMERO', 'TLALPUJAHUA', 'TLAZAZALCA', 'TOCUMBO', 'TUMBISCAT[IÍ]O', 'TURICATO', 'TUXPAN', 'TUZANTLA', 'TZINTZUNTZAN', 'TZITZIO', 'URUAPAN', 'VENUSTIANO CARRANZA', 'VILLAMAR', 'VISTA HERMOSA', 'YUR[EÉ]CUARO', 'ZACAPU', 'ZAMORA', 'ZIN[AÁ]PARO', 'ZINAP[EÉ]CUARO', 'ZIRACUARETIRO', 'ZIT[AÁ]CUARO', 'JOS[EÉ] SIXTO VERDUZCO']
            patrones_ciudades = {'ACUITZIO': 'ACUITZIO', 'AGUILILLA': 'AGUILILLA', 'AÁLVARO OBREGOÓN': 'ÁLVARO OBREGÓN', 'ANGAMACUTIRO': 'ANGAMACUTIRO', 'ANGANGUEO': 'ANGANGUEO', 'APATZINGAÁN': 'APATZINGÁN', 'APORO': 'APORO', 'AQUILA': 'AQUILA', 'ARIO': 'ARIO', 'ARTEAGA': 'ARTEAGA', 'BRISEÑAS': 'BRISEÑAS', 'BUENAVISTA': 'BUENAVISTA', 'CARAÁCUARO': 'CARÁCUARO', 'COAHUAYANA': 'COAHUAYANA', 'COALCOMAÁN DE VAÁZQUEZ PALLARES': 'COALCOMÁN DE VÁZQUEZ PALLARES', 'COENEO': 'COENEO', 'CONTEPEC': 'CONTEPEC', 'COPAÁNDARO': 'COPÁNDARO', 'COTIJA': 'COTIJA', 'CUITZEO': 'CUITZEO', 'CHARAPAN': 'CHARAPAN', 'CHARO': 'CHARO', 'CHAVINDA': 'CHAVINDA', 'CHERAÁN': 'CHERÁN', 'CHILCHOTA': 'CHILCHOTA', 'CHINICUILA': 'CHINICUILA', 'CHUCAÁNDIRO': 'CHUCÁNDIRO', 'CHURINTZIO': 'CHURINTZIO', 'CHURUMUCO': 'CHURUMUCO', 'ECUANDUREO': 'ECUANDUREO', 'EPITACIO HUERTA': 'EPITACIO HUERTA', 'ERONGARIÍCUARO': 'ERONGARÍCUARO', 'GABRIEL ZAMORA': 'GABRIEL ZAMORA', 'HIDALGO': 'HIDALGO', 'LA HUACANA': 'LA HUACANA', 'HUANDACAREO': 'HUANDACAREO', 'HUANIQUEO': 'HUANIQUEO', 'HUETAMO': 'HUETAMO', 'HUIRAMBA': 'HUIRAMBA', 'INDAPARAPEO': 'INDAPARAPEO', 'IRIMBO': 'IRIMBO', 'IXTLAÁN': 'IXTLÁN', 'JACONA': 'JACONA', 'JIMEÉNEZ': 'JIMÉNEZ', 'JIQUILPAN': 'JIQUILPAN', 'JUAÁREZ': 'JUÁREZ', 'JUNGAPEO': 'JUNGAPEO', 'LAGUNILLAS': 'LAGUNILLAS', 'MADERO': 'MADERO', 'MARAVATIÍO': 'MARAVATÍO', 'MARCOS CASTELLANOS': 'MARCOS CASTELLANOS', 'LAÁZARO CAÁRDENAS': 'LÁZARO CÁRDENAS', 'MORELIA': 'MORELIA', 'MORELOS': 'MORELOS', 'MUÚGICA': 'MÚGICA', 'NAHUATZEN': 'NAHUATZEN', 'NOCUPEÉTARO': 'NOCUPÉTARO', 'NUEVO PARANGARICUTIRO': 'NUEVO PARANGARICUTIRO', 'NUEVO URECHO': 'NUEVO URECHO', 'NUMARAÁN': 'NUMARÁN', 'OCAMPO': 'OCAMPO', 'PAJACUARAÁN': 'PAJACUARÁN', 'PANINDIÍCUARO': 'PANINDÍCUARO', 'PARAÁCUARO': 'PARÁCUARO', 'PARACHO': 'PARACHO', 'PAÁTZCUARO': 'PÁTZCUARO', 'PENJAMILLO': 'PENJAMILLO', 'PERIBAÁN': 'PERIBÁN', 'LA PIEDAD': 'LA PIEDAD', 'PUREÉPERO': 'PURÉPERO', 'PURUAÁNDIRO': 'PURUÁNDIRO', 'QUEREÉNDARO': 'QUERÉNDARO', 'QUIROGA': 'QUIROGA', 'COJUMATLAÁN DE REÉGULES': 'COJUMATLÁN DE RÉGULES', 'LOS REYES': 'LOS REYES', 'SAHUAYO': 'SAHUAYO', 'SAN LUCAS': 'SAN LUCAS', 'SANTA ANA MAYA': 'SANTA ANA MAYA', 'SALVADOR ESCALANTE': 'SALVADOR ESCALANTE', 'SENGUIO': 'SENGUIO', 'SUSUPUATO': 'SUSUPUATO', 'TACAÁMBARO': 'TACÁMBARO', 'TANCIÍTARO': 'TANCÍTARO', 'TANGAMANDAPIO': 'TANGAMANDAPIO', 'TANGANCIÍCUARO': 'TANGANCÍCUARO', 'TANHUATO': 'TANHUATO', 'TARETAN': 'TARETAN', 'TARIÍMBARO': 'TARÍMBARO', 'TEPALCATEPEC': 'TEPALCATEPEC', 'TINGAMBATO': 'TINGAMBATO', 'TINGÜINDIÍN': 'TINGÜINDÍN', 'TIQUICHEO DE NICOLAÁS ROMERO': 'TIQUICHEO DE NICOLÁS ROMERO', 'TLALPUJAHUA': 'TLALPUJAHUA', 'TLAZAZALCA': 'TLAZAZALCA', 'TOCUMBO': 'TOCUMBO', 'TUMBISCATIÍO': 'TUMBISCATÍO', 'TURICATO': 'TURICATO', 'TUXPAN': 'TUXPAN', 'TUZANTLA': 'TUZANTLA', 'TZINTZUNTZAN': 'TZINTZUNTZAN', 'TZITZIO': 'TZITZIO', 'URUAPAN': 'URUAPAN', 'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA', 'VILLAMAR': 'VILLAMAR', 'VISTA HERMOSA': 'VISTA HERMOSA', 'YUREÉCUARO': 'YURÉCUARO', 'ZACAPU': 'ZACAPU', 'ZAMORA': 'ZAMORA', 'ZINAÁPARO': 'ZINÁPARO', 'ZINAPEÉCUARO': 'ZINAPÉCUARO', 'ZIRACUARETIRO': 'ZIRACUARETIRO', 'ZITAÁCUARO': 'ZITÁCUARO', 'JOSEÉ SIXTO VERDUZCO': 'JOSÉ SIXTO VERDUZCO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'MORE', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['AMACUZAC', 'ATLATLAHUCAN', 'AXOCHIAPAN', 'AYALA', 'COATL[AÁ]N DEL R[IÍ]O', 'CUAUTLA', 'CUERNAVACA', 'EMILIANO ZAPATA', 'HUITZILAC', 'JANTETELCO', 'JIUTEPEC', 'JOJUTLA', 'JONACATEPEC DE LEANDRO VALLE', 'MAZATEPEC', 'MIACATL[AÁ]N', 'OCUITUCO', 'PUENTE DE IXTLA', 'TEMIXCO', 'TEPALCINGO', 'TEPOZTL[AÁ]N', 'TETECALA', 'TETELA DEL VOLC[AÁ]N', 'TLALNEPANTLA', 'TLALTIZAP[AÁ]N DE ZAPATA', 'TLAQUILTENANGO', 'TLAYACAPAN', 'TOTOLAPAN', 'XOCHITEPEC', 'YAUTEPEC', 'YECAPIXTLA', 'ZACATEPEC', 'ZACUALPAN DE AMILPAS', 'TEMOAC', 'COATETELCO', 'XOXOCOTLA', 'HUEYAPAN']
            patrones_ciudades = {'AMACUZAC': 'AMACUZAC', 'ATLATLAHUCAN': 'ATLATLAHUCAN', 'AXOCHIAPAN': 'AXOCHIAPAN', 'AYALA': 'AYALA', 'COATLAÁN DEL RIÍO': 'COATLÁN DEL RÍO', 'CUAUTLA': 'CUAUTLA', 'CUERNAVACA': 'CUERNAVACA', 'EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'HUITZILAC': 'HUITZILAC', 'JANTETELCO': 'JANTETELCO', 'JIUTEPEC': 'JIUTEPEC', 'JOJUTLA': 'JOJUTLA', 'JONACATEPEC DE LEANDRO VALLE': 'JONACATEPEC DE LEANDRO VALLE', 'MAZATEPEC': 'MAZATEPEC', 'MIACATLAÁN': 'MIACATLÁN', 'OCUITUCO': 'OCUITUCO', 'PUENTE DE IXTLA': 'PUENTE DE IXTLA', 'TEMIXCO': 'TEMIXCO', 'TEPALCINGO': 'TEPALCINGO', 'TEPOZTLAÁN': 'TEPOZTLÁN', 'TETECALA': 'TETECALA', 'TETELA DEL VOLCAÁN': 'TETELA DEL VOLCÁN', 'TLALNEPANTLA': 'TLALNEPANTLA', 'TLALTIZAPAÁN DE ZAPATA': 'TLALTIZAPÁN DE ZAPATA', 'TLAQUILTENANGO': 'TLAQUILTENANGO', 'TLAYACAPAN': 'TLAYACAPAN', 'TOTOLAPAN': 'TOTOLAPAN', 'XOCHITEPEC': 'XOCHITEPEC', 'YAUTEPEC': 'YAUTEPEC', 'YECAPIXTLA': 'YECAPIXTLA', 'ZACATEPEC': 'ZACATEPEC', 'ZACUALPAN DE AMILPAS': 'ZACUALPAN DE AMILPAS', 'TEMOAC': 'TEMOAC', 'COATETELCO': 'COATETELCO', 'XOXOCOTLA': 'XOXOCOTLA', 'HUEYAPAN': 'HUEYAPAN'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'NAYA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACAPONETA', 'AHUACATL[AÁ]N', 'AMATL[AÁ]N DE CAÑAS', 'COMPOSTELA', 'HUAJICORI', 'IXTL[AÁ]N DEL R[IÍ]O', 'JALA', 'XALISCO', 'DEL NAYAR', 'ROSAMORADA', 'RU[IÍ]Z', 'SAN BLAS', 'SAN PEDRO LAGUNILLAS', 'SANTA MAR[IÍ]A DEL ORO', 'SANTIAGO IXCUINTLA', 'TECUALA', 'TEPIC', 'TUXPAN', 'LA YESCA', 'BAH[IÍ]A DE BANDERAS']
            patrones_ciudades = {'ACAPONETA': 'ACAPONETA', 'AHUACATLAÁN': 'AHUACATLÁN', 'AMATLAÁN DE CAÑAS': 'AMATLÁN DE CAÑAS', 'COMPOSTELA': 'COMPOSTELA', 'HUAJICORI': 'HUAJICORI', 'IXTLAÁN DEL RIÍO': 'IXTLÁN DEL RÍO', 'JALA': 'JALA', 'XALISCO': 'XALISCO', 'DEL NAYAR': 'DEL NAYAR', 'ROSAMORADA': 'ROSAMORADA', 'RUIÍZ': 'RUÍZ', 'SAN BLAS': 'SAN BLAS', 'SAN PEDRO LAGUNILLAS': 'SAN PEDRO LAGUNILLAS', 'SANTA MARIÍA DEL ORO': 'SANTA MARÍA DEL ORO', 'SANTIAGO IXCUINTLA': 'SANTIAGO IXCUINTLA', 'TECUALA': 'TECUALA', 'TEPIC': 'TEPIC', 'TUXPAN': 'TUXPAN', 'LA YESCA': 'LA YESCA', 'BAHIÍA DE BANDERAS': 'BAHÍA DE BANDERAS'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'NUEVO', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ABASOLO', 'AGUALEGUAS', 'LOS ALDAMAS', 'ALLENDE', 'AN[AÁ]HUAC', 'APODACA', 'ARAMBERRI', 'BUSTAMANTE', 'CADEREYTA JIM[EÉ]NEZ', 'EL CARMEN', 'CERRALVO', 'CI[EÉ]NEGA DE FLORES', 'CHINA', 'DOCTOR ARROYO', 'DOCTOR COSS', 'DOCTOR GONZ[AÁ]LEZ', 'GALEANA', 'GARC[IÍ]A', 'SAN PEDRO GARZA GARC[IÍ]A', 'GENERAL BRAVO', 'GENERAL ESCOBEDO', 'GENERAL TER[AÁ]N', 'GENERAL TREVIÑO', 'GENERAL ZARAGOZA', 'GENERAL ZUAZUA', 'GUADALUPE', 'LOS HERRERAS', 'HIGUERAS', 'HUALAHUISES', 'ITURBIDE', 'JU[AÁ]REZ', 'LAMPAZOS DE NARANJO', 'LINARES', 'MAR[IÍ]N', 'MELCHOR OCAMPO', 'MIER Y NORIEGA', 'MINA', 'MONTEMORELOS', 'MONTERREY', 'PAR[AÁ]S', 'PESQUER[IÍ]A', 'LOS RAMONES', 'RAYONES', 'SABINAS HIDALGO', 'SALINAS VICTORIA', 'SAN NICOL[AÁ]S DE LOS GARZA', 'HIDALGO', 'SANTA CATARINA', 'SANTIAGO', 'VALLECILLO', 'VILLALDAMA']
            patrones_ciudades = {'ABASOLO': 'ABASOLO', 'AGUALEGUAS': 'AGUALEGUAS', 'LOS ALDAMAS': 'LOS ALDAMAS', 'ALLENDE': 'ALLENDE', 'ANAÁHUAC': 'ANÁHUAC', 'APODACA': 'APODACA', 'ARAMBERRI': 'ARAMBERRI', 'BUSTAMANTE': 'BUSTAMANTE', 'CADEREYTA JIMEÉNEZ': 'CADEREYTA JIMÉNEZ', 'EL CARMEN': 'EL CARMEN', 'CERRALVO': 'CERRALVO', 'CIEÉNEGA DE FLORES': 'CIÉNEGA DE FLORES', 'CHINA': 'CHINA', 'DOCTOR ARROYO': 'DOCTOR ARROYO', 'DOCTOR COSS': 'DOCTOR COSS', 'DOCTOR GONZAÁLEZ': 'DOCTOR GONZÁLEZ', 'GALEANA': 'GALEANA', 'GARCIÍA': 'GARCÍA', 'SAN PEDRO GARZA GARCIÍA': 'SAN PEDRO GARZA GARCÍA', 'GENERAL BRAVO': 'GENERAL BRAVO', 'GENERAL ESCOBEDO': 'GENERAL ESCOBEDO', 'GENERAL TERAÁN': 'GENERAL TERÁN', 'GENERAL TREVIÑO': 'GENERAL TREVIÑO', 'GENERAL ZARAGOZA': 'GENERAL ZARAGOZA', 'GENERAL ZUAZUA': 'GENERAL ZUAZUA', 'GUADALUPE': 'GUADALUPE', 'LOS HERRERAS': 'LOS HERRERAS', 'HIGUERAS': 'HIGUERAS', 'HUALAHUISES': 'HUALAHUISES', 'ITURBIDE': 'ITURBIDE', 'JUAÁREZ': 'JUÁREZ', 'LAMPAZOS DE NARANJO': 'LAMPAZOS DE NARANJO', 'LINARES': 'LINARES', 'MARIÍN': 'MARÍN', 'MELCHOR OCAMPO': 'MELCHOR OCAMPO', 'MIER Y NORIEGA': 'MIER Y NORIEGA', 'MINA': 'MINA', 'MONTEMORELOS': 'MONTEMORELOS', 'MONTERREY': 'MONTERREY', 'PARAÁS': 'PARÁS', 'PESQUERIÍA': 'PESQUERÍA', 'LOS RAMONES': 'LOS RAMONES', 'RAYONES': 'RAYONES', 'SABINAS HIDALGO': 'SABINAS HIDALGO', 'SALINAS VICTORIA': 'SALINAS VICTORIA', 'SAN NICOLAÁS DE LOS GARZA': 'SAN NICOLÁS DE LOS GARZA', 'HIDALGO': 'HIDALGO', 'SANTA CATARINA': 'SANTA CATARINA', 'SANTIAGO': 'SANTIAGO', 'VALLECILLO': 'VALLECILLO', 'VILLALDAMA': 'VILLALDAMA'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'OAX', estado_republica, re.IGNORECASE): 
            ciudades_clave = [ 'ABEJONES', 'ACATL[AÁ]N DE P[EÉ]REZ FIGUEROA', 'ASUNCI[OÓ]N CACALOTEPEC', 'ASUNCI[OÓ]N CUYOTEPEJI', 'ASUNCI[OÓ]N IXTALTEPEC', 'ASUNCI[OÓ]N NOCHIXTL[AÁ]N', 'ASUNCI[OÓ]N OCOTL[AÁ]N', 'ASUNCI[OÓ]N TLACOLULITA', 'AYOTZINTEPEC', 'EL BARRIO DE LA SOLEDAD', 'CALIHUAL[AÁ]', 'CANDELARIA LOXICHA', 'CI[EÉ]NEGA DE ZIMATL[AÁ]N', 'CIUDAD IXTEPEC', 'COATECAS ALTAS', 'COICOY[AÁ]N DE LAS FLORES', 'LA COMPAÑ[IÍ]A', 'CONCEPCI[OÓ]N BUENAVISTA', 'CONCEPCI[OÓ]N P[AÁ]PALO', 'CONSTANCIA DEL ROSARIO', 'COSOLAPA', 'COSOLTEPEC', 'CUIL[AÁ]PAM DE GUERRERO', 'CUYAMECALCO VILLA DE ZARAGOZA', 'CHAHUITES', 'CHALCATONGO DE HIDALGO', 'CHIQUIHUITL[AÁ]N DE BENITO JU[AÁ]REZ', 'HEROICA CIUDAD DE EJUTLA DE CRESPO', 'ELOXOCHITL[AÁ]N DE FLORES MAG[OÓ]N', 'EL ESPINAL', 'TAMAZUL[AÁ]PAM DEL ESP[IÍ]RITU SANTO', 'FRESNILLO DE TRUJANO', 'GUADALUPE ETLA', 'GUADALUPE DE RAM[IÍ]REZ', 'GUELATAO DE JU[AÁ]REZ', 'GUEVEA DE HUMBOLDT', 'MESONES HIDALGO', 'VILLA HIDALGO', 'HEROICA CIUDAD DE HUAJUAPAN DE LE[OÓ]N', 'HUAUTEPEC', 'HUAUTLA DE JIM[EÉ]NEZ', 'IXTL[AÁ]N DE JU[AÁ]REZ', 'JUCHIT[AÁ]N DE ZARAGOZA', 'LOMA BONITA', 'MAGDALENA APASCO', 'MAGDALENA JALTEPEC', 'SANTA MAGDALENA JICOTL[AÁ]N', 'MAGDALENA MIXTEPEC', 'MAGDALENA OCOTL[AÁ]N', 'MAGDALENA PEÑASCO', 'MAGDALENA TEITIPAC', 'MAGDALENA TEQUISISTL[AÁ]N', 'MAGDALENA TLACOTEPEC', 'MAGDALENA ZAHUATL[AÁ]N', 'MARISCALA DE JU[AÁ]REZ', 'M[AÁ]RTIRES DE TACUBAYA', 'MAT[IÍ]AS ROMERO AVENDAÑO', 'MAZATL[AÁ]N VILLA DE FLORES', 'MIAHUATL[AÁ]N DE PORFIRIO D[IÍ]AZ', 'MIXISTL[AÁ]N DE LA REFORMA', 'MONJAS', 'NATIVIDAD', 'NAZARENO ETLA', 'NEJAPA DE MADERO', 'IXPANTEPEC NIEVES', 'SANTIAGO NILTEPEC', 'OAXACA DE JU[AÁ]REZ', 'OCOTL[AÁ]N DE MORELOS', 'LA PE', 'PINOTEPA DE DON LUIS', 'PLUMA HIDALGO', 'SAN JOS[EÉ] DEL PROGRESO', 'PUTLA VILLA DE GUERRERO', 'SANTA CATARINA QUIOQUITANI', 'REFORMA DE PINEDA', 'LA REFORMA', 'REYES ETLA', 'ROJAS DE CUAUHT[EÉ]MOC', 'SALINA CRUZ', 'SAN AGUST[IÍ]N AMATENGO', 'SAN AGUST[IÍ]N ATENANGO', 'SAN AGUST[IÍ]N CHAYUCO', 'SAN AGUST[IÍ]N DE LAS JUNTAS', 'SAN AGUST[IÍ]N ETLA', 'SAN AGUST[IÍ]N LOXICHA', 'SAN AGUST[IÍ]N TLACOTEPEC', 'SAN AGUST[IÍ]N YATARENI', 'SAN ANDR[EÉ]S CABECERA NUEVA', 'SAN ANDR[EÉ]S DINICUITI', 'SAN ANDR[EÉ]S HUAXPALTEPEC', 'SAN ANDR[EÉ]S HUAY[AÁ]PAM', 'SAN ANDR[EÉ]S IXTLAHUACA', 'SAN ANDR[EÉ]S LAGUNAS', 'SAN ANDR[EÉ]S NUXIÑO', 'SAN ANDR[EÉ]S PAXTL[AÁ]N', 'SAN ANDR[EÉ]S SINAXTLA', 'SAN ANDR[EÉ]S SOLAGA', 'SAN ANDR[EÉ]S TEOTIL[AÁ]LPAM', 'SAN ANDR[EÉ]S TEPETLAPA', 'SAN ANDR[EÉ]S YA[AÁ]', 'SAN ANDR[EÉ]S ZABACHE', 'SAN ANDR[EÉ]S ZAUTLA', 'SAN ANTONINO CASTILLO VELASCO', 'SAN ANTONINO EL ALTO', 'SAN ANTONINO MONTE VERDE', 'SAN ANTONIO ACUTLA', 'SAN ANTONIO DE LA CAL', 'SAN ANTONIO HUITEPEC', 'SAN ANTONIO NANAHUAT[IÍ]PAM', 'SAN ANTONIO SINICAHUA', 'SAN ANTONIO TEPETLAPA', 'SAN BALTAZAR CHICHIC[AÁ]PAM', 'SAN BALTAZAR LOXICHA', 'SAN BALTAZAR YATZACHI EL BAJO', 'SAN BARTOLO COYOTEPEC', 'SAN BARTOLOM[EÉ] AYAUTLA', 'SAN BARTOLOM[EÉ] LOXICHA', 'SAN BARTOLOM[EÉ] QUIALANA', 'SAN BARTOLOM[EÉ] YUCUAÑE', 'SAN BARTOLOM[EÉ] ZOOGOCHO', 'SAN BARTOLO SOYALTEPEC', 'SAN BARTOLO YAUTEPEC', 'SAN BERNARDO MIXTEPEC', 'SAN BLAS ATEMPA', 'SAN CARLOS YAUTEPEC', 'SAN CRIST[OÓ]BAL AMATL[AÁ]N', 'SAN CRIST[OÓ]BAL AMOLTEPEC', 'SAN CRIST[OÓ]BAL LACHIRIOAG', 'SAN CRIST[OÓ]BAL SUCHIXTLAHUACA', 'SAN DIONISIO DEL MAR', 'SAN DIONISIO OCOTEPEC', 'SAN DIONISIO OCOTL[AÁ]N', 'SAN ESTEBAN ATATLAHUCA', 'SAN FELIPE JALAPA DE D[IÍ]AZ', 'SAN FELIPE TEJAL[AÁ]PAM', 'SAN FELIPE USILA', 'SAN FRANCISCO CAHUACU[AÁ]', 'SAN FRANCISCO CAJONOS', 'SAN FRANCISCO CHAPULAPA', 'SAN FRANCISCO CHIND[UÚ]A', 'SAN FRANCISCO DEL MAR', 'SAN FRANCISCO HUEHUETL[AÁ]N', 'SAN FRANCISCO IXHUAT[AÁ]N', 'SAN FRANCISCO JALTEPETONGO', 'SAN FRANCISCO LACHIGOL[OÓ]', 'SAN FRANCISCO LOGUECHE', 'SAN FRANCISCO NUXAÑO', 'SAN FRANCISCO OZOLOTEPEC', 'SAN FRANCISCO SOLA', 'SAN FRANCISCO TELIXTLAHUACA', 'SAN FRANCISCO TEOPAN', 'SAN FRANCISCO TLAPANCINGO', 'SAN GABRIEL MIXTEPEC', 'SAN ILDEFONSO AMATL[AÁ]N', 'SAN ILDEFONSO SOLA', 'SAN ILDEFONSO VILLA ALTA', 'SAN JACINTO AMILPAS', 'SAN JACINTO TLACOTEPEC', 'SAN JER[OÓ]NIMO COATL[AÁ]N', 'SAN JER[OÓ]NIMO SILACAYOAPILLA', 'SAN JER[OÓ]NIMO SOSOLA', 'SAN JER[OÓ]NIMO TAVICHE', 'SAN JER[OÓ]NIMO TEC[OÓ]ATL', 'SAN JORGE NUCHITA', 'SAN JOS[EÉ] AYUQUILA', 'SAN JOS[EÉ] CHILTEPEC', 'SAN JOS[EÉ] DEL PEÑASCO', 'SAN JOS[EÉ] ESTANCIA GRANDE', 'SAN JOS[EÉ] INDEPENDENCIA', 'SAN JOS[EÉ] LACHIGUIRI', 'SAN JOS[EÉ] TENANGO', 'SAN JUAN ACHIUTLA', 'SAN JUAN ATEPEC', '[AÁ]NIMAS TRUJANO', 'SAN JUAN BAUTISTA ATATLAHUCA', 'SAN JUAN BAUTISTA COIXTLAHUACA', 'SAN JUAN BAUTISTA CUICATL[AÁ]N', 'SAN JUAN BAUTISTA GUELACHE', 'SAN JUAN BAUTISTA JAYACATL[AÁ]N', 'SAN JUAN BAUTISTA LO DE SOTO', 'SAN JUAN BAUTISTA SUCHITEPEC', 'SAN JUAN BAUTISTA TLACOATZINTEPEC', 'SAN JUAN BAUTISTA TLACHICHILCO', 'SAN JUAN BAUTISTA TUXTEPEC', 'SAN JUAN CACAHUATEPEC', 'SAN JUAN CIENEGUILLA', 'SAN JUAN COATZ[OÓ]SPAM', 'SAN JUAN COLORADO', 'SAN JUAN COMALTEPEC', 'SAN JUAN COTZOC[OÓ]N', 'SAN JUAN CHICOMEZ[UÚ]CHIL', 'SAN JUAN CHILATECA', 'SAN JUAN DEL ESTADO', 'SAN JUAN DEL R[IÍ]O', 'SAN JUAN DIUXI', 'SAN JUAN EVANGELISTA ANALCO', 'SAN JUAN GUELAV[IÍ]A', 'SAN JUAN GUICHICOVI', 'SAN JUAN IHUALTEPEC', 'SAN JUAN JUQUILA MIXES', 'SAN JUAN JUQUILA VIJANOS', 'SAN JUAN LACHAO', 'SAN JUAN LACHIGALLA', 'SAN JUAN LAJARCIA', 'SAN JUAN LALANA', 'SAN JUAN DE LOS CU[EÉ]S', 'SAN JUAN MAZATL[AÁ]N', 'SAN JUAN MIXTEPEC', 'SAN JUAN MIXTEPEC.', 'SAN JUAN ÑUM[IÍ]', 'SAN JUAN OZOLOTEPEC', 'SAN JUAN PETLAPA', 'SAN JUAN QUIAHIJE', 'SAN JUAN QUIOTEPEC', 'SAN JUAN SAYULTEPEC', 'SAN JUAN TABA[AÁ]', 'SAN JUAN TAMAZOLA', 'SAN JUAN TEITA', 'SAN JUAN TEITIPAC', 'SAN JUAN TEPEUXILA', 'SAN JUAN TEPOSCOLULA', 'SAN JUAN YAE[EÉ]', 'SAN JUAN YATZONA', 'SAN JUAN YUCUITA', 'SAN LORENZO', 'SAN LORENZO ALBARRADAS', 'SAN LORENZO CACAOTEPEC', 'SAN LORENZO CUAUNECUILTITLA', 'SAN LORENZO TEXMEL[UÚ]CAN', 'SAN LORENZO VICTORIA', 'SAN LUCAS CAMOTL[AÁ]N', 'SAN LUCAS OJITL[AÁ]N', 'SAN LUCAS QUIAVIN[IÍ]', 'SAN LUCAS ZOQUI[AÁ]PAM', 'SAN LUIS AMATL[AÁ]N', 'SAN MARCIAL OZOLOTEPEC', 'SAN MARCOS ARTEAGA', 'SAN MART[IÍ]N DE LOS CANSECOS', 'SAN MART[IÍ]N HUAMEL[UÚ]LPAM', 'SAN MART[IÍ]N ITUNYOSO', 'SAN MART[IÍ]N LACHIL[AÁ]', 'SAN MART[IÍ]N PERAS', 'SAN MART[IÍ]N TILCAJETE', 'SAN MART[IÍ]N TOXPALAN', 'SAN MART[IÍ]N ZACATEPEC', 'SAN MATEO CAJONOS', 'CAPUL[AÁ]LPAM DE M[EÉ]NDEZ', 'SAN MATEO DEL MAR', 'SAN MATEO YOLOXOCHITL[AÁ]N', 'SAN MATEO ETLATONGO', 'SAN MATEO NEJ[AÁ]PAM', 'SAN MATEO PEÑASCO', 'SAN MATEO PIÑAS', 'SAN MATEO R[IÍ]O HONDO', 'SAN MATEO SINDIHUI', 'SAN MATEO TLAPILTEPEC', 'SAN MELCHOR BETAZA', 'SAN MIGUEL ACHIUTLA', 'SAN MIGUEL AHUEHUETITL[AÁ]N', 'SAN MIGUEL ALO[AÁ]PAM', 'SAN MIGUEL AMATITL[AÁ]N', 'SAN MIGUEL AMATL[AÁ]N', 'SAN MIGUEL COATL[AÁ]N', 'SAN MIGUEL CHICAHUA', 'SAN MIGUEL CHIMALAPA', 'SAN MIGUEL DEL PUERTO', 'SAN MIGUEL DEL R[IÍ]O', 'SAN MIGUEL EJUTLA', 'SAN MIGUEL EL GRANDE', 'SAN MIGUEL HUAUTLA', 'SAN MIGUEL MIXTEPEC', 'SAN MIGUEL PANIXTLAHUACA', 'SAN MIGUEL PERAS', 'SAN MIGUEL PIEDRAS', 'SAN MIGUEL QUETZALTEPEC', 'SAN MIGUEL SANTA FLOR', 'VILLA SOLA DE VEGA', 'SAN MIGUEL SOYALTEPEC', 'SAN MIGUEL SUCHIXTEPEC', 'VILLA TALEA DE CASTRO', 'SAN MIGUEL TECOMATL[AÁ]N', 'SAN MIGUEL TENANGO', 'SAN MIGUEL TEQUIXTEPEC', 'SAN MIGUEL TILQUI[AÁ]PAM', 'SAN MIGUEL TLACAMAMA', 'SAN MIGUEL TLACOTEPEC', 'SAN MIGUEL TULANCINGO', 'SAN MIGUEL YOTAO', 'SAN NICOL[AÁ]S', 'SAN NICOL[AÁ]S HIDALGO', 'SAN PABLO COATL[AÁ]N', 'SAN PABLO CUATRO VENADOS', 'SAN PABLO ETLA', 'SAN PABLO HUITZO', 'SAN PABLO HUIXTEPEC', 'SAN PABLO MACUILTIANGUIS', 'SAN PABLO TIJALTEPEC', 'SAN PABLO VILLA DE MITLA', 'SAN PABLO YAGANIZA', 'SAN PEDRO AMUZGOS', 'SAN PEDRO AP[OÓ]STOL', 'SAN PEDRO ATOYAC', 'SAN PEDRO CAJONOS', 'SAN PEDRO COXCALTEPEC C[AÁ]NTAROS', 'SAN PEDRO COMITANCILLO', 'SAN PEDRO EL ALTO', 'SAN PEDRO HUAMELULA', 'SAN PEDRO HUILOTEPEC', 'SAN PEDRO IXCATL[AÁ]N', 'SAN PEDRO IXTLAHUACA', 'SAN PEDRO JALTEPETONGO', 'SAN PEDRO JICAY[AÁ]N', 'SAN PEDRO JOCOTIPAC', 'SAN PEDRO JUCHATENGO', 'SAN PEDRO M[AÁ]RTIR', 'SAN PEDRO M[AÁ]RTIR QUIECHAPA', 'SAN PEDRO M[AÁ]RTIR YUCUXACO', 'SAN PEDRO MIXTEPEC', 'SAN PEDRO MOLINOS', 'SAN PEDRO NOPALA', 'SAN PEDRO OCOPETATILLO', 'SAN PEDRO OCOTEPEC', 'SAN PEDRO POCHUTLA', 'SAN PEDRO QUIATONI', 'SAN PEDRO SOCHI[AÁ]PAM', 'SAN PEDRO TAPANATEPEC', 'SAN PEDRO TAVICHE', 'SAN PEDRO TEOZACOALCO', 'SAN PEDRO TEUTILA', 'SAN PEDRO TIDA[AÁ]', 'SAN PEDRO TOPILTEPEC', 'SAN PEDRO TOTOL[AÁ]PAM', 'VILLA DE TUTUTEPEC', 'SAN PEDRO YANERI', 'SAN PEDRO Y[OÓ]LOX', 'SAN PEDRO Y SAN PABLO AYUTLA', 'VILLA DE ETLA', 'SAN PEDRO Y SAN PABLO TEPOSCOLULA', 'SAN PEDRO Y SAN PABLO TEQUIXTEPEC', 'SAN PEDRO YUCUNAMA', 'SAN RAYMUNDO JALPAN', 'SAN SEBASTI[AÁ]N ABASOLO', 'SAN SEBASTI[AÁ]N COATL[AÁ]N', 'SAN SEBASTI[AÁ]N IXCAPA', 'SAN SEBASTI[AÁ]N NICANANDUTA', 'SAN SEBASTI[AÁ]N R[IÍ]O HONDO', 'SAN SEBASTI[AÁ]N TECOMAXTLAHUACA', 'SAN SEBASTI[AÁ]N TEITIPAC', 'SAN SEBASTI[AÁ]N TUTLA', 'SAN SIM[OÓ]N ALMOLONGAS', 'SAN SIM[OÓ]N ZAHUATL[AÁ]N', 'SANTA ANA', 'SANTA ANA ATEIXTLAHUACA', 'SANTA ANA CUAUHT[EÉ]MOC', 'SANTA ANA DEL VALLE', 'SANTA ANA TAVELA', 'SANTA ANA TLAPACOYAN', 'SANTA ANA YARENI', 'SANTA ANA ZEGACHE', 'SANTA CATALINA QUIER[IÍ]', 'SANTA CATARINA CUIXTLA', 'SANTA CATARINA IXTEPEJI', 'SANTA CATARINA JUQUILA', 'SANTA CATARINA LACHATAO', 'SANTA CATARINA LOXICHA', 'SANTA CATARINA MECHOAC[AÁ]N', 'SANTA CATARINA MINAS', 'SANTA CATARINA QUIAN[EÉ]', 'SANTA CATARINA TAYATA', 'SANTA CATARINA TICU[AÁ]', 'SANTA CATARINA YOSONOT[UÚ]', 'SANTA CATARINA ZAPOQUILA', 'SANTA CRUZ ACATEPEC', 'SANTA CRUZ AMILPAS', 'SANTA CRUZ DE BRAVO', 'SANTA CRUZ ITUNDUJIA', 'SANTA CRUZ MIXTEPEC', 'SANTA CRUZ NUNDACO', 'SANTA CRUZ PAPALUTLA', 'SANTA CRUZ TACACHE DE MINA', 'SANTA CRUZ TACAHUA', 'SANTA CRUZ TAYATA', 'SANTA CRUZ XITLA', 'SANTA CRUZ XOXOCOTL[AÁ]N', 'SANTA CRUZ ZENZONTEPEC', 'SANTA GERTRUDIS', 'SANTA IN[EÉ]S DEL MONTE', 'SANTA IN[EÉ]S YATZECHE', 'SANTA LUC[IÍ]A DEL CAMINO', 'SANTA LUC[IÍ]A MIAHUATL[AÁ]N', 'SANTA LUC[IÍ]A MONTEVERDE', 'SANTA LUC[IÍ]A OCOTL[AÁ]N', 'SANTA MAR[IÍ]A ALOTEPEC', 'SANTA MAR[IÍ]A APAZCO', 'SANTA MAR[IÍ]A LA ASUNCI[OÓ]N', 'HEROICA CIUDAD DE TLAXIACO', 'AYOQUEZCO DE ALDAMA',
                               'SANTA MAR[IÍ]A ATZOMPA', 'SANTA MAR[IÍ]A CAMOTL[AÁ]N', 'SANTA MAR[IÍ]A COLOTEPEC', 'SANTA MAR[IÍ]A CORTIJO', 'SANTA MAR[IÍ]A COYOTEPEC', 'SANTA MAR[IÍ]A CHACHO[AÁ]PAM', 'VILLA DE CHILAPA DE D[IÍ]AZ', 'SANTA MAR[IÍ]A CHILCHOTLA', 'SANTA MAR[IÍ]A CHIMALAPA', 'SANTA MAR[IÍ]A DEL ROSARIO', 'SANTA MAR[IÍ]A DEL TULE', 'SANTA MAR[IÍ]A ECATEPEC', 'SANTA MAR[IÍ]A GUELAC[EÉ]', 'SANTA MAR[IÍ]A GUIENAGATI', 'SANTA MAR[IÍ]A HUATULCO', 'SANTA MAR[IÍ]A HUAZOLOTITL[AÁ]N', 'SANTA MAR[IÍ]A IPALAPA', 'SANTA MAR[IÍ]A IXCATL[AÁ]N', 'SANTA MAR[IÍ]A JACATEPEC', 'SANTA MAR[IÍ]A JALAPA DEL MARQU[EÉ]S', 'SANTA MAR[IÍ]A JALTIANGUIS', 'SANTA MAR[IÍ]A LACHIX[IÍ]O', 'SANTA MAR[IÍ]A MIXTEQUILLA', 'SANTA MAR[IÍ]A NATIVITAS', 'SANTA MAR[IÍ]A NDUAYACO', 'SANTA MAR[IÍ]A OZOLOTEPEC', 'SANTA MAR[IÍ]A P[AÁ]PALO', 'SANTA MAR[IÍ]A PEÑOLES', 'SANTA MAR[IÍ]A PETAPA', 'SANTA MAR[IÍ]A QUIEGOLANI', 'SANTA MAR[IÍ]A SOLA', 'SANTA MAR[IÍ]A TATALTEPEC', 'SANTA MAR[IÍ]A TECOMAVACA', 'SANTA MAR[IÍ]A TEMAXCALAPA', 'SANTA MAR[IÍ]A TEMAXCALTEPEC', 'SANTA MAR[IÍ]A TEOPOXCO', 'SANTA MAR[IÍ]A TEPANTLALI', 'SANTA MAR[IÍ]A TEXCATITL[AÁ]N', 'SANTA MAR[IÍ]A TLAHUITOLTEPEC', 'SANTA MAR[IÍ]A TLALIXTAC', 'SANTA MAR[IÍ]A TONAMECA', 'SANTA MAR[IÍ]A TOTOLAPILLA', 'SANTA MAR[IÍ]A XADANI', 'SANTA MAR[IÍ]A YALINA', 'SANTA MAR[IÍ]A YAVES[IÍ]A', 'SANTA MAR[IÍ]A YOLOTEPEC', 'SANTA MAR[IÍ]A YOSOY[UÚ]A', 'SANTA MAR[IÍ]A YUCUHITI', 'SANTA MAR[IÍ]A ZACATEPEC', 'SANTA MAR[IÍ]A ZANIZA', 'SANTA MAR[IÍ]A ZOQUITL[AÁ]N', 'SANTIAGO AMOLTEPEC', 'SANTIAGO APOALA', 'SANTIAGO AP[OÓ]STOL', 'SANTIAGO ASTATA', 'SANTIAGO ATITL[AÁ]N', 'SANTIAGO AYUQUILILLA', 'SANTIAGO CACALOXTEPEC', 'SANTIAGO CAMOTL[AÁ]N', 'SANTIAGO COMALTEPEC', 'VILLA DE SANTIAGO CHAZUMBA', 'SANTIAGO CHO[AÁ]PAM', 'SANTIAGO DEL R[IÍ]O', 'SANTIAGO HUAJOLOTITL[AÁ]N', 'SANTIAGO HUAUCLILLA', 'SANTIAGO IHUITL[AÁ]N PLUMAS', 'SANTIAGO IXCUINTEPEC', 'SANTIAGO IXTAYUTLA', 'SANTIAGO JAMILTEPEC', 'SANTIAGO JOCOTEPEC', 'SANTIAGO JUXTLAHUACA', 'SANTIAGO LACHIGUIRI', 'SANTIAGO LALOPA', 'SANTIAGO LAOLLAGA', 'SANTIAGO LAXOPA', 'SANTIAGO LLANO GRANDE', 'SANTIAGO MATATL[AÁ]N', 'SANTIAGO MILTEPEC', 'SANTIAGO MINAS', 'SANTIAGO NACALTEPEC', 'SANTIAGO NEJAPILLA', 'SANTIAGO NUNDICHE', 'SANTIAGO NUYO[OÓ]', 'SANTIAGO PINOTEPA NACIONAL', 'SANTIAGO SUCHILQUITONGO', 'SANTIAGO TAMAZOLA', 'SANTIAGO TAPEXTLA', 'VILLA TEJ[UÚ]PAM DE LA UNI[OÓ]N', 'SANTIAGO TENANGO', 'SANTIAGO TEPETLAPA', 'SANTIAGO TETEPEC', 'SANTIAGO TEXCALCINGO', 'SANTIAGO TEXTITL[AÁ]N', 'SANTIAGO TILANTONGO', 'SANTIAGO TILLO', 'SANTIAGO TLAZOYALTEPEC', 'SANTIAGO XANICA', 'SANTIAGO XIACU[IÍ]', 'SANTIAGO YAITEPEC', 'SANTIAGO YAVEO', 'SANTIAGO YOLOM[EÉ]CATL', 'SANTIAGO YOSOND[UÚ]A', 'SANTIAGO YUCUYACHI', 'SANTIAGO ZACATEPEC', 'SANTIAGO ZOOCHILA', 'NUEVO ZOQUI[AÁ]PAM', 'SANTO DOMINGO INGENIO', 'SANTO DOMINGO ALBARRADAS', 'SANTO DOMINGO ARMENTA', 'SANTO DOMINGO CHIHUIT[AÁ]N', 'SANTO DOMINGO DE MORELOS', 'SANTO DOMINGO IXCATL[AÁ]N', 'SANTO DOMINGO NUXA[AÁ]', 'SANTO DOMINGO OZOLOTEPEC', 'SANTO DOMINGO PETAPA', 'SANTO DOMINGO ROAYAGA', 'SANTO DOMINGO TEHUANTEPEC', 'SANTO DOMINGO TEOJOMULCO', 'SANTO DOMINGO TEPUXTEPEC', 'SANTO DOMINGO TLATAY[AÁ]PAM', 'SANTO DOMINGO TOMALTEPEC', 'SANTO DOMINGO TONAL[AÁ]', 'SANTO DOMINGO TONALTEPEC', 'SANTO DOMINGO XAGAC[IÍ]A', 'SANTO DOMINGO YANHUITL[AÁ]N', 'SANTO DOMINGO YODOHINO', 'SANTO DOMINGO ZANATEPEC', 'SANTOS REYES NOPALA', 'SANTOS REYES P[AÁ]PALO', 'SANTOS REYES TEPEJILLO', 'SANTOS REYES YUCUN[AÁ]', 'SANTO TOM[AÁ]S JALIEZA', 'SANTO TOM[AÁ]S MAZALTEPEC', 'SANTO TOM[AÁ]S OCOTEPEC', 'SANTO TOM[AÁ]S TAMAZULAPAN', 'SAN VICENTE COATL[AÁ]N', 'SAN VICENTE LACHIX[IÍ]O', 'SAN VICENTE NUÑ[UÚ]', 'SILACAYO[AÁ]PAM', 'SITIO DE XITLAPEHUA', 'SOLEDAD ETLA', 'VILLA DE TAMAZUL[AÁ]PAM DEL PROGRESO', 'TANETZE DE ZARAGOZA', 'TANICHE', 'TATALTEPEC DE VALD[EÉ]S', 'TEOCOCUILCO DE MARCOS P[EÉ]REZ', 'TEOTITL[AÁ]N DE FLORES MAG[OÓ]N', 'TEOTITL[AÁ]N DEL VALLE', 'TEOTONGO', 'TEPELMEME VILLA DE MORELOS', 'HEROICA VILLA TEZOATL[AÁ]N DE SEGURA Y LUNA', 'SAN JER[OÓ]NIMO TLACOCHAHUAYA', 'TLACOLULA DE MATAMOROS', 'TLACOTEPEC PLUMAS', 'TLALIXTAC DE CABRERA', 'TOTONTEPEC VILLA DE MORELOS', 'TRINIDAD ZAACHILA', 'LA TRINIDAD VISTA HERMOSA', 'UNI[OÓ]N HIDALGO', 'VALERIO TRUJANO', 'SAN JUAN BAUTISTA VALLE NACIONAL', 'VILLA D[IÍ]AZ ORDAZ', 'YAXE', 'MAGDALENA YODOCONO DE PORFIRIO D[IÍ]AZ', 'YOGANA', 'YUTANDUCHI DE GUERRERO', 'VILLA DE ZAACHILA', 'SAN MATEO YUCUTINDOO', 'ZAPOTITL[AÁ]N LAGUNAS', 'ZAPOTITL[AÁ]N PALMAS', 'SANTA IN[EÉ]S DE ZARAGOZA', 'ZIMATL[AÁ]N DE [AÁ]LVAREZ' ]       
            patrones_ciudades = {'ABEJONES': 'ABEJONES', 'ACATLAÁN DE PEÉREZ FIGUEROA': 'ACATLÁN DE PÉREZ FIGUEROA', 'ASUNCIOÓN CACALOTEPEC': 'ASUNCIÓN CACALOTEPEC', 'ASUNCIOÓN CUYOTEPEJI': 'ASUNCIÓN CUYOTEPEJI', 'ASUNCIOÓN IXTALTEPEC': 'ASUNCIÓN IXTALTEPEC', 'ASUNCIOÓN NOCHIXTLAÁN': 'ASUNCIÓN NOCHIXTLÁN', 'ASUNCIOÓN OCOTLAÁN': 'ASUNCIÓN OCOTLÁN', 'ASUNCIOÓN TLACOLULITA': 'ASUNCIÓN TLACOLULITA', 'AYOTZINTEPEC': 'AYOTZINTEPEC', 'EL BARRIO DE LA SOLEDAD': 'EL BARRIO DE LA SOLEDAD', 'CALIHUALAÁ': 'CALIHUALÁ', 'CANDELARIA LOXICHA': 'CANDELARIA LOXICHA', 'CIEÉNEGA DE ZIMATLAÁN': 'CIÉNEGA DE ZIMATLÁN', 'CIUDAD IXTEPEC': 'CIUDAD IXTEPEC', 'COATECAS ALTAS': 'COATECAS ALTAS', 'COICOYAÁN DE LAS FLORES': 'COICOYÁN DE LAS FLORES', 'LA COMPAÑIÍA': 'LA COMPAÑÍA', 'CONCEPCIOÓN BUENAVISTA': 'CONCEPCIÓN BUENAVISTA', 'CONCEPCIOÓN PAÁPALO': 'CONCEPCIÓN PÁPALO', 'CONSTANCIA DEL ROSARIO': 'CONSTANCIA DEL ROSARIO', 'COSOLAPA': 'COSOLAPA', 'COSOLTEPEC': 'COSOLTEPEC', 'CUILAÁPAM DE GUERRERO': 'CUILÁPAM DE GUERRERO', 'CUYAMECALCO VILLA DE ZARAGOZA': 'CUYAMECALCO VILLA DE ZARAGOZA', 'CHAHUITES': 'CHAHUITES', 'CHALCATONGO DE HIDALGO': 'CHALCATONGO DE HIDALGO', 'CHIQUIHUITLAÁN DE BENITO JUAÁREZ': 'CHIQUIHUITLÁN DE BENITO JUÁREZ', 'HEROICA CIUDAD DE EJUTLA DE CRESPO': 'HEROICA CIUDAD DE EJUTLA DE CRESPO', 'ELOXOCHITLAÁN DE FLORES MAGOÓN': 'ELOXOCHITLÁN DE FLORES MAGÓN', 'EL ESPINAL': 'EL ESPINAL', 'TAMAZULAÁPAM DEL ESPIÍRITU SANTO': 'TAMAZULÁPAM DEL ESPÍRITU SANTO', 'FRESNILLO DE TRUJANO': 'FRESNILLO DE TRUJANO', 'GUADALUPE ETLA': 'GUADALUPE ETLA', 'GUADALUPE DE RAMIÍREZ': 'GUADALUPE DE RAMÍREZ', 'GUELATAO DE JUAÁREZ': 'GUELATAO DE JUÁREZ', 'GUEVEA DE HUMBOLDT': 'GUEVEA DE HUMBOLDT', 'MESONES HIDALGO': 'MESONES HIDALGO', 'VILLA HIDALGO': 'VILLA HIDALGO', 'HEROICA CIUDAD DE HUAJUAPAN DE LEOÓN': 'HEROICA CIUDAD DE HUAJUAPAN DE LEÓN', 'HUAUTEPEC': 'HUAUTEPEC', 'HUAUTLA DE JIMEÉNEZ': 'HUAUTLA DE JIMÉNEZ', 'IXTLAÁN DE JUAÁREZ': 'IXTLÁN DE JUÁREZ', 'JUCHITAÁN DE ZARAGOZA': 'JUCHITÁN DE ZARAGOZA', 'LOMA BONITA': 'LOMA BONITA', 'MAGDALENA APASCO': 'MAGDALENA APASCO', 'MAGDALENA JALTEPEC': 'MAGDALENA JALTEPEC', 'SANTA MAGDALENA JICOTLAÁN': 'SANTA MAGDALENA JICOTLÁN', 'MAGDALENA MIXTEPEC': 'MAGDALENA MIXTEPEC', 'MAGDALENA OCOTLAÁN': 'MAGDALENA OCOTLÁN', 'MAGDALENA PEÑASCO': 'MAGDALENA PEÑASCO', 'MAGDALENA TEITIPAC': 'MAGDALENA TEITIPAC', 'MAGDALENA TEQUISISTLAÁN': 'MAGDALENA TEQUISISTLÁN', 'MAGDALENA TLACOTEPEC': 'MAGDALENA TLACOTEPEC', 'MAGDALENA ZAHUATLAÁN': 'MAGDALENA ZAHUATLÁN', 'MARISCALA DE JUAÁREZ': 'MARISCALA DE JUÁREZ', 'MAÁRTIRES DE TACUBAYA': 'MÁRTIRES DE TACUBAYA', 'MATIÍAS ROMERO AVENDAÑO': 'MATÍAS ROMERO AVENDAÑO', 'MAZATLAÁN VILLA DE FLORES': 'MAZATLÁN VILLA DE FLORES', 'MIAHUATLAÁN DE PORFIRIO DIÍAZ': 'MIAHUATLÁN DE PORFIRIO DÍAZ', 'MIXISTLAÁN DE LA REFORMA': 'MIXISTLÁN DE LA REFORMA', 'MONJAS': 'MONJAS', 'NATIVIDAD': 'NATIVIDAD', 'NAZARENO ETLA': 'NAZARENO ETLA', 'NEJAPA DE MADERO': 'NEJAPA DE MADERO', 'IXPANTEPEC NIEVES': 'IXPANTEPEC NIEVES', 'SANTIAGO NILTEPEC': 'SANTIAGO NILTEPEC', 'OAXACA DE JUAÁREZ': 'OAXACA DE JUÁREZ', 'OCOTLAÁN DE MORELOS': 'OCOTLÁN DE MORELOS', 'LA PE': 'LA PE', 'PINOTEPA DE DON LUIS': 'PINOTEPA DE DON LUIS', 'PLUMA HIDALGO': 'PLUMA HIDALGO', 'SAN JOSEÉ DEL PROGRESO': 'SAN JOSÉ DEL PROGRESO', 'PUTLA VILLA DE GUERRERO': 'PUTLA VILLA DE GUERRERO', 'SANTA CATARINA QUIOQUITANI': 'SANTA CATARINA QUIOQUITANI', 'REFORMA DE PINEDA': 'REFORMA DE PINEDA', 'LA REFORMA': 'LA REFORMA', 'REYES ETLA': 'REYES ETLA', 'ROJAS DE CUAUHTEÉMOC': 'ROJAS DE CUAUHTÉMOC', 'SALINA CRUZ': 'SALINA CRUZ', 'SAN AGUSTIÍN AMATENGO': 'SAN AGUSTÍN AMATENGO', 'SAN AGUSTIÍN ATENANGO': 'SAN AGUSTÍN ATENANGO', 'SAN AGUSTIÍN CHAYUCO': 'SAN AGUSTÍN CHAYUCO', 'SAN AGUSTIÍN DE LAS JUNTAS': 'SAN AGUSTÍN DE LAS JUNTAS', 'SAN AGUSTIÍN ETLA': 'SAN AGUSTÍN ETLA', 'SAN AGUSTIÍN LOXICHA': 'SAN AGUSTÍN LOXICHA', 'SAN AGUSTIÍN TLACOTEPEC': 'SAN AGUSTÍN TLACOTEPEC', 'SAN AGUSTIÍN YATARENI': 'SAN AGUSTÍN YATARENI', 'SAN ANDREÉS CABECERA NUEVA': 'SAN ANDRÉS CABECERA NUEVA', 'SAN ANDREÉS DINICUITI': 'SAN ANDRÉS DINICUITI', 'SAN ANDREÉS HUAXPALTEPEC': 'SAN ANDRÉS HUAXPALTEPEC', 'SAN ANDREÉS HUAYAÁPAM': 'SAN ANDRÉS HUAYÁPAM', 'SAN ANDREÉS IXTLAHUACA': 'SAN ANDRÉS IXTLAHUACA', 'SAN ANDREÉS LAGUNAS': 'SAN ANDRÉS LAGUNAS', 'SAN ANDREÉS NUXIÑO': 'SAN ANDRÉS NUXIÑO', 'SAN ANDREÉS PAXTLAÁN': 'SAN ANDRÉS PAXTLÁN', 'SAN ANDREÉS SINAXTLA': 'SAN ANDRÉS SINAXTLA', 'SAN ANDREÉS SOLAGA': 'SAN ANDRÉS SOLAGA', 'SAN ANDREÉS TEOTILAÁLPAM': 'SAN ANDRÉS TEOTILÁLPAM', 'SAN ANDREÉS TEPETLAPA': 'SAN ANDRÉS TEPETLAPA', 'SAN ANDREÉS YAAÁ': 'SAN ANDRÉS YAÁ', 'SAN ANDREÉS ZABACHE': 'SAN ANDRÉS ZABACHE', 'SAN ANDREÉS ZAUTLA': 'SAN ANDRÉS ZAUTLA', 'SAN ANTONINO CASTILLO VELASCO': 'SAN ANTONINO CASTILLO VELASCO', 'SAN ANTONINO EL ALTO': 'SAN ANTONINO EL ALTO', 'SAN ANTONINO MONTE VERDE': 'SAN ANTONINO MONTE VERDE', 'SAN ANTONIO ACUTLA': 'SAN ANTONIO ACUTLA', 'SAN ANTONIO DE LA CAL': 'SAN ANTONIO DE LA CAL', 'SAN ANTONIO HUITEPEC': 'SAN ANTONIO HUITEPEC', 'SAN ANTONIO NANAHUATIÍPAM': 'SAN ANTONIO NANAHUATÍPAM', 'SAN ANTONIO SINICAHUA': 'SAN ANTONIO SINICAHUA', 'SAN ANTONIO TEPETLAPA': 'SAN ANTONIO TEPETLAPA', 'SAN BALTAZAR CHICHICAÁPAM': 'SAN BALTAZAR CHICHICÁPAM', 'SAN BALTAZAR LOXICHA': 'SAN BALTAZAR LOXICHA', 'SAN BALTAZAR YATZACHI EL BAJO': 'SAN BALTAZAR YATZACHI EL BAJO', 'SAN BARTOLO COYOTEPEC': 'SAN BARTOLO COYOTEPEC', 'SAN BARTOLOMEÉ AYAUTLA': 'SAN BARTOLOMÉ AYAUTLA', 'SAN BARTOLOMEÉ LOXICHA': 'SAN BARTOLOMÉ LOXICHA', 'SAN BARTOLOMEÉ QUIALANA': 'SAN BARTOLOMÉ QUIALANA', 'SAN BARTOLOMEÉ YUCUAÑE': 'SAN BARTOLOMÉ YUCUAÑE', 'SAN BARTOLOMEÉ ZOOGOCHO': 'SAN BARTOLOMÉ ZOOGOCHO', 'SAN BARTOLO SOYALTEPEC': 'SAN BARTOLO SOYALTEPEC', 'SAN BARTOLO YAUTEPEC': 'SAN BARTOLO YAUTEPEC', 'SAN BERNARDO MIXTEPEC': 'SAN BERNARDO MIXTEPEC', 'SAN BLAS ATEMPA': 'SAN BLAS ATEMPA', 'SAN CARLOS YAUTEPEC': 'SAN CARLOS YAUTEPEC', 'SAN CRISTOÓBAL AMATLAÁN': 'SAN CRISTÓBAL AMATLÁN', 'SAN CRISTOÓBAL AMOLTEPEC': 'SAN CRISTÓBAL AMOLTEPEC', 'SAN CRISTOÓBAL LACHIRIOAG': 'SAN CRISTÓBAL LACHIRIOAG', 'SAN CRISTOÓBAL SUCHIXTLAHUACA': 'SAN CRISTÓBAL SUCHIXTLAHUACA', 'SAN DIONISIO DEL MAR': 'SAN DIONISIO DEL MAR', 'SAN DIONISIO OCOTEPEC': 'SAN DIONISIO OCOTEPEC', 'SAN DIONISIO OCOTLAÁN': 'SAN DIONISIO OCOTLÁN', 'SAN ESTEBAN ATATLAHUCA': 'SAN ESTEBAN ATATLAHUCA', 'SAN FELIPE JALAPA DE DIÍAZ': 'SAN FELIPE JALAPA DE DÍAZ', 'SAN FELIPE TEJALAÁPAM': 'SAN FELIPE TEJALÁPAM', 'SAN FELIPE USILA': 'SAN FELIPE USILA', 'SAN FRANCISCO CAHUACUAÁ': 'SAN FRANCISCO CAHUACUÁ', 'SAN FRANCISCO CAJONOS': 'SAN FRANCISCO CAJONOS', 'SAN FRANCISCO CHAPULAPA': 'SAN FRANCISCO CHAPULAPA', 'SAN FRANCISCO CHINDUÚA': 'SAN FRANCISCO CHINDÚA', 'SAN FRANCISCO DEL MAR': 'SAN FRANCISCO DEL MAR', 'SAN FRANCISCO HUEHUETLAÁN': 'SAN FRANCISCO HUEHUETLÁN', 'SAN FRANCISCO IXHUATAÁN': 'SAN FRANCISCO IXHUATÁN', 'SAN FRANCISCO JALTEPETONGO': 'SAN FRANCISCO JALTEPETONGO', 'SAN FRANCISCO LACHIGOLOÓ': 'SAN FRANCISCO LACHIGOLÓ', 'SAN FRANCISCO LOGUECHE': 'SAN FRANCISCO LOGUECHE', 'SAN FRANCISCO NUXAÑO': 'SAN FRANCISCO NUXAÑO', 'SAN FRANCISCO OZOLOTEPEC': 'SAN FRANCISCO OZOLOTEPEC', 'SAN FRANCISCO SOLA': 'SAN FRANCISCO SOLA', 'SAN FRANCISCO TELIXTLAHUACA': 'SAN FRANCISCO TELIXTLAHUACA', 'SAN FRANCISCO TEOPAN': 'SAN FRANCISCO TEOPAN', 'SAN FRANCISCO TLAPANCINGO': 'SAN FRANCISCO TLAPANCINGO', 'SAN GABRIEL MIXTEPEC': 'SAN GABRIEL MIXTEPEC', 'SAN ILDEFONSO AMATLAÁN': 'SAN ILDEFONSO AMATLÁN', 'SAN ILDEFONSO SOLA': 'SAN ILDEFONSO SOLA', 'SAN ILDEFONSO VILLA ALTA': 'SAN ILDEFONSO VILLA ALTA', 'SAN JACINTO AMILPAS': 'SAN JACINTO AMILPAS', 'SAN JACINTO TLACOTEPEC': 'SAN JACINTO TLACOTEPEC', 'SAN JEROÓNIMO COATLAÁN': 'SAN JERÓNIMO COATLÁN', 'SAN JEROÓNIMO SILACAYOAPILLA': 'SAN JERÓNIMO SILACAYOAPILLA', 'SAN JEROÓNIMO SOSOLA': 'SAN JERÓNIMO SOSOLA', 'SAN JEROÓNIMO TAVICHE': 'SAN JERÓNIMO TAVICHE', 'SAN JEROÓNIMO TECOÓATL': 'SAN JERÓNIMO TECÓATL', 'SAN JORGE NUCHITA': 'SAN JORGE NUCHITA', 'SAN JOSEÉ AYUQUILA': 'SAN JOSÉ AYUQUILA', 'SAN JOSEÉ CHILTEPEC': 'SAN JOSÉ CHILTEPEC', 'SAN JOSEÉ DEL PEÑASCO': 'SAN JOSÉ DEL PEÑASCO', 'SAN JOSEÉ ESTANCIA GRANDE': 'SAN JOSÉ ESTANCIA GRANDE', 'SAN JOSEÉ INDEPENDENCIA': 'SAN JOSÉ INDEPENDENCIA', 'SAN JOSEÉ LACHIGUIRI': 'SAN JOSÉ LACHIGUIRI', 'SAN JOSEÉ TENANGO': 'SAN JOSÉ TENANGO', 'SAN JUAN ACHIUTLA': 'SAN JUAN ACHIUTLA', 'SAN JUAN ATEPEC': 'SAN JUAN ATEPEC', 'AÁNIMAS TRUJANO': 'ÁNIMAS TRUJANO', 'SAN JUAN BAUTISTA ATATLAHUCA': 'SAN JUAN BAUTISTA ATATLAHUCA', 'SAN JUAN BAUTISTA COIXTLAHUACA': 'SAN JUAN BAUTISTA COIXTLAHUACA', 'SAN JUAN BAUTISTA CUICATLAÁN': 'SAN JUAN BAUTISTA CUICATLÁN', 'SAN JUAN BAUTISTA GUELACHE': 'SAN JUAN BAUTISTA GUELACHE', 'SAN JUAN BAUTISTA JAYACATLAÁN': 'SAN JUAN BAUTISTA JAYACATLÁN', 'SAN JUAN BAUTISTA LO DE SOTO': 'SAN JUAN BAUTISTA LO DE SOTO', 'SAN JUAN BAUTISTA SUCHITEPEC': 'SAN JUAN BAUTISTA SUCHITEPEC', 'SAN JUAN BAUTISTA TLACOATZINTEPEC': 'SAN JUAN BAUTISTA TLACOATZINTEPEC', 'SAN JUAN BAUTISTA TLACHICHILCO': 'SAN JUAN BAUTISTA TLACHICHILCO', 'SAN JUAN BAUTISTA TUXTEPEC': 'SAN JUAN BAUTISTA TUXTEPEC', 'SAN JUAN CACAHUATEPEC': 'SAN JUAN CACAHUATEPEC', 'SAN JUAN CIENEGUILLA': 'SAN JUAN CIENEGUILLA', 'SAN JUAN COATZOÓSPAM': 'SAN JUAN COATZÓSPAM', 'SAN JUAN COLORADO': 'SAN JUAN COLORADO', 'SAN JUAN COMALTEPEC': 'SAN JUAN COMALTEPEC', 'SAN JUAN COTZOCOÓN': 'SAN JUAN COTZOCÓN', 'SAN JUAN CHICOMEZUÚCHIL': 'SAN JUAN CHICOMEZÚCHIL', 'SAN JUAN CHILATECA': 'SAN JUAN CHILATECA', 'SAN JUAN DEL ESTADO': 'SAN JUAN DEL ESTADO', 'SAN JUAN DEL RIÍO': 'SAN JUAN DEL RÍO', 'SAN JUAN DIUXI': 'SAN JUAN DIUXI', 'SAN JUAN EVANGELISTA ANALCO': 'SAN JUAN EVANGELISTA ANALCO', 'SAN JUAN GUELAVIÍA': 'SAN JUAN GUELAVÍA', 'SAN JUAN GUICHICOVI': 'SAN JUAN GUICHICOVI', 'SAN JUAN IHUALTEPEC': 'SAN JUAN IHUALTEPEC', 'SAN JUAN JUQUILA MIXES': 'SAN JUAN JUQUILA MIXES', 'SAN JUAN JUQUILA VIJANOS': 'SAN JUAN JUQUILA VIJANOS', 'SAN JUAN LACHAO': 'SAN JUAN LACHAO', 'SAN JUAN LACHIGALLA': 'SAN JUAN LACHIGALLA', 'SAN JUAN LAJARCIA': 'SAN JUAN LAJARCIA', 'SAN JUAN LALANA': 'SAN JUAN LALANA', 'SAN JUAN DE LOS CUEÉS': 'SAN JUAN DE LOS CUÉS', 'SAN JUAN MAZATLAÁN': 'SAN JUAN MAZATLÁN',
                                 'SAN JUAN MIXTEPEC': 'SAN JUAN MIXTEPEC', 'SAN JUAN MIXTEPEC.': 'SAN JUAN MIXTEPEC.', 'SAN JUAN ÑUMIÍ': 'SAN JUAN ÑUMÍ', 'SAN JUAN OZOLOTEPEC': 'SAN JUAN OZOLOTEPEC', 'SAN JUAN PETLAPA': 'SAN JUAN PETLAPA', 'SAN JUAN QUIAHIJE': 'SAN JUAN QUIAHIJE', 'SAN JUAN QUIOTEPEC': 'SAN JUAN QUIOTEPEC', 'SAN JUAN SAYULTEPEC': 'SAN JUAN SAYULTEPEC', 'SAN JUAN TABAAÁ': 'SAN JUAN TABAÁ', 'SAN JUAN TAMAZOLA': 'SAN JUAN TAMAZOLA', 'SAN JUAN TEITA': 'SAN JUAN TEITA', 'SAN JUAN TEITIPAC': 'SAN JUAN TEITIPAC', 'SAN JUAN TEPEUXILA': 'SAN JUAN TEPEUXILA', 'SAN JUAN TEPOSCOLULA': 'SAN JUAN TEPOSCOLULA', 'SAN JUAN YAEEÉ': 'SAN JUAN YAEÉ', 'SAN JUAN YATZONA': 'SAN JUAN YATZONA', 'SAN JUAN YUCUITA': 'SAN JUAN YUCUITA', 'SAN LORENZO': 'SAN LORENZO', 'SAN LORENZO ALBARRADAS': 'SAN LORENZO ALBARRADAS', 'SAN LORENZO CACAOTEPEC': 'SAN LORENZO CACAOTEPEC', 'SAN LORENZO CUAUNECUILTITLA': 'SAN LORENZO CUAUNECUILTITLA', 'SAN LORENZO TEXMELUÚCAN': 'SAN LORENZO TEXMELÚCAN', 'SAN LORENZO VICTORIA': 'SAN LORENZO VICTORIA', 'SAN LUCAS CAMOTLAÁN': 'SAN LUCAS CAMOTLÁN', 'SAN LUCAS OJITLAÁN': 'SAN LUCAS OJITLÁN', 'SAN LUCAS QUIAVINIÍ': 'SAN LUCAS QUIAVINÍ', 'SAN LUCAS ZOQUIAÁPAM': 'SAN LUCAS ZOQUIÁPAM', 'SAN LUIS AMATLAÁN': 'SAN LUIS AMATLÁN', 'SAN MARCIAL OZOLOTEPEC': 'SAN MARCIAL OZOLOTEPEC', 'SAN MARCOS ARTEAGA': 'SAN MARCOS ARTEAGA', 'SAN MARTIÍN DE LOS CANSECOS': 'SAN MARTÍN DE LOS CANSECOS', 'SAN MARTIÍN HUAMELUÚLPAM': 'SAN MARTÍN HUAMELÚLPAM', 'SAN MARTIÍN ITUNYOSO': 'SAN MARTÍN ITUNYOSO', 'SAN MARTIÍN LACHILAÁ': 'SAN MARTÍN LACHILÁ', 'SAN MARTIÍN PERAS': 'SAN MARTÍN PERAS', 'SAN MARTIÍN TILCAJETE': 'SAN MARTÍN TILCAJETE', 'SAN MARTIÍN TOXPALAN': 'SAN MARTÍN TOXPALAN', 'SAN MARTIÍN ZACATEPEC': 'SAN MARTÍN ZACATEPEC', 'SAN MATEO CAJONOS': 'SAN MATEO CAJONOS', 'CAPULAÁLPAM DE MEÉNDEZ': 'CAPULÁLPAM DE MÉNDEZ', 'SAN MATEO DEL MAR': 'SAN MATEO DEL MAR', 'SAN MATEO YOLOXOCHITLAÁN': 'SAN MATEO YOLOXOCHITLÁN', 'SAN MATEO ETLATONGO': 'SAN MATEO ETLATONGO', 'SAN MATEO NEJAÁPAM': 'SAN MATEO NEJÁPAM', 'SAN MATEO PEÑASCO': 'SAN MATEO PEÑASCO', 'SAN MATEO PIÑAS': 'SAN MATEO PIÑAS', 'SAN MATEO RIÍO HONDO': 'SAN MATEO RÍO HONDO', 'SAN MATEO SINDIHUI': 'SAN MATEO SINDIHUI', 'SAN MATEO TLAPILTEPEC': 'SAN MATEO TLAPILTEPEC', 'SAN MELCHOR BETAZA': 'SAN MELCHOR BETAZA', 'SAN MIGUEL ACHIUTLA': 'SAN MIGUEL ACHIUTLA', 'SAN MIGUEL AHUEHUETITLAÁN': 'SAN MIGUEL AHUEHUETITLÁN', 'SAN MIGUEL ALOAÁPAM': 'SAN MIGUEL ALOÁPAM', 'SAN MIGUEL AMATITLAÁN': 'SAN MIGUEL AMATITLÁN', 'SAN MIGUEL AMATLAÁN': 'SAN MIGUEL AMATLÁN', 'SAN MIGUEL COATLAÁN': 'SAN MIGUEL COATLÁN', 'SAN MIGUEL CHICAHUA': 'SAN MIGUEL CHICAHUA', 'SAN MIGUEL CHIMALAPA': 'SAN MIGUEL CHIMALAPA', 'SAN MIGUEL DEL PUERTO': 'SAN MIGUEL DEL PUERTO', 'SAN MIGUEL DEL RIÍO': 'SAN MIGUEL DEL RÍO', 'SAN MIGUEL EJUTLA': 'SAN MIGUEL EJUTLA', 'SAN MIGUEL EL GRANDE': 'SAN MIGUEL EL GRANDE', 'SAN MIGUEL HUAUTLA': 'SAN MIGUEL HUAUTLA', 'SAN MIGUEL MIXTEPEC': 'SAN MIGUEL MIXTEPEC', 'SAN MIGUEL PANIXTLAHUACA': 'SAN MIGUEL PANIXTLAHUACA', 'SAN MIGUEL PERAS': 'SAN MIGUEL PERAS', 'SAN MIGUEL PIEDRAS': 'SAN MIGUEL PIEDRAS', 'SAN MIGUEL QUETZALTEPEC': 'SAN MIGUEL QUETZALTEPEC', 'SAN MIGUEL SANTA FLOR': 'SAN MIGUEL SANTA FLOR', 'VILLA SOLA DE VEGA': 'VILLA SOLA DE VEGA', 'SAN MIGUEL SOYALTEPEC': 'SAN MIGUEL SOYALTEPEC', 'SAN MIGUEL SUCHIXTEPEC': 'SAN MIGUEL SUCHIXTEPEC', 'VILLA TALEA DE CASTRO': 'VILLA TALEA DE CASTRO', 'SAN MIGUEL TECOMATLAÁN': 'SAN MIGUEL TECOMATLÁN', 'SAN MIGUEL TENANGO': 'SAN MIGUEL TENANGO', 'SAN MIGUEL TEQUIXTEPEC': 'SAN MIGUEL TEQUIXTEPEC', 'SAN MIGUEL TILQUIAÁPAM': 'SAN MIGUEL TILQUIÁPAM', 'SAN MIGUEL TLACAMAMA': 'SAN MIGUEL TLACAMAMA', 'SAN MIGUEL TLACOTEPEC': 'SAN MIGUEL TLACOTEPEC', 'SAN MIGUEL TULANCINGO': 'SAN MIGUEL TULANCINGO', 'SAN MIGUEL YOTAO': 'SAN MIGUEL YOTAO', 'SAN NICOLAÁS': 'SAN NICOLÁS', 'SAN NICOLAÁS HIDALGO': 'SAN NICOLÁS HIDALGO', 'SAN PABLO COATLAÁN': 'SAN PABLO COATLÁN', 'SAN PABLO CUATRO VENADOS': 'SAN PABLO CUATRO VENADOS', 'SAN PABLO ETLA': 'SAN PABLO ETLA', 'SAN PABLO HUITZO': 'SAN PABLO HUITZO', 'SAN PABLO HUIXTEPEC': 'SAN PABLO HUIXTEPEC', 'SAN PABLO MACUILTIANGUIS': 'SAN PABLO MACUILTIANGUIS', 'SAN PABLO TIJALTEPEC': 'SAN PABLO TIJALTEPEC', 'SAN PABLO VILLA DE MITLA': 'SAN PABLO VILLA DE MITLA', 'SAN PABLO YAGANIZA': 'SAN PABLO YAGANIZA', 'SAN PEDRO AMUZGOS': 'SAN PEDRO AMUZGOS', 'SAN PEDRO APOÓSTOL': 'SAN PEDRO APÓSTOL', 'SAN PEDRO ATOYAC': 'SAN PEDRO ATOYAC', 'SAN PEDRO CAJONOS': 'SAN PEDRO CAJONOS', 'SAN PEDRO COXCALTEPEC CAÁNTAROS': 'SAN PEDRO COXCALTEPEC CÁNTAROS', 'SAN PEDRO COMITANCILLO': 'SAN PEDRO COMITANCILLO', 'SAN PEDRO EL ALTO': 'SAN PEDRO EL ALTO', 'SAN PEDRO HUAMELULA': 'SAN PEDRO HUAMELULA', 'SAN PEDRO HUILOTEPEC': 'SAN PEDRO HUILOTEPEC', 'SAN PEDRO IXCATLAÁN': 'SAN PEDRO IXCATLÁN', 'SAN PEDRO IXTLAHUACA': 'SAN PEDRO IXTLAHUACA', 'SAN PEDRO JALTEPETONGO': 'SAN PEDRO JALTEPETONGO', 'SAN PEDRO JICAYAÁN': 'SAN PEDRO JICAYÁN', 'SAN PEDRO JOCOTIPAC': 'SAN PEDRO JOCOTIPAC', 'SAN PEDRO JUCHATENGO': 'SAN PEDRO JUCHATENGO', 'SAN PEDRO MAÁRTIR': 'SAN PEDRO MÁRTIR', 'SAN PEDRO MAÁRTIR QUIECHAPA': 'SAN PEDRO MÁRTIR QUIECHAPA', 'SAN PEDRO MAÁRTIR YUCUXACO': 'SAN PEDRO MÁRTIR YUCUXACO', 'SAN PEDRO MIXTEPEC': 'SAN PEDRO MIXTEPEC', 'SAN PEDRO MOLINOS': 'SAN PEDRO MOLINOS', 'SAN PEDRO NOPALA': 'SAN PEDRO NOPALA', 'SAN PEDRO OCOPETATILLO': 'SAN PEDRO OCOPETATILLO', 'SAN PEDRO OCOTEPEC': 'SAN PEDRO OCOTEPEC', 'SAN PEDRO POCHUTLA': 'SAN PEDRO POCHUTLA', 'SAN PEDRO QUIATONI': 'SAN PEDRO QUIATONI', 'SAN PEDRO SOCHIAÁPAM': 'SAN PEDRO SOCHIÁPAM', 'SAN PEDRO TAPANATEPEC': 'SAN PEDRO TAPANATEPEC', 'SAN PEDRO TAVICHE': 'SAN PEDRO TAVICHE', 'SAN PEDRO TEOZACOALCO': 'SAN PEDRO TEOZACOALCO', 'SAN PEDRO TEUTILA': 'SAN PEDRO TEUTILA', 'SAN PEDRO TIDAAÁ': 'SAN PEDRO TIDAÁ', 'SAN PEDRO TOPILTEPEC': 'SAN PEDRO TOPILTEPEC', 'SAN PEDRO TOTOLAÁPAM': 'SAN PEDRO TOTOLÁPAM', 'VILLA DE TUTUTEPEC': 'VILLA DE TUTUTEPEC', 'SAN PEDRO YANERI': 'SAN PEDRO YANERI', 'SAN PEDRO YOÓLOX': 'SAN PEDRO YÓLOX', 'SAN PEDRO Y SAN PABLO AYUTLA': 'SAN PEDRO Y SAN PABLO AYUTLA', 'VILLA DE ETLA': 'VILLA DE ETLA', 'SAN PEDRO Y SAN PABLO TEPOSCOLULA': 'SAN PEDRO Y SAN PABLO TEPOSCOLULA', 'SAN PEDRO Y SAN PABLO TEQUIXTEPEC': 'SAN PEDRO Y SAN PABLO TEQUIXTEPEC', 'SAN PEDRO YUCUNAMA': 'SAN PEDRO YUCUNAMA', 'SAN RAYMUNDO JALPAN': 'SAN RAYMUNDO JALPAN', 'SAN SEBASTIAÁN ABASOLO': 'SAN SEBASTIÁN ABASOLO', 'SAN SEBASTIAÁN COATLAÁN': 'SAN SEBASTIÁN COATLÁN', 'SAN SEBASTIAÁN IXCAPA': 'SAN SEBASTIÁN IXCAPA', 'SAN SEBASTIAÁN NICANANDUTA': 'SAN SEBASTIÁN NICANANDUTA', 'SAN SEBASTIAÁN RIÍO HONDO': 'SAN SEBASTIÁN RÍO HONDO', 'SAN SEBASTIAÁN TECOMAXTLAHUACA': 'SAN SEBASTIÁN TECOMAXTLAHUACA', 'SAN SEBASTIAÁN TEITIPAC': 'SAN SEBASTIÁN TEITIPAC', 'SAN SEBASTIAÁN TUTLA': 'SAN SEBASTIÁN TUTLA', 'SAN SIMOÓN ALMOLONGAS': 'SAN SIMÓN ALMOLONGAS', 'SAN SIMOÓN ZAHUATLAÁN': 'SAN SIMÓN ZAHUATLÁN', 'SANTA ANA': 'SANTA ANA', 'SANTA ANA ATEIXTLAHUACA': 'SANTA ANA ATEIXTLAHUACA', 'SANTA ANA CUAUHTEÉMOC': 'SANTA ANA CUAUHTÉMOC', 'SANTA ANA DEL VALLE': 'SANTA ANA DEL VALLE', 'SANTA ANA TAVELA': 'SANTA ANA TAVELA', 'SANTA ANA TLAPACOYAN': 'SANTA ANA TLAPACOYAN', 'SANTA ANA YARENI': 'SANTA ANA YARENI', 'SANTA ANA ZEGACHE': 'SANTA ANA ZEGACHE', 'SANTA CATALINA QUIERIÍ': 'SANTA CATALINA QUIERÍ', 'SANTA CATARINA CUIXTLA': 'SANTA CATARINA CUIXTLA', 'SANTA CATARINA IXTEPEJI': 'SANTA CATARINA IXTEPEJI', 'SANTA CATARINA JUQUILA': 'SANTA CATARINA JUQUILA', 'SANTA CATARINA LACHATAO': 'SANTA CATARINA LACHATAO', 'SANTA CATARINA LOXICHA': 'SANTA CATARINA LOXICHA', 'SANTA CATARINA MECHOACAÁN': 'SANTA CATARINA MECHOACÁN', 'SANTA CATARINA MINAS': 'SANTA CATARINA MINAS', 'SANTA CATARINA QUIANEÉ': 'SANTA CATARINA QUIANÉ', 'SANTA CATARINA TAYATA': 'SANTA CATARINA TAYATA', 'SANTA CATARINA TICUAÁ': 'SANTA CATARINA TICUÁ', 'SANTA CATARINA YOSONOTUÚ': 'SANTA CATARINA YOSONOTÚ', 'SANTA CATARINA ZAPOQUILA': 'SANTA CATARINA ZAPOQUILA', 'SANTA CRUZ ACATEPEC': 'SANTA CRUZ ACATEPEC', 'SANTA CRUZ AMILPAS': 'SANTA CRUZ AMILPAS', 'SANTA CRUZ DE BRAVO': 'SANTA CRUZ DE BRAVO', 'SANTA CRUZ ITUNDUJIA': 'SANTA CRUZ ITUNDUJIA', 'SANTA CRUZ MIXTEPEC': 'SANTA CRUZ MIXTEPEC', 'SANTA CRUZ NUNDACO': 'SANTA CRUZ NUNDACO', 'SANTA CRUZ PAPALUTLA': 'SANTA CRUZ PAPALUTLA', 'SANTA CRUZ TACACHE DE MINA': 'SANTA CRUZ TACACHE DE MINA', 'SANTA CRUZ TACAHUA': 'SANTA CRUZ TACAHUA', 'SANTA CRUZ TAYATA': 'SANTA CRUZ TAYATA', 'SANTA CRUZ XITLA': 'SANTA CRUZ XITLA', 'SANTA CRUZ XOXOCOTLAÁN': 'SANTA CRUZ XOXOCOTLÁN', 'SANTA CRUZ ZENZONTEPEC': 'SANTA CRUZ ZENZONTEPEC', 'SANTA GERTRUDIS': 'SANTA GERTRUDIS', 'SANTA INEÉS DEL MONTE': 'SANTA INÉS DEL MONTE', 'SANTA INEÉS YATZECHE': 'SANTA INÉS YATZECHE', 'SANTA LUCIÍA DEL CAMINO': 'SANTA LUCÍA DEL CAMINO', 'SANTA LUCIÍA MIAHUATLAÁN': 'SANTA LUCÍA MIAHUATLÁN', 'SANTA LUCIÍA MONTEVERDE': 'SANTA LUCÍA MONTEVERDE', 'SANTA LUCIÍA OCOTLAÁN': 'SANTA LUCÍA OCOTLÁN', 'SANTA MARIÍA ALOTEPEC': 'SANTA MARÍA ALOTEPEC', 'SANTA MARIÍA APAZCO': 'SANTA MARÍA APAZCO', 'SANTA MARIÍA LA ASUNCIOÓN': 'SANTA MARÍA LA ASUNCIÓN', 'HEROICA CIUDAD DE TLAXIACO': 'HEROICA CIUDAD DE TLAXIACO', 'AYOQUEZCO DE ALDAMA': 'AYOQUEZCO DE ALDAMA', 'SANTA MARIÍA ATZOMPA': 'SANTA MARÍA ATZOMPA', 'SANTA MARIÍA CAMOTLAÁN': 'SANTA MARÍA CAMOTLÁN', 'SANTA MARIÍA COLOTEPEC': 'SANTA MARÍA COLOTEPEC', 'SANTA MARIÍA CORTIJO': 'SANTA MARÍA CORTIJO', 'SANTA MARIÍA COYOTEPEC': 'SANTA MARÍA COYOTEPEC', 'SANTA MARIÍA CHACHOAÁPAM': 'SANTA MARÍA CHACHOÁPAM', 'VILLA DE CHILAPA DE DIÍAZ': 'VILLA DE CHILAPA DE DÍAZ', 'SANTA MARIÍA CHILCHOTLA': 'SANTA MARÍA CHILCHOTLA', 'SANTA MARIÍA CHIMALAPA': 'SANTA MARÍA CHIMALAPA', 'SANTA MARIÍA DEL ROSARIO': 'SANTA MARÍA DEL ROSARIO', 'SANTA MARIÍA DEL TULE': 'SANTA MARÍA DEL TULE', 'SANTA MARIÍA ECATEPEC': 'SANTA MARÍA ECATEPEC', 'SANTA MARIÍA GUELACEÉ': 'SANTA MARÍA GUELACÉ', 'SANTA MARIÍA GUIENAGATI': 'SANTA MARÍA GUIENAGATI', 'SANTA MARIÍA HUATULCO': 'SANTA MARÍA HUATULCO', 'SANTA MARIÍA HUAZOLOTITLAÁN': 'SANTA MARÍA HUAZOLOTITLÁN', 'SANTA MARIÍA IPALAPA': 'SANTA MARÍA IPALAPA', 'SANTA MARIÍA IXCATLAÁN': 'SANTA MARÍA IXCATLÁN', 'SANTA MARIÍA JACATEPEC': 'SANTA MARÍA JACATEPEC',
                                 'SANTA MARIÍA JALAPA DEL MARQUEÉS': 'SANTA MARÍA JALAPA DEL MARQUÉS', 'SANTA MARIÍA JALTIANGUIS': 'SANTA MARÍA JALTIANGUIS', 'SANTA MARIÍA LACHIXIÍO': 'SANTA MARÍA LACHIXÍO', 'SANTA MARIÍA MIXTEQUILLA': 'SANTA MARÍA MIXTEQUILLA', 'SANTA MARIÍA NATIVITAS': 'SANTA MARÍA NATIVITAS', 'SANTA MARIÍA NDUAYACO': 'SANTA MARÍA NDUAYACO', 'SANTA MARIÍA OZOLOTEPEC': 'SANTA MARÍA OZOLOTEPEC', 'SANTA MARIÍA PAÁPALO': 'SANTA MARÍA PÁPALO', 'SANTA MARIÍA PEÑOLES': 'SANTA MARÍA PEÑOLES', 'SANTA MARIÍA PETAPA': 'SANTA MARÍA PETAPA', 'SANTA MARIÍA QUIEGOLANI': 'SANTA MARÍA QUIEGOLANI', 'SANTA MARIÍA SOLA': 'SANTA MARÍA SOLA', 'SANTA MARIÍA TATALTEPEC': 'SANTA MARÍA TATALTEPEC', 'SANTA MARIÍA TECOMAVACA': 'SANTA MARÍA TECOMAVACA', 'SANTA MARIÍA TEMAXCALAPA': 'SANTA MARÍA TEMAXCALAPA', 'SANTA MARIÍA TEMAXCALTEPEC': 'SANTA MARÍA TEMAXCALTEPEC', 'SANTA MARIÍA TEOPOXCO': 'SANTA MARÍA TEOPOXCO', 'SANTA MARIÍA TEPANTLALI': 'SANTA MARÍA TEPANTLALI', 'SANTA MARIÍA TEXCATITLAÁN': 'SANTA MARÍA TEXCATITLÁN', 'SANTA MARIÍA TLAHUITOLTEPEC': 'SANTA MARÍA TLAHUITOLTEPEC', 'SANTA MARIÍA TLALIXTAC': 'SANTA MARÍA TLALIXTAC', 'SANTA MARIÍA TONAMECA': 'SANTA MARÍA TONAMECA', 'SANTA MARIÍA TOTOLAPILLA': 'SANTA MARÍA TOTOLAPILLA', 'SANTA MARIÍA XADANI': 'SANTA MARÍA XADANI', 'SANTA MARIÍA YALINA': 'SANTA MARÍA YALINA', 'SANTA MARIÍA YAVESIÍA': 'SANTA MARÍA YAVESÍA', 'SANTA MARIÍA YOLOTEPEC': 'SANTA MARÍA YOLOTEPEC', 'SANTA MARIÍA YOSOYUÚA': 'SANTA MARÍA YOSOYÚA', 'SANTA MARIÍA YUCUHITI': 'SANTA MARÍA YUCUHITI', 'SANTA MARIÍA ZACATEPEC': 'SANTA MARÍA ZACATEPEC', 'SANTA MARIÍA ZANIZA': 'SANTA MARÍA ZANIZA', 'SANTA MARIÍA ZOQUITLAÁN': 'SANTA MARÍA ZOQUITLÁN', 'SANTIAGO AMOLTEPEC': 'SANTIAGO AMOLTEPEC', 'SANTIAGO APOALA': 'SANTIAGO APOALA', 'SANTIAGO APOÓSTOL': 'SANTIAGO APÓSTOL', 'SANTIAGO ASTATA': 'SANTIAGO ASTATA', 'SANTIAGO ATITLAÁN': 'SANTIAGO ATITLÁN', 'SANTIAGO AYUQUILILLA': 'SANTIAGO AYUQUILILLA', 'SANTIAGO CACALOXTEPEC': 'SANTIAGO CACALOXTEPEC', 'SANTIAGO CAMOTLAÁN': 'SANTIAGO CAMOTLÁN', 'SANTIAGO COMALTEPEC': 'SANTIAGO COMALTEPEC', 'VILLA DE SANTIAGO CHAZUMBA': 'VILLA DE SANTIAGO CHAZUMBA', 'SANTIAGO CHOAÁPAM': 'SANTIAGO CHOÁPAM', 'SANTIAGO DEL RIÍO': 'SANTIAGO DEL RÍO', 'SANTIAGO HUAJOLOTITLAÁN': 'SANTIAGO HUAJOLOTITLÁN', 'SANTIAGO HUAUCLILLA': 'SANTIAGO HUAUCLILLA', 'SANTIAGO IHUITLAÁN PLUMAS': 'SANTIAGO IHUITLÁN PLUMAS', 'SANTIAGO IXCUINTEPEC': 'SANTIAGO IXCUINTEPEC', 'SANTIAGO IXTAYUTLA': 'SANTIAGO IXTAYUTLA', 'SANTIAGO JAMILTEPEC': 'SANTIAGO JAMILTEPEC', 'SANTIAGO JOCOTEPEC': 'SANTIAGO JOCOTEPEC', 'SANTIAGO JUXTLAHUACA': 'SANTIAGO JUXTLAHUACA', 'SANTIAGO LACHIGUIRI': 'SANTIAGO LACHIGUIRI', 'SANTIAGO LALOPA': 'SANTIAGO LALOPA', 'SANTIAGO LAOLLAGA': 'SANTIAGO LAOLLAGA', 'SANTIAGO LAXOPA': 'SANTIAGO LAXOPA', 'SANTIAGO LLANO GRANDE': 'SANTIAGO LLANO GRANDE', 'SANTIAGO MATATLAÁN': 'SANTIAGO MATATLÁN', 'SANTIAGO MILTEPEC': 'SANTIAGO MILTEPEC', 'SANTIAGO MINAS': 'SANTIAGO MINAS', 'SANTIAGO NACALTEPEC': 'SANTIAGO NACALTEPEC', 'SANTIAGO NEJAPILLA': 'SANTIAGO NEJAPILLA', 'SANTIAGO NUNDICHE': 'SANTIAGO NUNDICHE', 'SANTIAGO NUYOOÓ': 'SANTIAGO NUYOÓ', 'SANTIAGO PINOTEPA NACIONAL': 'SANTIAGO PINOTEPA NACIONAL', 'SANTIAGO SUCHILQUITONGO': 'SANTIAGO SUCHILQUITONGO', 'SANTIAGO TAMAZOLA': 'SANTIAGO TAMAZOLA', 'SANTIAGO TAPEXTLA': 'SANTIAGO TAPEXTLA', 'VILLA TEJUÚPAM DE LA UNIOÓN': 'VILLA TEJÚPAM DE LA UNIÓN', 'SANTIAGO TENANGO': 'SANTIAGO TENANGO', 'SANTIAGO TEPETLAPA': 'SANTIAGO TEPETLAPA', 'SANTIAGO TETEPEC': 'SANTIAGO TETEPEC', 'SANTIAGO TEXCALCINGO': 'SANTIAGO TEXCALCINGO', 'SANTIAGO TEXTITLAÁN': 'SANTIAGO TEXTITLÁN', 'SANTIAGO TILANTONGO': 'SANTIAGO TILANTONGO', 'SANTIAGO TILLO': 'SANTIAGO TILLO', 'SANTIAGO TLAZOYALTEPEC': 'SANTIAGO TLAZOYALTEPEC', 'SANTIAGO XANICA': 'SANTIAGO XANICA', 'SANTIAGO XIACUIÍ': 'SANTIAGO XIACUÍ', 'SANTIAGO YAITEPEC': 'SANTIAGO YAITEPEC', 'SANTIAGO YAVEO': 'SANTIAGO YAVEO', 'SANTIAGO YOLOMEÉCATL': 'SANTIAGO YOLOMÉCATL', 'SANTIAGO YOSONDUÚA': 'SANTIAGO YOSONDÚA', 'SANTIAGO YUCUYACHI': 'SANTIAGO YUCUYACHI', 'SANTIAGO ZACATEPEC': 'SANTIAGO ZACATEPEC', 'SANTIAGO ZOOCHILA': 'SANTIAGO ZOOCHILA', 'NUEVO ZOQUIAÁPAM': 'NUEVO ZOQUIÁPAM', 'SANTO DOMINGO INGENIO': 'SANTO DOMINGO INGENIO', 'SANTO DOMINGO ALBARRADAS': 'SANTO DOMINGO ALBARRADAS', 'SANTO DOMINGO ARMENTA': 'SANTO DOMINGO ARMENTA', 'SANTO DOMINGO CHIHUITAÁN': 'SANTO DOMINGO CHIHUITÁN', 'SANTO DOMINGO DE MORELOS': 'SANTO DOMINGO DE MORELOS', 'SANTO DOMINGO IXCATLAÁN': 'SANTO DOMINGO IXCATLÁN', 'SANTO DOMINGO NUXAAÁ': 'SANTO DOMINGO NUXAÁ', 'SANTO DOMINGO OZOLOTEPEC': 'SANTO DOMINGO OZOLOTEPEC', 'SANTO DOMINGO PETAPA': 'SANTO DOMINGO PETAPA', 'SANTO DOMINGO ROAYAGA': 'SANTO DOMINGO ROAYAGA', 'SANTO DOMINGO TEHUANTEPEC': 'SANTO DOMINGO TEHUANTEPEC', 'SANTO DOMINGO TEOJOMULCO': 'SANTO DOMINGO TEOJOMULCO', 'SANTO DOMINGO TEPUXTEPEC': 'SANTO DOMINGO TEPUXTEPEC', 'SANTO DOMINGO TLATAYAÁPAM': 'SANTO DOMINGO TLATAYÁPAM', 'SANTO DOMINGO TOMALTEPEC': 'SANTO DOMINGO TOMALTEPEC', 'SANTO DOMINGO TONALAÁ': 'SANTO DOMINGO TONALÁ', 'SANTO DOMINGO TONALTEPEC': 'SANTO DOMINGO TONALTEPEC', 'SANTO DOMINGO XAGACIÍA': 'SANTO DOMINGO XAGACÍA', 'SANTO DOMINGO YANHUITLAÁN': 'SANTO DOMINGO YANHUITLÁN', 'SANTO DOMINGO YODOHINO': 'SANTO DOMINGO YODOHINO', 'SANTO DOMINGO ZANATEPEC': 'SANTO DOMINGO ZANATEPEC', 'SANTOS REYES NOPALA': 'SANTOS REYES NOPALA', 'SANTOS REYES PAÁPALO': 'SANTOS REYES PÁPALO', 'SANTOS REYES TEPEJILLO': 'SANTOS REYES TEPEJILLO', 'SANTOS REYES YUCUNAÁ': 'SANTOS REYES YUCUNÁ', 'SANTO TOMAÁS JALIEZA': 'SANTO TOMÁS JALIEZA', 'SANTO TOMAÁS MAZALTEPEC': 'SANTO TOMÁS MAZALTEPEC', 'SANTO TOMAÁS OCOTEPEC': 'SANTO TOMÁS OCOTEPEC', 'SANTO TOMAÁS TAMAZULAPAN': 'SANTO TOMÁS TAMAZULAPAN', 'SAN VICENTE COATLAÁN': 'SAN VICENTE COATLÁN', 'SAN VICENTE LACHIXIÍO': 'SAN VICENTE LACHIXÍO', 'SAN VICENTE NUÑUÚ': 'SAN VICENTE NUÑÚ', 'SILACAYOAÁPAM': 'SILACAYOÁPAM', 'SITIO DE XITLAPEHUA': 'SITIO DE XITLAPEHUA', 'SOLEDAD ETLA': 'SOLEDAD ETLA', 'VILLA DE TAMAZULAÁPAM DEL PROGRESO': 'VILLA DE TAMAZULÁPAM DEL PROGRESO', 'TANETZE DE ZARAGOZA': 'TANETZE DE ZARAGOZA', 'TANICHE': 'TANICHE', 'TATALTEPEC DE VALDEÉS': 'TATALTEPEC DE VALDÉS', 'TEOCOCUILCO DE MARCOS PEÉREZ': 'TEOCOCUILCO DE MARCOS PÉREZ', 'TEOTITLAÁN DE FLORES MAGOÓN': 'TEOTITLÁN DE FLORES MAGÓN', 'TEOTITLAÁN DEL VALLE': 'TEOTITLÁN DEL VALLE', 'TEOTONGO': 'TEOTONGO', 'TEPELMEME VILLA DE MORELOS': 'TEPELMEME VILLA DE MORELOS', 'HEROICA VILLA TEZOATLAÁN DE SEGURA Y LUNA': 'HEROICA VILLA TEZOATLÁN DE SEGURA Y LUNA', 'SAN JEROÓNIMO TLACOCHAHUAYA': 'SAN JERÓNIMO TLACOCHAHUAYA', 'TLACOLULA DE MATAMOROS': 'TLACOLULA DE MATAMOROS', 'TLACOTEPEC PLUMAS': 'TLACOTEPEC PLUMAS', 'TLALIXTAC DE CABRERA': 'TLALIXTAC DE CABRERA', 'TOTONTEPEC VILLA DE MORELOS': 'TOTONTEPEC VILLA DE MORELOS', 'TRINIDAD ZAACHILA': 'TRINIDAD ZAACHILA', 'LA TRINIDAD VISTA HERMOSA': 'LA TRINIDAD VISTA HERMOSA', 'UNIOÓN HIDALGO': 'UNIÓN HIDALGO', 'VALERIO TRUJANO': 'VALERIO TRUJANO', 'SAN JUAN BAUTISTA VALLE NACIONAL': 'SAN JUAN BAUTISTA VALLE NACIONAL', 'VILLA DIÍAZ ORDAZ': 'VILLA DÍAZ ORDAZ', 'YAXE': 'YAXE', 'MAGDALENA YODOCONO DE PORFIRIO DIÍAZ': 'MAGDALENA YODOCONO DE PORFIRIO DÍAZ', 'YOGANA': 'YOGANA', 'YUTANDUCHI DE GUERRERO': 'YUTANDUCHI DE GUERRERO', 'VILLA DE ZAACHILA': 'VILLA DE ZAACHILA', 'SAN MATEO YUCUTINDOO': 'SAN MATEO YUCUTINDOO', 'ZAPOTITLAÁN LAGUNAS': 'ZAPOTITLÁN LAGUNAS', 'ZAPOTITLAÁN PALMAS': 'ZAPOTITLÁN PALMAS', 'SANTA INEÉS DE ZARAGOZA': 'SANTA INÉS DE ZARAGOZA', 'ZIMATLAÁN DE AÁLVAREZ': 'ZIMATLÁN DE ÁLVAREZ' }
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'PUEB', estado_republica, re.IGNORECASE):             
            ciudades_clave = [ 'MUNICIPIO DE PUEBLA', 'ZACATL[AÁ]N', 'ACAJETE', 'ACATENO', 'ACATL[AÁ]N', 'ACATZINGO', 'ACTEOPAN', 'AHUACATL[AÁ]N', 'AHUATL[AÁ]N', 'AHUAZOTEPEC', 'AHUEHUETITLA', 'AJALPAN', 'ALBINO ZERTUCHE', 'ALJOJUCA', 'ALTEPEXI', 'AMIXTL[AÁ]N', 'AMOZOC', 'AQUIXTLA', 'ATEMPAN', 'ATEXCAL', 'ATLIXCO', 'ATOYATEMPAN', 'ATZALA', 'ATZITZIHUAC[AÁ]N', 'ATZITZINTLA', 'AXUTLA', 'AYOTOXCO DE GUERRERO', 'CALPAN', 'CALTEPEC', 'CAMOCUAUTLA', 'CAXHUACAN', 'COATEPEC', 'COATZINGO', 'COHETZALA', 'COHUECAN', 'CORONANGO', 'COXCATL[AÁ]N', 'COYOMEAPAN', 'COYOTEPEC', 'CUAPIAXTLA DE MADERO', 'CUAUTEMPAN', 'CUAUTINCH[AÁ]N', 'CUAUTLANCINGO', 'CUAYUCA DE ANDRADE', 'CUETZALAN DEL PROGRESO', 'CUYOACO', 'CHALCHICOMULA DE SESMA', 'CHAPULCO', 'CHIAUTLA', 'CHIAUTZINGO', 'CHICONCUAUTLA', 'CHICHIQUILA', 'CHIETLA', 'CHIGMECATITL[AÁ]N', 'CHIGNAHUAPAN', 'CHIGNAUTLA', 'CHILA', 'CHILA DE LA SAL', 'HONEY', 'CHILCHOTLA', 'CHINANTLA', 'DOMINGO ARENAS', 'ELOXOCHITL[AÁ]N', 'EPATL[AÁ]N', 'ESPERANZA', 'FRANCISCO Z. MENA', 'GENERAL FELIPE [AÁ]NGELES', 'GUADALUPE', 'GUADALUPE VICTORIA', 'HERMENEGILDO GALEANA', 'HUAQUECHULA', 'HUATLATLAUCA', 'HUAUCHINANGO', 'HUEHUETLA', 'HUEHUETL[AÁ]N EL CHICO', 'HUEJOTZINGO', 'HUEYAPAN', 'HUEYTAMALCO', 'HUEYTLALPAN', 'HUITZILAN DE SERD[AÁ]N', 'HUITZILTEPEC', 'ATLEQUIZAYAN', 'IXCAMILPA DE GUERRERO', 'IXCAQUIXTLA', 'IXTACAMAXTITL[AÁ]N', 'IXTEPEC', 'IZ[UÚ]CAR DE MATAMOROS', 'JALPAN', 'JOLALPAN', 'JONOTLA', 'JOPALA', 'JUAN C. BONILLA', 'JUAN GALINDO', 'JUAN N. M[EÉ]NDEZ', 'LAFRAGUA', 'LIBRES', 'LA MAGDALENA TLATLAUQUITEPEC', 'MAZAPILTEPEC DE JU[AÁ]REZ', 'MIXTLA', 'MOLCAXAC', 'CAÑADA MORELOS', 'NAUPAN', 'NAUZONTLA', 'NEALTICAN', 'NICOL[AÁ]S BRAVO', 'NOPALUCAN', 'OCOTEPEC', 'OCOYUCAN', 'OLINTLA', 'ORIENTAL', 'PAHUATL[AÁ]N', 'PALMAR DE BRAVO', 'PANTEPEC', 'PETLALCINGO', 'PIAXTLA', 'CIUDAD DE PUEBLA', 'QUECHOLAC', 'QUIMIXTL[AÁ]N', 'RAFAEL LARA GRAJALES', 'LOS REYES DE JU[AÁ]REZ', 'SAN ANDR[EÉ]S CHOLULA', 'SAN ANTONIO CAÑADA', 'SAN DIEGO LA MESA TOCHIMILTZINGO', 'SAN FELIPE TEOTLALCINGO', 'SAN FELIPE TEPATL[AÁ]N', 'SAN GABRIEL CHILAC', 'SAN GREGORIO ATZOMPA', 'SAN JER[OÓ]NIMO TECUANIPAN', 'SAN JER[OÓ]NIMO XAYACATL[AÁ]N', 'SAN JOS[EÉ] CHIAPA', 'SAN JOS[EÉ] MIAHUATL[AÁ]N', 'SAN JUAN ATENCO', 'SAN JUAN ATZOMPA', 'SAN MART[IÍ]N TEXMELUCAN', 'SAN MART[IÍ]N TOTOLTEPEC', 'SAN MAT[IÍ]AS TLALANCALECA', 'SAN MIGUEL IXITL[AÁ]N', 'SAN MIGUEL XOXTLA', 'SAN NICOL[AÁ]S BUENOS AIRES', 'SAN NICOL[AÁ]S DE LOS RANCHOS', 'SAN PABLO ANICANO', 'SAN PEDRO CHOLULA', 'SAN PEDRO YELOIXTLAHUACA', 'SAN SALVADOR EL SECO', 'SAN SALVADOR EL VERDE', 'SAN SALVADOR HUIXCOLOTLA', 'SAN SEBASTI[AÁ]N TLACOTEPEC', 'SANTA CATARINA TLALTEMPAN', 'SANTA IN[EÉ]S AHUATEMPAN', 'SANTA ISABEL CHOLULA', 'SANTIAGO MIAHUATL[AÁ]N', 'HUEHUETL[AÁ]N EL GRANDE', 'SANTO TOM[AÁ]S HUEYOTLIPAN', 'SOLTEPEC', 'TECALI DE HERRERA', 'TECAMACHALCO', 'TECOMATL[AÁ]N', 'TEHUAC[AÁ]N', 'TEHUITZINGO', 'TENAMPULCO', 'TEOPANTL[AÁ]N', 'TEOTLALCO', 'TEPANCO DE L[OÓ]PEZ', 'TEPANGO DE RODR[IÍ]GUEZ', 'TEPATLAXCO DE HIDALGO', 'TEPEACA', 'TEPEMAXALCO', 'TEPEOJUMA', 'TEPETZINTLA', 'TEPEXCO', 'TEPEXI DE RODR[IÍ]GUEZ', 'TEPEYAHUALCO', 'TEPEYAHUALCO DE CUAUHT[EÉ]MOC', 'TETELA DE OCAMPO', 'TETELES DE [AÁ]VILA CASTILLO', 'TEZIUTL[AÁ]N', 'TIANGUISMANALCO', 'TILAPA', 'TLACOTEPEC DE BENITO JU[AÁ]REZ', 'TLACUILOTEPEC', 'TLACHICHUCA', 'TLAHUAPAN', 'TLALTENANGO', 'TLANEPANTLA', 'TLAOLA', 'TLAPACOYA', 'TLAPANAL[AÁ]', 'TLATLAUQUITEPEC', 'TLAXCO', 'TOCHIMILCO', 'TOCHTEPEC', 'TOTOLTEPEC DE GUERRERO', 'TULCINGO', 'TUZAMAPAN DE GALEANA', 'TZICATLACOYAN', 'VENUSTIANO CARRANZA', 'VICENTE GUERRERO', 'XAYACATL[AÁ]N DE BRAVO', 'XICOTEPEC', 'XICOTL[AÁ]N', 'XIUTETELCO', 'XOCHIAPULCO', 'XOCHILTEPEC', 'XOCHITL[AÁ]N DE VICENTE SU[AÁ]REZ', 'XOCHITL[AÁ]N TODOS SANTOS', 'YAON[AÁ]HUAC', 'YEHUALTEPEC', 'ZACAPALA', 'ZACAPOAXTLA', 'ZAPOTITL[AÁ]N', 'ZAPOTITL[AÁ]N DE M[EÉ]NDEZ', 'ZARAGOZA', 'ZAUTLA', 'ZIHUATEUTLA', 'ZINACATEPEC', 'ZONGOZOTLA', 'ZOQUIAPAN', 'ZOQUITL[AÁ]N', 'PUEBLA']
            patrones_ciudades = { 'MUNICIPIO DE PUEBLA': 'CIUDAD DE PUEBLA', 'ZACATLAÁN': 'ZACATLÁN', 'ACAJETE': 'ACAJETE', 'ACATENO': 'ACATENO', 'ACATLAÁN': 'ACATLÁN', 'ACATZINGO': 'ACATZINGO', 'ACTEOPAN': 'ACTEOPAN', 'AHUACATLAÁN': 'AHUACATLÁN', 'AHUATLAÁN': 'AHUATLÁN', 'AHUAZOTEPEC': 'AHUAZOTEPEC', 'AHUEHUETITLA': 'AHUEHUETITLA', 'AJALPAN': 'AJALPAN', 'ALBINO ZERTUCHE': 'ALBINO ZERTUCHE', 'ALJOJUCA': 'ALJOJUCA', 'ALTEPEXI': 'ALTEPEXI', 'AMIXTLAÁN': 'AMIXTLÁN', 'AMOZOC': 'AMOZOC', 'AQUIXTLA': 'AQUIXTLA', 'ATEMPAN': 'ATEMPAN', 'ATEXCAL': 'ATEXCAL', 'ATLIXCO': 'ATLIXCO', 'ATOYATEMPAN': 'ATOYATEMPAN', 'ATZALA': 'ATZALA', 'ATZITZIHUACAÁN': 'ATZITZIHUACÁN', 'ATZITZINTLA': 'ATZITZINTLA', 'AXUTLA': 'AXUTLA', 'AYOTOXCO DE GUERRERO': 'AYOTOXCO DE GUERRERO', 'CALPAN': 'CALPAN', 'CALTEPEC': 'CALTEPEC', 'CAMOCUAUTLA': 'CAMOCUAUTLA', 'CAXHUACAN': 'CAXHUACAN', 'COATEPEC': 'COATEPEC', 'COATZINGO': 'COATZINGO', 'COHETZALA': 'COHETZALA', 'COHUECAN': 'COHUECAN', 'CORONANGO': 'CORONANGO', 'COXCATLAÁN': 'COXCATLÁN', 'COYOMEAPAN': 'COYOMEAPAN', 'COYOTEPEC': 'COYOTEPEC', 'CUAPIAXTLA DE MADERO': 'CUAPIAXTLA DE MADERO', 'CUAUTEMPAN': 'CUAUTEMPAN', 'CUAUTINCHAÁN': 'CUAUTINCHÁN', 'CUAUTLANCINGO': 'CUAUTLANCINGO', 'CUAYUCA DE ANDRADE': 'CUAYUCA DE ANDRADE', 'CUETZALAN DEL PROGRESO': 'CUETZALAN DEL PROGRESO', 'CUYOACO': 'CUYOACO', 'CHALCHICOMULA DE SESMA': 'CHALCHICOMULA DE SESMA', 'CHAPULCO': 'CHAPULCO', 'CHIAUTLA': 'CHIAUTLA', 'CHIAUTZINGO': 'CHIAUTZINGO', 'CHICONCUAUTLA': 'CHICONCUAUTLA', 'CHICHIQUILA': 'CHICHIQUILA', 'CHIETLA': 'CHIETLA', 'CHIGMECATITLAÁN': 'CHIGMECATITLÁN', 'CHIGNAHUAPAN': 'CHIGNAHUAPAN', 'CHIGNAUTLA': 'CHIGNAUTLA', 'CHILA': 'CHILA', 'CHILA DE LA SAL': 'CHILA DE LA SAL', 'HONEY': 'HONEY', 'CHILCHOTLA': 'CHILCHOTLA', 'CHINANTLA': 'CHINANTLA', 'DOMINGO ARENAS': 'DOMINGO ARENAS', 'ELOXOCHITLAÁN': 'ELOXOCHITLÁN', 'EPATLAÁN': 'EPATLÁN', 'ESPERANZA': 'ESPERANZA', 'FRANCISCO Z. MENA': 'FRANCISCO Z. MENA', 'GENERAL FELIPE AÁNGELES': 'GENERAL FELIPE ÁNGELES', 'GUADALUPE': 'GUADALUPE', 'GUADALUPE VICTORIA': 'GUADALUPE VICTORIA', 'HERMENEGILDO GALEANA': 'HERMENEGILDO GALEANA', 'HUAQUECHULA': 'HUAQUECHULA', 'HUATLATLAUCA': 'HUATLATLAUCA', 'HUAUCHINANGO': 'HUAUCHINANGO', 'HUEHUETLA': 'HUEHUETLA', 'HUEHUETLAÁN EL CHICO': 'HUEHUETLÁN EL CHICO', 'HUEJOTZINGO': 'HUEJOTZINGO', 'HUEYAPAN': 'HUEYAPAN', 'HUEYTAMALCO': 'HUEYTAMALCO', 'HUEYTLALPAN': 'HUEYTLALPAN', 'HUITZILAN DE SERDAÁN': 'HUITZILAN DE SERDÁN', 'HUITZILTEPEC': 'HUITZILTEPEC', 'ATLEQUIZAYAN': 'ATLEQUIZAYAN', 'IXCAMILPA DE GUERRERO': 'IXCAMILPA DE GUERRERO', 'IXCAQUIXTLA': 'IXCAQUIXTLA', 'IXTACAMAXTITLAÁN': 'IXTACAMAXTITLÁN', 'IXTEPEC': 'IXTEPEC', 'IZUÚCAR DE MATAMOROS': 'IZÚCAR DE MATAMOROS', 'JALPAN': 'JALPAN', 'JOLALPAN': 'JOLALPAN', 'JONOTLA': 'JONOTLA', 'JOPALA': 'JOPALA', 'JUAN C. BONILLA': 'JUAN C. BONILLA', 'JUAN GALINDO': 'JUAN GALINDO', 'JUAN N. MEÉNDEZ': 'JUAN N. MÉNDEZ', 'LAFRAGUA': 'LAFRAGUA', 'LIBRES': 'LIBRES', 'LA MAGDALENA TLATLAUQUITEPEC': 'LA MAGDALENA TLATLAUQUITEPEC', 'MAZAPILTEPEC DE JUAÁREZ': 'MAZAPILTEPEC DE JUÁREZ', 'MIXTLA': 'MIXTLA', 'MOLCAXAC': 'MOLCAXAC', 'CAÑADA MORELOS': 'CAÑADA MORELOS', 'NAUPAN': 'NAUPAN', 'NAUZONTLA': 'NAUZONTLA', 'NEALTICAN': 'NEALTICAN', 'NICOLAÁS BRAVO': 'NICOLÁS BRAVO', 'NOPALUCAN': 'NOPALUCAN', 'OCOTEPEC': 'OCOTEPEC', 'OCOYUCAN': 'OCOYUCAN', 'OLINTLA': 'OLINTLA', 'ORIENTAL': 'ORIENTAL', 'PAHUATLAÁN': 'PAHUATLÁN', 'PALMAR DE BRAVO': 'PALMAR DE BRAVO', 'PANTEPEC': 'PANTEPEC', 'PETLALCINGO': 'PETLALCINGO', 'PIAXTLA': 'PIAXTLA', 'CIUDAD DE PUEBLA': 'PUEBLA', 'QUECHOLAC': 'QUECHOLAC', 'QUIMIXTLAÁN': 'QUIMIXTLÁN', 'RAFAEL LARA GRAJALES': 'RAFAEL LARA GRAJALES', 'LOS REYES DE JUAÁREZ': 'LOS REYES DE JUÁREZ', 'SAN ANDREÉS CHOLULA': 'SAN ANDRÉS CHOLULA', 'SAN ANTONIO CAÑADA': 'SAN ANTONIO CAÑADA', 'SAN DIEGO LA MESA TOCHIMILTZINGO': 'SAN DIEGO LA MESA TOCHIMILTZINGO', 'SAN FELIPE TEOTLALCINGO': 'SAN FELIPE TEOTLALCINGO', 'SAN FELIPE TEPATLAÁN': 'SAN FELIPE TEPATLÁN', 'SAN GABRIEL CHILAC': 'SAN GABRIEL CHILAC', 'SAN GREGORIO ATZOMPA': 'SAN GREGORIO ATZOMPA', 'SAN JEROÓNIMO TECUANIPAN': 'SAN JERÓNIMO TECUANIPAN', 'SAN JEROÓNIMO XAYACATLAÁN': 'SAN JERÓNIMO XAYACATLÁN', 'SAN JOSEÉ CHIAPA': 'SAN JOSÉ CHIAPA', 'SAN JOSEÉ MIAHUATLAÁN': 'SAN JOSÉ MIAHUATLÁN', 'SAN JUAN ATENCO': 'SAN JUAN ATENCO', 'SAN JUAN ATZOMPA': 'SAN JUAN ATZOMPA', 'SAN MARTIÍN TEXMELUCAN': 'SAN MARTÍN TEXMELUCAN', 'SAN MARTIÍN TOTOLTEPEC': 'SAN MARTÍN TOTOLTEPEC', 'SAN MATIÍAS TLALANCALECA': 'SAN MATÍAS TLALANCALECA', 'SAN MIGUEL IXITLAÁN': 'SAN MIGUEL IXITLÁN', 'SAN MIGUEL XOXTLA': 'SAN MIGUEL XOXTLA', 'SAN NICOLAÁS BUENOS AIRES': 'SAN NICOLÁS BUENOS AIRES', 'SAN NICOLAÁS DE LOS RANCHOS': 'SAN NICOLÁS DE LOS RANCHOS', 'SAN PABLO ANICANO': 'SAN PABLO ANICANO', 'SAN PEDRO CHOLULA': 'SAN PEDRO CHOLULA', 'SAN PEDRO YELOIXTLAHUACA': 'SAN PEDRO YELOIXTLAHUACA', 'SAN SALVADOR EL SECO': 'SAN SALVADOR EL SECO', 'SAN SALVADOR EL VERDE': 'SAN SALVADOR EL VERDE', 'SAN SALVADOR HUIXCOLOTLA': 'SAN SALVADOR HUIXCOLOTLA', 'SAN SEBASTIAÁN TLACOTEPEC': 'SAN SEBASTIÁN TLACOTEPEC', 'SANTA CATARINA TLALTEMPAN': 'SANTA CATARINA TLALTEMPAN', 'SANTA INEÉS AHUATEMPAN': 'SANTA INÉS AHUATEMPAN', 'SANTA ISABEL CHOLULA': 'SANTA ISABEL CHOLULA', 'SANTIAGO MIAHUATLAÁN': 'SANTIAGO MIAHUATLÁN', 'HUEHUETLAÁN EL GRANDE': 'HUEHUETLÁN EL GRANDE', 'SANTO TOMAÁS HUEYOTLIPAN': 'SANTO TOMÁS HUEYOTLIPAN', 'SOLTEPEC': 'SOLTEPEC', 'TECALI DE HERRERA': 'TECALI DE HERRERA', 'TECAMACHALCO': 'TECAMACHALCO', 'TECOMATLAÁN': 'TECOMATLÁN', 'TEHUACAÁN': 'TEHUACÁN', 'TEHUITZINGO': 'TEHUITZINGO', 'TENAMPULCO': 'TENAMPULCO', 'TEOPANTLAÁN': 'TEOPANTLÁN', 'TEOTLALCO': 'TEOTLALCO', 'TEPANCO DE LOÓPEZ': 'TEPANCO DE LÓPEZ', 'TEPANGO DE RODRIÍGUEZ': 'TEPANGO DE RODRÍGUEZ', 'TEPATLAXCO DE HIDALGO': 'TEPATLAXCO DE HIDALGO', 'TEPEACA': 'TEPEACA', 'TEPEMAXALCO': 'TEPEMAXALCO', 'TEPEOJUMA': 'TEPEOJUMA', 'TEPETZINTLA': 'TEPETZINTLA', 'TEPEXCO': 'TEPEXCO', 'TEPEXI DE RODRIÍGUEZ': 'TEPEXI DE RODRÍGUEZ', 'TEPEYAHUALCO': 'TEPEYAHUALCO', 'TEPEYAHUALCO DE CUAUHTEÉMOC': 'TEPEYAHUALCO DE CUAUHTÉMOC', 'TETELA DE OCAMPO': 'TETELA DE OCAMPO', 'TETELES DE AÁVILA CASTILLO': 'TETELES DE ÁVILA CASTILLO', 'TEZIUTLAÁN': 'TEZIUTLÁN', 'TIANGUISMANALCO': 'TIANGUISMANALCO', 'TILAPA': 'TILAPA', 'TLACOTEPEC DE BENITO JUAÁREZ': 'TLACOTEPEC DE BENITO JUÁREZ', 'TLACUILOTEPEC': 'TLACUILOTEPEC', 'TLACHICHUCA': 'TLACHICHUCA', 'TLAHUAPAN': 'TLAHUAPAN', 'TLALTENANGO': 'TLALTENANGO', 'TLANEPANTLA': 'TLANEPANTLA', 'TLAOLA': 'TLAOLA', 'TLAPACOYA': 'TLAPACOYA', 'TLAPANALAÁ': 'TLAPANALÁ', 'TLATLAUQUITEPEC': 'TLATLAUQUITEPEC', 'TLAXCO': 'TLAXCO', 'TOCHIMILCO': 'TOCHIMILCO', 'TOCHTEPEC': 'TOCHTEPEC', 'TOTOLTEPEC DE GUERRERO': 'TOTOLTEPEC DE GUERRERO', 'TULCINGO': 'TULCINGO', 'TUZAMAPAN DE GALEANA': 'TUZAMAPAN DE GALEANA', 'TZICATLACOYAN': 'TZICATLACOYAN', 'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA', 'VICENTE GUERRERO': 'VICENTE GUERRERO', 'XAYACATLAÁN DE BRAVO': 'XAYACATLÁN DE BRAVO', 'XICOTEPEC': 'XICOTEPEC', 'XICOTLAÁN': 'XICOTLÁN', 'XIUTETELCO': 'XIUTETELCO', 'XOCHIAPULCO': 'XOCHIAPULCO', 'XOCHILTEPEC': 'XOCHILTEPEC', 'XOCHITLAÁN DE VICENTE SUAÁREZ': 'XOCHITLÁN DE VICENTE SUÁREZ', 'XOCHITLAÁN TODOS SANTOS': 'XOCHITLÁN TODOS SANTOS', 'YAONAÁHUAC': 'YAONÁHUAC', 'YEHUALTEPEC': 'YEHUALTEPEC', 'ZACAPALA': 'ZACAPALA', 'ZACAPOAXTLA': 'ZACAPOAXTLA', 'ZAPOTITLAÁN': 'ZAPOTITLÁN', 'ZAPOTITLAÁN DE MEÉNDEZ': 'ZAPOTITLÁN DE MÉNDEZ', 'ZARAGOZA': 'ZARAGOZA', 'ZAUTLA': 'ZAUTLA', 'ZIHUATEUTLA': 'ZIHUATEUTLA', 'ZINACATEPEC': 'ZINACATEPEC', 'ZONGOZOTLA': 'ZONGOZOTLA', 'ZOQUIAPAN': 'ZOQUIAPAN', 'ZOQUITLAÁN': 'ZOQUITLÁN', 'PUEBLA': 'PUEBLA' }
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'QUER', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['MUNICIPIO DE QUER[EÉ]T', 'AMEALCO DE BONFIL', 'PINAL DE AMOLES', 'ARROYO SECO', 'CADEREYTA DE MONTES', 'COL[OÓ]N', 'CORREGIDORA', 'EZEQUIEL MONTES', 'HUIMILPAN', 'JALPAN DE SERRA', 'LANDA DE MATAMOROS', 'EL MARQU[EÉ]S', 'PEDRO ESCOBEDO', 'PEÑAMILLER', 'CIUDAD DE QUER[EÉ]TARO', 'SAN JOAQU[IÍ]N', 'SAN JUAN DEL R[IÍ]O', 'TEQUISQUIAPAN', 'TOLIM[AÁ]N', 'QUER[EÉT]']
            patrones_ciudades = {'MUNICIPIO DE QUEREÉT': 'CIUDAD DE QUERÉTARO', 'AMEALCO DE BONFIL': 'AMEALCO DE BONFIL', 'PINAL DE AMOLES': 'PINAL DE AMOLES', 'ARROYO SECO': 'ARROYO SECO', 'CADEREYTA DE MONTES': 'CADEREYTA DE MONTES', 'COLOÓN': 'COLÓN', 'CORREGIDORA': 'CORREGIDORA', 'EZEQUIEL MONTES': 'EZEQUIEL MONTES', 'HUIMILPAN': 'HUIMILPAN', 'JALPAN DE SERRA': 'JALPAN DE SERRA', 'LANDA DE MATAMOROS': 'LANDA DE MATAMOROS', 'EL MARQUEÉS': 'EL MARQUÉS', 'PEDRO ESCOBEDO': 'PEDRO ESCOBEDO', 'PEÑAMILLER': 'PEÑAMILLER', 'CIUDAD DE QUEREÉTARO': 'CIUDAD DE QUERÉTARO', 'SAN JOAQUIÍN': 'SAN JOAQUÍN', 'SAN JUAN DEL RIÍO': 'SAN JUAN DEL RÍO', 'TEQUISQUIAPAN': 'TEQUISQUIAPAN', 'TOLIMAÁN': 'TOLIMÁN', 'QUEREÉT': 'QUERÉTARO'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'ROO', estado_republica, re.IGNORECASE): 
            ciudades_clave = ['COZUMEL', 'FELIPE CARRILLO PUERTO', 'ISLA MUJERES', 'OTH[OÓ]N P. BLANCO', 'BENITO JU[AÁ]REZ', 'JOS[EÉ] MAR[IÍ]A MORELOS', 'L[AÁ]ZARO C[AÁ]RDENAS', 'SOLIDARIDAD', 'TULUM', 'BACALAR', 'PUERTO MORELOS', 'CARMEN']
            patrones_ciudades = {'COZUMEL': 'COZUMEL', 'FELIPE CARRILLO PUERTO': 'FELIPE CARRILLO PUERTO', 'ISLA MUJERES': 'ISLA MUJERES', 'OTHOÓN P. BLANCO': 'OTHÓN P. BLANCO', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'JOSEÉ MARIÍA MORELOS': 'JOSÉ MARÍA MORELOS', 'LAÁZARO CAÁRDENAS': 'LÁZARO CÁRDENAS', 'SOLIDARIDAD': 'SOLIDARIDAD', 'TULUM': 'TULUM', 'BACALAR': 'BACALAR', 'PUERTO MORELOS': 'PUERTO MORELOS', 'CARMEN': 'CARMEN'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'LUIS', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['MUNICIPIO DE SAN LUIS POTO', 'AHUALULCO', 'ALAQUINES', 'AQUISM[OÓ]N', 'ARMADILLO DE LOS INFANTE', 'C[AÁ]RDENAS', 'CATORCE', 'CEDRAL', 'CERRITOS', 'CERRO DE SAN PEDRO', 'CIUDAD DEL MA[IÍ]Z', 'CIUDAD FERN[AÁ]NDEZ', 'TANCANHUITZ', 'CIUDAD VALLES', 'COXCATL[AÁ]N', 'CHARCAS', 'EBANO', 'GUADALC[AÁ]ZAR', 'HUEHUETL[AÁ]N', 'LAGUNILLAS', 'MATEHUALA', 'MEXQUITIC DE CARMONA', 'MOCTEZUMA', 'RAY[OÓ]N', 'RIOVERDE', 'SALINAS', 'SAN ANTONIO', 'SAN CIRO DE ACOSTA', 'CIUDAD DE SAN LUIS POTOS', 'SAN MART[IÍ]N CHALCHICUAUTLA', 'SAN NICOL[AÁ]S TOLENTINO', 'SANTA CATARINA', 'SANTA MAR[IÍ]A DEL R[IÍ]O', 'SANTO DOMINGO', 'SAN VICENTE TANCUAYALAB', 'SOLEDAD DE GRACIANO S[AÁ]NCHEZ', 'TAMASOPO', 'TAMAZUNCHALE', 'TAMPAC[AÁ]N', 'TAMPAMOL[OÓ]N CORONA', 'TAMU[IÍ]N', 'TANLAJ[AÁ]S', 'TANQUI[AÁ]N DE ESCOBEDO', 'TIERRA NUEVA', 'VANEGAS', 'VENADO', 'VILLA DE ARRIAGA', 'VILLA DE GUADALUPE', 'VILLA DE LA PAZ', 'VILLA DE RAMOS', 'VILLA DE REYES', 'VILLA HIDALGO', 'VILLA JU[AÁ]REZ', 'AXTLA DE TERRAZAS', 'XILITLA', 'ZARAGOZA', 'VILLA DE ARISTA', 'MATLAPA', 'EL NARANJO', 'SAN LUIS POTO']
            patrones_ciudades = {'MUNICIPIO DE SAN LUIS POTO': 'CIUDAD DE SAN LUIS POTOSÍ', 'AHUALULCO': 'AHUALULCO', 'ALAQUINES': 'ALAQUINES', 'AQUISMOÓN': 'AQUISMÓN', 'ARMADILLO DE LOS INFANTE': 'ARMADILLO DE LOS INFANTE', 'CAÁRDENAS': 'CÁRDENAS', 'CATORCE': 'CATORCE', 'CEDRAL': 'CEDRAL', 'CERRITOS': 'CERRITOS', 'CERRO DE SAN PEDRO': 'CERRO DE SAN PEDRO', 'CIUDAD DEL MAIÍZ': 'CIUDAD DEL MAÍZ', 'CIUDAD FERNAÁNDEZ': 'CIUDAD FERNÁNDEZ', 'TANCANHUITZ': 'TANCANHUITZ', 'CIUDAD VALLES': 'CIUDAD VALLES', 'COXCATLAÁN': 'COXCATLÁN', 'CHARCAS': 'CHARCAS', 'EBANO': 'EBANO', 'GUADALCAÁZAR': 'GUADALCÁZAR', 'HUEHUETLAÁN': 'HUEHUETLÁN', 'LAGUNILLAS': 'LAGUNILLAS', 'MATEHUALA': 'MATEHUALA', 'MEXQUITIC DE CARMONA': 'MEXQUITIC DE CARMONA', 'MOCTEZUMA': 'MOCTEZUMA', 'RAYOÓN': 'RAYÓN', 'RIOVERDE': 'RIOVERDE', 'SALINAS': 'SALINAS', 'SAN ANTONIO': 'SAN ANTONIO', 'SAN CIRO DE ACOSTA': 'SAN CIRO DE ACOSTA', 'CIUDAD DE SAN LUIS POTOS': 'CIUDAD DE SAN LUIS POTOSÍ', 'SAN MARTIÍN CHALCHICUAUTLA': 'SAN MARTÍN CHALCHICUAUTLA', 'SAN NICOLAÁS TOLENTINO': 'SAN NICOLÁS TOLENTINO', 'SANTA CATARINA': 'SANTA CATARINA', 'SANTA MARIÍA DEL RIÍO': 'SANTA MARÍA DEL RÍO', 'SANTO DOMINGO': 'SANTO DOMINGO', 'SAN VICENTE TANCUAYALAB': 'SAN VICENTE TANCUAYALAB', 'SOLEDAD DE GRACIANO SAÁNCHEZ': 'SOLEDAD DE GRACIANO SÁNCHEZ', 'TAMASOPO': 'TAMASOPO', 'TAMAZUNCHALE': 'TAMAZUNCHALE', 'TAMPACAÁN': 'TAMPACÁN', 'TAMPAMOLOÓN CORONA': 'TAMPAMOLÓN CORONA', 'TAMUIÍN': 'TAMUÍN', 'TANLAJAÁS': 'TANLAJÁS', 'TANQUIAÁN DE ESCOBEDO': 'TANQUIÁN DE ESCOBEDO', 'TIERRA NUEVA': 'TIERRA NUEVA', 'VANEGAS': 'VANEGAS', 'VENADO': 'VENADO', 'VILLA DE ARRIAGA': 'VILLA DE ARRIAGA', 'VILLA DE GUADALUPE': 'VILLA DE GUADALUPE', 'VILLA DE LA PAZ': 'VILLA DE LA PAZ', 'VILLA DE RAMOS': 'VILLA DE RAMOS', 'VILLA DE REYES': 'VILLA DE REYES', 'VILLA HIDALGO': 'VILLA HIDALGO', 'VILLA JUAÁREZ': 'VILLA JUÁREZ', 'AXTLA DE TERRAZAS': 'AXTLA DE TERRAZAS', 'XILITLA': 'XILITLA', 'ZARAGOZA': 'ZARAGOZA', 'VILLA DE ARISTA': 'VILLA DE ARISTA', 'MATLAPA': 'MATLAPA', 'EL NARANJO': 'EL NARANJO', 'SAN LUIS POTO': 'SAN LUIS POTOSÍ'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'SINA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['AHOME', 'ANGOSTURA', 'BADIRAGUATO', 'CONCORDIA', 'COSAL[AÁ]', 'CULIAC[AÁ]N', 'CHOIX', 'ELOTA', 'ESCUINAPA', 'EL FUERTE', 'GUASAVE', 'MAZATL[AÁ]N', 'MOCORITO', 'ROSARIO', 'SALVADOR ALVARADO', 'SAN IGNACIO', 'SINALOA', 'NAVOLATO', 'ELDORADO', 'JUAN JOS[EÉ] R[IÍ]OS']
            patrones_ciudades = {'AHOME': 'AHOME', 'ANGOSTURA': 'ANGOSTURA', 'BADIRAGUATO': 'BADIRAGUATO', 'CONCORDIA': 'CONCORDIA', 'COSALAÁ': 'COSALÁ', 'CULIACAÁN': 'CULIACÁN', 'CHOIX': 'CHOIX', 'ELOTA': 'ELOTA', 'ESCUINAPA': 'ESCUINAPA', 'EL FUERTE': 'EL FUERTE', 'GUASAVE': 'GUASAVE', 'MAZATLAÁN': 'MAZATLÁN', 'MOCORITO': 'MOCORITO', 'ROSARIO': 'ROSARIO', 'SALVADOR ALVARADO': 'SALVADOR ALVARADO', 'SAN IGNACIO': 'SAN IGNACIO', 'SINALOA': 'SINALOA', 'NAVOLATO': 'NAVOLATO', 'ELDORADO': 'ELDORADO', 'JUAN JOSEÉ RIÍOS': 'JUAN JOSÉ RÍOS'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'SONO', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ACONCHI', 'AGUA PRIETA', 'ALAMOS', 'ARIVECHI', 'ARIZPE', 'ATIL', 'BACAD[EÉ]HUACHI', 'BACANORA', 'BACERAC', 'BACOACHI', 'B[AÁ]CUM', 'BAN[AÁ]MICHI', 'BAVI[AÁ]CORA', 'BAVISPE', 'BENJAM[IÍ]N HILL', 'CABORCA', 'CAJEME', 'CANANEA', 'CARB[OÓ]', 'LA COLORADA', 'CUCURPE', 'CUMPAS', 'DIVISADEROS', 'EMPALME', 'ETCHOJOA', 'FRONTERAS', 'GRANADOS', 'GUAYMAS', 'HERMOSILLO', 'HUACHINERA', 'HU[AÁ]SABAS', 'HUATABAMPO', 'HU[EÉ]PAC', 'IMURIS', 'MAGDALENA', 'MAZAT[AÁ]N', 'MOCTEZUMA', 'NACO', 'N[AÁ]CORI CHICO', 'NACOZARI DE GARC[IÍ]A', 'NAVOJOA', 'NOGALES', '[OÓ]NAVAS', 'OPODEPE', 'OQUITOA', 'PITIQUITO', 'PUERTO PEÑASCO', 'QUIRIEGO', 'RAY[OÓ]N', 'ROSARIO', 'SAHUARIPA', 'SAN FELIPE DE JES[UÚ]S', 'SAN JAVIER', 'SAN LUIS R[IÍ]O COLORADO', 'SAN MIGUEL DE HORCASITAS', 'SAN PEDRO DE LA CUEVA', 'SANTA ANA', 'SANTA CRUZ', 'S[AÁ]RIC', 'SOYOPA', 'SUAQUI GRANDE', 'TEPACHE', 'TRINCHERAS', 'TUBUTAMA', 'URES', 'VILLA HIDALGO', 'VILLA PESQUEIRA', 'Y[EÉ]CORA', 'GENERAL PLUTARCO EL[IÍ]AS CALLES', 'BENITO JU[AÁ]REZ', 'SAN IGNACIO R[IÍ]O MUERTO', 'ALTAR']
            patrones_ciudades = {'ACONCHI': 'ACONCHI', 'AGUA PRIETA': 'AGUA PRIETA', 'ALAMOS': 'ALAMOS', 'ARIVECHI': 'ARIVECHI', 'ARIZPE': 'ARIZPE', 'ATIL': 'ATIL', 'BACADEÉHUACHI': 'BACADÉHUACHI', 'BACANORA': 'BACANORA', 'BACERAC': 'BACERAC', 'BACOACHI': 'BACOACHI', 'BAÁCUM': 'BÁCUM', 'BANAÁMICHI': 'BANÁMICHI', 'BAVIAÁCORA': 'BAVIÁCORA', 'BAVISPE': 'BAVISPE', 'BENJAMIÍN HILL': 'BENJAMÍN HILL', 'CABORCA': 'CABORCA', 'CAJEME': 'CAJEME', 'CANANEA': 'CANANEA', 'CARBOÓ': 'CARBÓ', 'LA COLORADA': 'LA COLORADA', 'CUCURPE': 'CUCURPE', 'CUMPAS': 'CUMPAS', 'DIVISADEROS': 'DIVISADEROS', 'EMPALME': 'EMPALME', 'ETCHOJOA': 'ETCHOJOA', 'FRONTERAS': 'FRONTERAS', 'GRANADOS': 'GRANADOS', 'GUAYMAS': 'GUAYMAS', 'HERMOSILLO': 'HERMOSILLO', 'HUACHINERA': 'HUACHINERA', 'HUAÁSABAS': 'HUÁSABAS', 'HUATABAMPO': 'HUATABAMPO', 'HUEÉPAC': 'HUÉPAC', 'IMURIS': 'IMURIS', 'MAGDALENA': 'MAGDALENA', 'MAZATAÁN': 'MAZATÁN', 'MOCTEZUMA': 'MOCTEZUMA', 'NACO': 'NACO', 'NAÁCORI CHICO': 'NÁCORI CHICO', 'NACOZARI DE GARCIÍA': 'NACOZARI DE GARCÍA', 'NAVOJOA': 'NAVOJOA', 'NOGALES': 'NOGALES', 'OÓNAVAS': 'ÓNAVAS', 'OPODEPE': 'OPODEPE', 'OQUITOA': 'OQUITOA', 'PITIQUITO': 'PITIQUITO', 'PUERTO PEÑASCO': 'PUERTO PEÑASCO', 'QUIRIEGO': 'QUIRIEGO', 'RAYOÓN': 'RAYÓN', 'ROSARIO': 'ROSARIO', 'SAHUARIPA': 'SAHUARIPA', 'SAN FELIPE DE JESUÚS': 'SAN FELIPE DE JESÚS', 'SAN JAVIER': 'SAN JAVIER', 'SAN LUIS RIÍO COLORADO': 'SAN LUIS RÍO COLORADO', 'SAN MIGUEL DE HORCASITAS': 'SAN MIGUEL DE HORCASITAS', 'SAN PEDRO DE LA CUEVA': 'SAN PEDRO DE LA CUEVA', 'SANTA ANA': 'SANTA ANA', 'SANTA CRUZ': 'SANTA CRUZ', 'SAÁRIC': 'SÁRIC', 'SOYOPA': 'SOYOPA', 'SUAQUI GRANDE': 'SUAQUI GRANDE', 'TEPACHE': 'TEPACHE', 'TRINCHERAS': 'TRINCHERAS', 'TUBUTAMA': 'TUBUTAMA', 'URES': 'URES', 'VILLA HIDALGO': 'VILLA HIDALGO', 'VILLA PESQUEIRA': 'VILLA PESQUEIRA', 'YEÉCORA': 'YÉCORA', 'GENERAL PLUTARCO ELIÍAS CALLES': 'GENERAL PLUTARCO ELÍAS CALLES', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'SAN IGNACIO RIÍO MUERTO': 'SAN IGNACIO RÍO MUERTO', 'ALTAR': 'ALTAR'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'TABA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['BALANC[AÁ]N', 'C[AÁ]RDENAS', 'CENTLA', 'CENTRO', 'COMALCALCO', 'CUNDUAC[AÁ]N', 'EMILIANO ZAPATA', 'HUIMANGUILLO', 'JALAPA', 'JALPA DE M[EÉ]NDEZ', 'JONUTA', 'MACUSPANA', 'NACAJUCA', 'PARA[IÍ]SO', 'TACOTALPA', 'TEAPA', 'TENOSIQUE']
            patrones_ciudades = {'BALANCAÁN': 'BALANCÁN', 'CAÁRDENAS': 'CÁRDENAS', 'CENTLA': 'CENTLA', 'CENTRO': 'CENTRO', 'COMALCALCO': 'COMALCALCO', 'CUNDUACAÁN': 'CUNDUACÁN', 'EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'HUIMANGUILLO': 'HUIMANGUILLO', 'JALAPA': 'JALAPA', 'JALPA DE MEÉNDEZ': 'JALPA DE MÉNDEZ', 'JONUTA': 'JONUTA', 'MACUSPANA': 'MACUSPANA', 'NACAJUCA': 'NACAJUCA', 'PARAIÍSO': 'PARAÍSO', 'TACOTALPA': 'TACOTALPA', 'TEAPA': 'TEAPA', 'TENOSIQUE': 'TENOSIQUE'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'TAMA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ABASOLO', 'ALDAMA', 'ALTAMIRA', 'ANTIGUO MORELOS', 'BURGOS', 'BUSTAMANTE', 'CAMARGO', 'CASAS', 'CIUDAD MADERO', 'CRUILLAS', 'G[OÓ]MEZ FAR[IÍ]AS', 'GONZ[AÁ]LEZ', 'GÜ[EÉ]MEZ', 'GUERRERO', 'GUSTAVO D[IÍ]AZ ORDAZ', 'HIDALGO', 'JAUMAVE', 'JIM[EÉ]NEZ', 'LLERA', 'MAINERO', 'EL MANTE', 'MATAMOROS', 'M[EÉ]NDEZ', 'MIER', 'MIGUEL ALEM[AÁ]N', 'MIQUIHUANA', 'NUEVO LAREDO', 'NUEVO MORELOS', 'OCAMPO', 'PADILLA', 'PALMILLAS', 'REYNOSA', 'R[IÍ]O BRAVO', 'SAN CARLOS', 'SAN FERNANDO', 'SAN NICOL[AÁ]S', 'SOTO LA MARINA', 'TAMPICO', 'TULA', 'VALLE HERMOSO', 'VICTORIA', 'VILLAGR[AÁ]N', 'XICOT[EÉ]NCATL']
            patrones_ciudades = {'ABASOLO': 'ABASOLO', 'ALDAMA': 'ALDAMA', 'ALTAMIRA': 'ALTAMIRA', 'ANTIGUO MORELOS': 'ANTIGUO MORELOS', 'BURGOS': 'BURGOS', 'BUSTAMANTE': 'BUSTAMANTE', 'CAMARGO': 'CAMARGO', 'CASAS': 'CASAS', 'CIUDAD MADERO': 'CIUDAD MADERO', 'CRUILLAS': 'CRUILLAS', 'GOÓMEZ FARIÍAS': 'GÓMEZ FARÍAS', 'GONZAÁLEZ': 'GONZÁLEZ', 'GÜEÉMEZ': 'GÜÉMEZ', 'GUERRERO': 'GUERRERO', 'GUSTAVO DIÍAZ ORDAZ': 'GUSTAVO DÍAZ ORDAZ', 'HIDALGO': 'HIDALGO', 'JAUMAVE': 'JAUMAVE', 'JIMEÉNEZ': 'JIMÉNEZ', 'LLERA': 'LLERA', 'MAINERO': 'MAINERO', 'EL MANTE': 'EL MANTE', 'MATAMOROS': 'MATAMOROS', 'MEÉNDEZ': 'MÉNDEZ', 'MIER': 'MIER', 'MIGUEL ALEMAÁN': 'MIGUEL ALEMÁN', 'MIQUIHUANA': 'MIQUIHUANA', 'NUEVO LAREDO': 'NUEVO LAREDO', 'NUEVO MORELOS': 'NUEVO MORELOS', 'OCAMPO': 'OCAMPO', 'PADILLA': 'PADILLA', 'PALMILLAS': 'PALMILLAS', 'REYNOSA': 'REYNOSA', 'RIÍO BRAVO': 'RÍO BRAVO', 'SAN CARLOS': 'SAN CARLOS', 'SAN FERNANDO': 'SAN FERNANDO', 'SAN NICOLAÁS': 'SAN NICOLÁS', 'SOTO LA MARINA': 'SOTO LA MARINA', 'TAMPICO': 'TAMPICO', 'TULA': 'TULA', 'VALLE HERMOSO': 'VALLE HERMOSO', 'VICTORIA': 'VICTORIA', 'VILLAGRAÁN': 'VILLAGRÁN', 'XICOTEÉNCATL': 'XICOTÉNCATL'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'TLA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['AMAXAC DE GUERRERO', 'APETATITL[AÁ]N DE ANTONIO CARVAJAL', 'ATLANGATEPEC', 'ATLTZAYANCA', 'APIZACO', 'CALPULALPAN', 'EL CARMEN TEQUEXQUITLA', 'CUAPIAXTLA', 'CUAXOMULCO', 'CHIAUTEMPAN', 'MUÑOZ DE DOMINGO ARENAS', 'ESPAÑITA', 'HUAMANTLA', 'HUEYOTLIPAN', 'IXTACUIXTLA DE MARIANO MATAMOROS', 'IXTENCO', 'MAZATECOCHCO DE JOS[EÉ] MAR[IÍ]A MORELOS', 'CONTLA DE JUAN CUAMATZI', 'TEPETITLA DE LARDIZ[AÁ]BAL', 'SANCT[OÓ]RUM DE L[AÁ]ZARO C[AÁ]RDENAS', 'NANACAMILPA DE MARIANO ARISTA', 'ACUAMANALA DE MIGUEL HIDALGO', 'NAT[IÍ]VITAS', 'PANOTLA', 'SAN PABLO DEL MONTE', 'SANTA CRUZ TLAXCALA', 'TENANCINGO', 'TEOLOCHOLCO', 'TEPEYANCO', 'TERRENATE', 'TETLA DE LA SOLIDARIDAD', 'TETLATLAHUCA', 'CIUDAD DE TLAXCALA', 'TLAXCO', 'TOCATL[AÁ]N', 'TOTOLAC', 'ZILTLALT[EÉ]PEC DE TRINIDAD S[AÁ]NCHEZ SANTOS', 'TZOMPANTEPEC', 'XALOZTOC', 'XALTOCAN', 'PAPALOTLA DE XICOHT[EÉ]NCATL', 'XICOHTZINCO', 'YAUHQUEMEHCAN', 'ZACATELCO', 'BENITO JU[AÁ]REZ', 'EMILIANO ZAPATA', 'L[AÁ]ZARO C[AÁ]RDENAS', 'LA MAGDALENA TLALTELULCO', 'SAN DAMI[AÁ]N TEX[OÓ]LOC', 'SAN FRANCISCO TETLANOHCAN', 'SAN JER[OÓ]NIMO ZACUALPAN', 'SAN JOS[EÉ] TEACALCO', 'SAN JUAN HUACTZINCO', 'SAN LORENZO AXOCOMANITLA', 'SAN LUCAS TECOPILCO', 'SANTA ANA NOPALUCAN', 'SANTA APOLONIA TEACALCO', 'SANTA CATARINA AYOMETLA', 'SANTA CRUZ QUILEHTLA', 'SANTA ISABEL XILOXOXTLA']
            patrones_ciudades = {'AMAXAC DE GUERRERO': 'AMAXAC DE GUERRERO', 'APETATITLAÁN DE ANTONIO CARVAJAL': 'APETATITLÁN DE ANTONIO CARVAJAL', 'ATLANGATEPEC': 'ATLANGATEPEC', 'ATLTZAYANCA': 'ATLTZAYANCA', 'APIZACO': 'APIZACO', 'CALPULALPAN': 'CALPULALPAN', 'EL CARMEN TEQUEXQUITLA': 'EL CARMEN TEQUEXQUITLA', 'CUAPIAXTLA': 'CUAPIAXTLA', 'CUAXOMULCO': 'CUAXOMULCO', 'CHIAUTEMPAN': 'CHIAUTEMPAN', 'MUÑOZ DE DOMINGO ARENAS': 'MUÑOZ DE DOMINGO ARENAS', 'ESPAÑITA': 'ESPAÑITA', 'HUAMANTLA': 'HUAMANTLA', 'HUEYOTLIPAN': 'HUEYOTLIPAN', 'IXTACUIXTLA DE MARIANO MATAMOROS': 'IXTACUIXTLA DE MARIANO MATAMOROS', 'IXTENCO': 'IXTENCO', 'MAZATECOCHCO DE JOSEÉ MARIÍA MORELOS': 'MAZATECOCHCO DE JOSÉ MARÍA MORELOS', 'CONTLA DE JUAN CUAMATZI': 'CONTLA DE JUAN CUAMATZI', 'TEPETITLA DE LARDIZAÁBAL': 'TEPETITLA DE LARDIZÁBAL', 'SANCTOÓRUM DE LAÁZARO CAÁRDENAS': 'SANCTÓRUM DE LÁZARO CÁRDENAS', 'NANACAMILPA DE MARIANO ARISTA': 'NANACAMILPA DE MARIANO ARISTA', 'ACUAMANALA DE MIGUEL HIDALGO': 'ACUAMANALA DE MIGUEL HIDALGO', 'NATIÍVITAS': 'NATÍVITAS', 'PANOTLA': 'PANOTLA', 'SAN PABLO DEL MONTE': 'SAN PABLO DEL MONTE', 'SANTA CRUZ TLAXCALA': 'SANTA CRUZ TLAXCALA', 'TENANCINGO': 'TENANCINGO', 'TEOLOCHOLCO': 'TEOLOCHOLCO', 'TEPEYANCO': 'TEPEYANCO', 'TERRENATE': 'TERRENATE', 'TETLA DE LA SOLIDARIDAD': 'TETLA DE LA SOLIDARIDAD', 'TETLATLAHUCA': 'TETLATLAHUCA', 'CIUDAD DE TLAXCALA': 'CIUDAD DE TLAXCALA', 'TLAXCO': 'TLAXCO', 'TOCATLAÁN': 'TOCATLÁN', 'TOTOLAC': 'TOTOLAC', 'ZILTLALTEÉPEC DE TRINIDAD SAÁNCHEZ SANTOS': 'ZILTLALTÉPEC DE TRINIDAD SÁNCHEZ SANTOS', 'TZOMPANTEPEC': 'TZOMPANTEPEC', 'XALOZTOC': 'XALOZTOC', 'XALTOCAN': 'XALTOCAN', 'PAPALOTLA DE XICOHTEÉNCATL': 'PAPALOTLA DE XICOHTÉNCATL', 'XICOHTZINCO': 'XICOHTZINCO', 'YAUHQUEMEHCAN': 'YAUHQUEMEHCAN', 'ZACATELCO': 'ZACATELCO', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'LAÁZARO CAÁRDENAS': 'LÁZARO CÁRDENAS', 'LA MAGDALENA TLALTELULCO': 'LA MAGDALENA TLALTELULCO', 'SAN DAMIAÁN TEXOÓLOC': 'SAN DAMIÁN TEXÓLOC', 'SAN FRANCISCO TETLANOHCAN': 'SAN FRANCISCO TETLANOHCAN', 'SAN JEROÓNIMO ZACUALPAN': 'SAN JERÓNIMO ZACUALPAN', 'SAN JOSEÉ TEACALCO': 'SAN JOSÉ TEACALCO', 'SAN JUAN HUACTZINCO': 'SAN JUAN HUACTZINCO', 'SAN LORENZO AXOCOMANITLA': 'SAN LORENZO AXOCOMANITLA', 'SAN LUCAS TECOPILCO': 'SAN LUCAS TECOPILCO', 'SANTA ANA NOPALUCAN': 'SANTA ANA NOPALUCAN', 'SANTA APOLONIA TEACALCO': 'SANTA APOLONIA TEACALCO', 'SANTA CATARINA AYOMETLA': 'SANTA CATARINA AYOMETLA', 'SANTA CRUZ QUILEHTLA': 'SANTA CRUZ QUILEHTLA', 'SANTA ISABEL XILOXOXTLA': 'SANTA ISABEL XILOXOXTLA'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'VERA', estado_republica, re.IGNORECASE):  
            ciudades_clave = [ 'MUNICIPIO DE VERACRUZ','ACAJETE', 'ACATL[AÁ]N', 'ACAYUCAN', 'ACTOPAN', 'ACULA', 'ACULTZINGO', 'CAMAR[OÓ]N DE TEJEDA', 'ALPATL[AÁ]HUAC', 'ALTO LUCERO DE GUTI[EÉ]RREZ BARRIOS', 'ALTOTONGA', 'ALVARADO', 'AMATITL[AÁ]N', 'NARANJOS AMATL[AÁ]N', 'AMATL[AÁ]N DE LOS REYES', 'ANGEL R. CABADA', 'LA ANTIGUA', 'APAZAPAN', 'AQUILA', 'ASTACINGA', 'ATLAHUILCO', 'ATOYAC', 'ATZACAN', 'ATZALAN', 'TLALTETELA', 'AYAHUALULCO', 'BANDERILLA', 'BENITO JU[AÁ]REZ', 'BOCA DEL R[IÍ]O', 'CALCAHUALCO', 'CAMERINO Z. MENDOZA', 'CARRILLO PUERTO', 'CATEMACO', 'CAZONES DE HERRERA', 'CERRO AZUL', 'CITLALT[EÉ]PETL', 'COACOATZINTLA', 'COAHUITL[AÁ]N', 'COATEPEC', 'COATZACOALCOS', 'COATZINTLA', 'COETZALA', 'COLIPA', 'COMAPA', 'C[OÓ]RDOBA', 'COSAMALOAPAN DE CARPIO', 'COSAUTL[AÁ]N DE CARVAJAL', 'COSCOMATEPEC', 'COSOLEACAQUE', 'COTAXTLA', 'COXQUIHUI', 'COYUTLA', 'CUICHAPA', 'CUITL[AÁ]HUAC', 'CHACALTIANGUIS', 'CHALMA', 'CHICONAMEL', 'CHICONQUIACO', 'CHICONTEPEC', 'CHINAMECA', 'CHINAMPA DE GOROSTIZA', 'LAS CHOAPAS', 'CHOCAM[AÁ]N', 'CHONTLA', 'CHUMATL[AÁ]N', 'CIUDAD DE EMILIANO ZAPATA', 'MUNICIPIO DE EMILIANO ZAPATA', 'ESPINAL', 'FILOMENO MATA', 'FORT[IÍ]N', 'GUTI[EÉ]RREZ ZAMORA', 'HIDALGOTITL[AÁ]N', 'HUATUSCO', 'HUAYACOCOTLA', 'HUEYAPAN DE OCAMPO', 'HUILOAPAN DE CUAUHT[EÉ]MOC', 'CIUDAD DE IGNACIO', 'MUNICIPIO DE IGNACIO', 'ILAMATL[AÁ]N', 'ISLA', 'IXCATEPEC', 'IXHUAC[AÁ]N DE LOS REYES', 'IXHUATL[AÁ]N DEL CAF[EÉ]', 'IXHUATLANCILLO', 'IXHUATL[AÁ]N DEL SURESTE', 'IXHUATL[AÁ]N DE MADERO', 'IXMATLAHUACAN', 'IXTACZOQUITL[AÁ]N', 'JALACINGO', 'XALAPA', 'JALCOMULCO', 'J[AÁ]LTIPAN', 'JAMAPA', 'JES[UÚ]S CARRANZA', 'XICO', 'JILOTEPEC', 'JUAN RODR[IÍ]GUEZ CLARA', 'JUCHIQUE DE FERRER', 'LANDERO Y COSS', 'LERDO DE TEJADA', 'MAGDALENA', 'MALTRATA', 'MANLIO FABIO ALTAMIRANO', 'MARIANO ESCOBEDO', 'MART[IÍ]NEZ DE LA TORRE', 'MECATL[AÁ]N', 'MECAYAPAN', 'MEDELL[IÍ]N DE BRAVO', 'MIAHUATL[AÁ]N', 'LAS MINAS', 'MINATITL[AÁ]N', 'MISANTLA', 'MIXTLA DE ALTAMIRANO', 'MOLOAC[AÁ]N', 'NAOLINCO', 'NARANJAL', 'NAUTLA', 'NOGALES', 'OLUTA', 'OMEALCA', 'ORIZABA', 'OTATITL[AÁ]N', 'OTEAPAN', 'OZULUAMA DE MASCAREÑAS', 'PAJAPAN', 'P[AÁ]NUCO', 'PAPANTLA', 'PASO DEL MACHO', 'PASO DE OVEJAS', 'LA PERLA', 'PEROTE', 'PLAT[OÓ]N S[AÁ]NCHEZ', 'PLAYA VICENTE', 'POZA RICA DE HIDALGO', 'LAS VIGAS DE RAM[IÍ]REZ', 'PUEBLO VIEJO', 'PUENTE NACIONAL', 'RAFAEL DELGADO', 'RAFAEL LUCIO', 'LOS REYES', 'R[IÍ]O BLANCO', 'SALTABARRANCA', 'SAN ANDR[EÉ]S TENEJAPAN', 'SAN ANDR[EÉ]S TUXTLA', 'SAN JUAN EVANGELISTA', 'SANTIAGO TUXTLA', 'SAYULA DE ALEM[AÁ]N', 'SOCONUSCO', 'SOCHIAPA', 'SOLEDAD ATZOMPA', 'SOLEDAD DE DOBLADO', 'SOTEAPAN', 'TAMAL[IÍ]N', 'TAMIAHUA', 'TAMPICO ALTO', 'TANCOCO', 'TANTIMA', 'TANTOYUCA', 'TATATILA', 'CASTILLO DE TEAYO', 'TECOLUTLA', 'TEHUIPANGO', '[AÁ]LAMO TEMAPACHE', 'TEMPOAL', 'TENAMPA', 'TENOCHTITL[AÁ]N', 'TEOCELO', 'TEPATLAXCO', 'TEPETL[AÁ]N', 'TEPETZINTLA', 'TEQUILA', 'JOS[EÉ] AZUETA', 'TEXCATEPEC', 'TEXHUAC[AÁ]N', 'TEXISTEPEC', 'TEZONAPA', 'TIERRA BLANCA', 'TIHUATL[AÁ]N', 'TLACOJALPAN', 'TLACOLULAN', 'TLACOTALPAN', 'TLACOTEPEC DE MEJ[IÍ]A', 'TLACHICHILCO', 'TLALIXCOYAN', 'TLALNELHUAYOCAN', 'TLAPACOYAN', 'TLAQUILPA', 'TLILAPAN', 'TOMATL[AÁ]N', 'TONAY[AÁ]N', 'TOTUTLA', 'TUXPAN', 'TUXTILLA', 'URSULO GALV[AÁ]N', 'VEGA DE ALATORRE', 'CIUDAD DE VERACRUZ', 'VILLA ALDAMA', 'XOXOCOTLA', 'YANGA', 'YECUATLA', 'ZACUALPAN', 'ZARAGOZA', 'ZENTLA', 'ZONGOLICA', 'ZONTECOMATL[AÁ]N DE L[OÓ]PEZ Y FUENTES', 'ZOZOCOLCO DE HIDALGO', 'AGUA DULCE', 'EL HIGO', 'NANCHITAL DE L[AÁ]ZARO C[AÁ]RDENAS DEL R[IÍ]O', 'TRES VALLES', 'CARLOS A. CARRILLO', 'TATAHUICAPAN DE JU[AÁ]REZ', 'UXPANAPA', 'SAN RAFAEL', 'SANTIAGO SOCHIAPAN', 'VERACRUZ']
            patrones_ciudades = { 'MUNICIPIO DE VERACRUZ': 'CIUDAD DE VERACRUZ', 'ACAJETE': 'ACAJETE', 'ACATLAÁN': 'ACATLÁN', 'ACAYUCAN': 'ACAYUCAN', 'ACTOPAN': 'ACTOPAN', 'ACULA': 'ACULA', 'ACULTZINGO': 'ACULTZINGO', 'CAMAROÓN DE TEJEDA': 'CAMARÓN DE TEJEDA', 'ALPATLAÁHUAC': 'ALPATLÁHUAC', 'ALTO LUCERO DE GUTIEÉRREZ BARRIOS': 'ALTO LUCERO DE GUTIÉRREZ BARRIOS', 'ALTOTONGA': 'ALTOTONGA', 'ALVARADO': 'ALVARADO', 'AMATITLAÁN': 'AMATITLÁN', 'NARANJOS AMATLAÁN': 'NARANJOS AMATLÁN', 'AMATLAÁN DE LOS REYES': 'AMATLÁN DE LOS REYES', 'ANGEL R. CABADA': 'ANGEL R. CABADA', 'LA ANTIGUA': 'LA ANTIGUA', 'APAZAPAN': 'APAZAPAN', 'AQUILA': 'AQUILA', 'ASTACINGA': 'ASTACINGA', 'ATLAHUILCO': 'ATLAHUILCO', 'ATOYAC': 'ATOYAC', 'ATZACAN': 'ATZACAN', 'ATZALAN': 'ATZALAN', 'TLALTETELA': 'TLALTETELA', 'AYAHUALULCO': 'AYAHUALULCO', 'BANDERILLA': 'BANDERILLA', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'BOCA DEL RIÍO': 'BOCA DEL RÍO', 'CALCAHUALCO': 'CALCAHUALCO', 'CAMERINO Z. MENDOZA': 'CAMERINO Z. MENDOZA', 'CARRILLO PUERTO': 'CARRILLO PUERTO', 'CATEMACO': 'CATEMACO', 'CAZONES DE HERRERA': 'CAZONES DE HERRERA', 'CERRO AZUL': 'CERRO AZUL', 'CITLALTEÉPETL': 'CITLALTÉPETL', 'COACOATZINTLA': 'COACOATZINTLA', 'COAHUITLAÁN': 'COAHUITLÁN', 'COATEPEC': 'COATEPEC', 'COATZACOALCOS': 'COATZACOALCOS', 'COATZINTLA': 'COATZINTLA', 'COETZALA': 'COETZALA', 'COLIPA': 'COLIPA', 'COMAPA': 'COMAPA', 'COÓRDOBA': 'CÓRDOBA', 'COSAMALOAPAN DE CARPIO': 'COSAMALOAPAN DE CARPIO', 'COSAUTLAÁN DE CARVAJAL': 'COSAUTLÁN DE CARVAJAL', 'COSCOMATEPEC': 'COSCOMATEPEC', 'COSOLEACAQUE': 'COSOLEACAQUE', 'COTAXTLA': 'COTAXTLA', 'COXQUIHUI': 'COXQUIHUI', 'COYUTLA': 'COYUTLA', 'CUICHAPA': 'CUICHAPA', 'CUITLAÁHUAC': 'CUITLÁHUAC', 'CHACALTIANGUIS': 'CHACALTIANGUIS', 'CHALMA': 'CHALMA', 'CHICONAMEL': 'CHICONAMEL', 'CHICONQUIACO': 'CHICONQUIACO', 'CHICONTEPEC': 'CHICONTEPEC', 'CHINAMECA': 'CHINAMECA', 'CHINAMPA DE GOROSTIZA': 'CHINAMPA DE GOROSTIZA', 'LAS CHOAPAS': 'LAS CHOAPAS', 'CHOCAMAÁN': 'CHOCAMÁN', 'CHONTLA': 'CHONTLA', 'CHUMATLAÁN': 'CHUMATLÁN', 'CIUDAD DE EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'MUNICIPIO DE EMILIANO ZAPATA': 'EMILIANO ZAPATA', 'ESPINAL': 'ESPINAL', 'FILOMENO MATA': 'FILOMENO MATA', 'FORTIÍN': 'FORTÍN', 'GUTIEÉRREZ ZAMORA': 'GUTIÉRREZ ZAMORA', 'HIDALGOTITLAÁN': 'HIDALGOTITLÁN', 'HUATUSCO': 'HUATUSCO', 'HUAYACOCOTLA': 'HUAYACOCOTLA', 'HUEYAPAN DE OCAMPO': 'HUEYAPAN DE OCAMPO', 'HUILOAPAN DE CUAUHTEÉMOC': 'HUILOAPAN DE CUAUHTÉMOC', 'CIUDAD DE IGNACIO': 'IGNACIO DE LA LLAVE', 'MUNICIPIO DE IGNACIO': 'IGNACIO DE LA LLAVE', 'ILAMATLAÁN': 'ILAMATLÁN', 'ISLA': 'ISLA', 'IXCATEPEC': 'IXCATEPEC', 'IXHUACAÁN DE LOS REYES': 'IXHUACÁN DE LOS REYES', 'IXHUATLAÁN DEL CAFEÉ': 'IXHUATLÁN DEL CAFÉ', 'IXHUATLANCILLO': 'IXHUATLANCILLO', 'IXHUATLAÁN DEL SURESTE': 'IXHUATLÁN DEL SURESTE', 'IXHUATLAÁN DE MADERO': 'IXHUATLÁN DE MADERO', 'IXMATLAHUACAN': 'IXMATLAHUACAN', 'IXTACZOQUITLAÁN': 'IXTACZOQUITLÁN', 'JALACINGO': 'JALACINGO', 'XALAPA': 'XALAPA', 'JALCOMULCO': 'JALCOMULCO', 'JAÁLTIPAN': 'JÁLTIPAN', 'JAMAPA': 'JAMAPA', 'JESUÚS CARRANZA': 'JESÚS CARRANZA', 'XICO': 'XICO', 'JILOTEPEC': 'JILOTEPEC', 'JUAN RODRIÍGUEZ CLARA': 'JUAN RODRÍGUEZ CLARA', 'JUCHIQUE DE FERRER': 'JUCHIQUE DE FERRER', 'LANDERO Y COSS': 'LANDERO Y COSS', 'LERDO DE TEJADA': 'LERDO DE TEJADA', 'MAGDALENA': 'MAGDALENA', 'MALTRATA': 'MALTRATA', 'MANLIO FABIO ALTAMIRANO': 'MANLIO FABIO ALTAMIRANO', 'MARIANO ESCOBEDO': 'MARIANO ESCOBEDO', 'MARTIÍNEZ DE LA TORRE': 'MARTÍNEZ DE LA TORRE', 'MECATLAÁN': 'MECATLÁN', 'MECAYAPAN': 'MECAYAPAN', 'MEDELLIÍN DE BRAVO': 'MEDELLÍN DE BRAVO', 'MIAHUATLAÁN': 'MIAHUATLÁN', 'LAS MINAS': 'LAS MINAS', 'MINATITLAÁN': 'MINATITLÁN', 'MISANTLA': 'MISANTLA', 'MIXTLA DE ALTAMIRANO': 'MIXTLA DE ALTAMIRANO', 'MOLOACAÁN': 'MOLOACÁN', 'NAOLINCO': 'NAOLINCO', 'NARANJAL': 'NARANJAL', 'NAUTLA': 'NAUTLA', 'NOGALES': 'NOGALES', 'OLUTA': 'OLUTA', 'OMEALCA': 'OMEALCA', 'ORIZABA': 'ORIZABA', 'OTATITLAÁN': 'OTATITLÁN', 'OTEAPAN': 'OTEAPAN', 'OZULUAMA DE MASCAREÑAS': 'OZULUAMA DE MASCAREÑAS', 'PAJAPAN': 'PAJAPAN', 'PAÁNUCO': 'PÁNUCO', 'PAPANTLA': 'PAPANTLA', 'PASO DEL MACHO': 'PASO DEL MACHO', 'PASO DE OVEJAS': 'PASO DE OVEJAS', 'LA PERLA': 'LA PERLA', 'PEROTE': 'PEROTE', 'PLATOÓN SAÁNCHEZ': 'PLATÓN SÁNCHEZ', 'PLAYA VICENTE': 'PLAYA VICENTE', 'POZA RICA DE HIDALGO': 'POZA RICA DE HIDALGO', 'LAS VIGAS DE RAMIÍREZ': 'LAS VIGAS DE RAMÍREZ', 'PUEBLO VIEJO': 'PUEBLO VIEJO', 'PUENTE NACIONAL': 'PUENTE NACIONAL', 'RAFAEL DELGADO': 'RAFAEL DELGADO', 'RAFAEL LUCIO': 'RAFAEL LUCIO', 'LOS REYES': 'LOS REYES', 'RIÍO BLANCO': 'RÍO BLANCO', 'SALTABARRANCA': 'SALTABARRANCA', 'SAN ANDREÉS TENEJAPAN': 'SAN ANDRÉS TENEJAPAN', 'SAN ANDREÉS TUXTLA': 'SAN ANDRÉS TUXTLA', 'SAN JUAN EVANGELISTA': 'SAN JUAN EVANGELISTA', 'SANTIAGO TUXTLA': 'SANTIAGO TUXTLA', 'SAYULA DE ALEMAÁN': 'SAYULA DE ALEMÁN', 'SOCONUSCO': 'SOCONUSCO', 'SOCHIAPA': 'SOCHIAPA', 'SOLEDAD ATZOMPA': 'SOLEDAD ATZOMPA', 'SOLEDAD DE DOBLADO': 'SOLEDAD DE DOBLADO', 'SOTEAPAN': 'SOTEAPAN', 'TAMALIÍN': 'TAMALÍN', 'TAMIAHUA': 'TAMIAHUA', 'TAMPICO ALTO': 'TAMPICO ALTO', 'TANCOCO': 'TANCOCO', 'TANTIMA': 'TANTIMA', 'TANTOYUCA': 'TANTOYUCA', 'TATATILA': 'TATATILA', 'CASTILLO DE TEAYO': 'CASTILLO DE TEAYO', 'TECOLUTLA': 'TECOLUTLA', 'TEHUIPANGO': 'TEHUIPANGO', 'AÁLAMO TEMAPACHE': 'ÁLAMO TEMAPACHE', 'TEMPOAL': 'TEMPOAL', 'TENAMPA': 'TENAMPA', 'TENOCHTITLAÁN': 'TENOCHTITLÁN', 'TEOCELO': 'TEOCELO', 'TEPATLAXCO': 'TEPATLAXCO', 'TEPETLAÁN': 'TEPETLÁN', 'TEPETZINTLA': 'TEPETZINTLA', 'TEQUILA': 'TEQUILA', 'JOSEÉ AZUETA': 'JOSÉ AZUETA', 'TEXCATEPEC': 'TEXCATEPEC', 'TEXHUACAÁN': 'TEXHUACÁN', 'TEXISTEPEC': 'TEXISTEPEC', 'TEZONAPA': 'TEZONAPA', 'TIERRA BLANCA': 'TIERRA BLANCA', 'TIHUATLAÁN': 'TIHUATLÁN', 'TLACOJALPAN': 'TLACOJALPAN', 'TLACOLULAN': 'TLACOLULAN', 'TLACOTALPAN': 'TLACOTALPAN', 'TLACOTEPEC DE MEJIÍA': 'TLACOTEPEC DE MEJÍA', 'TLACHICHILCO': 'TLACHICHILCO', 'TLALIXCOYAN': 'TLALIXCOYAN', 'TLALNELHUAYOCAN': 'TLALNELHUAYOCAN', 'TLAPACOYAN': 'TLAPACOYAN', 'TLAQUILPA': 'TLAQUILPA', 'TLILAPAN': 'TLILAPAN', 'TOMATLAÁN': 'TOMATLÁN', 'TONAYAÁN': 'TONAYÁN', 'TOTUTLA': 'TOTUTLA', 'TUXPAN': 'TUXPAN', 'TUXTILLA': 'TUXTILLA', 'URSULO GALVAÁN': 'URSULO GALVÁN', 'VEGA DE ALATORRE': 'VEGA DE ALATORRE', 'CIUDAD DE VERACRUZ': 'CIUDAD DE VERACRUZ', 'VILLA ALDAMA': 'VILLA ALDAMA', 'XOXOCOTLA': 'XOXOCOTLA', 'YANGA': 'YANGA', 'YECUATLA': 'YECUATLA', 'ZACUALPAN': 'ZACUALPAN', 'ZARAGOZA': 'ZARAGOZA', 'ZENTLA': 'ZENTLA', 'ZONGOLICA': 'ZONGOLICA', 'ZONTECOMATLAÁN DE LOÓPEZ Y FUENTES': 'ZONTECOMATLÁN DE LÓPEZ Y FUENTES', 'ZOZOCOLCO DE HIDALGO': 'ZOZOCOLCO DE HIDALGO', 'AGUA DULCE': 'AGUA DULCE', 'EL HIGO': 'EL HIGO', 'NANCHITAL DE LAÁZARO CAÁRDENAS DEL RIÍO': 'NANCHITAL DE LÁZARO CÁRDENAS DEL RÍO', 'TRES VALLES': 'TRES VALLES', 'CARLOS A. CARRILLO': 'CARLOS A. CARRILLO', 'TATAHUICAPAN DE JUAÁREZ': 'TATAHUICAPAN DE JUÁREZ', 'UXPANAPA': 'UXPANAPA', 'SAN RAFAEL': 'SAN RAFAEL', 'SANTIAGO SOCHIAPAN': 'SANTIAGO SOCHIAPAN', 'VERACRUZ': 'VERACRUZ'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'YUCA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['ABAL[AÁ]', 'ACANCEH', 'AKIL', 'BACA', 'BOKOB[AÁ]', 'BUCTZOTZ', 'CACALCH[EÉ]N', 'CALOTMUL', 'CANSAHCAB', 'CANTAMAYEC', 'CELEST[UÚ]N', 'CENOTILLO', 'CONKAL', 'CUNCUNUL', 'CUZAM[AÁ]', 'CHACSINK[IÍ]N', 'CHANKOM', 'CHAPAB', 'CHEMAX', 'CHICXULUB PUEBLO', 'CHICHIMIL[AÁ]', 'CHIKINDZONOT', 'CHOCHOL[AÁ]', 'CHUMAYEL', 'DZ[AÁ]N', 'DZEMUL', 'DZIDZANT[UÚ]N', 'DZILAM DE BRAVO', 'DZILAM GONZ[AÁ]LEZ', 'DZIT[AÁ]S', 'DZONCAUICH', 'ESPITA', 'HALACH[OÓ]', 'HOCAB[AÁ]', 'HOCT[UÚ]N', 'HOM[UÚ]N', 'HUH[IÍ]', 'HUNUCM[AÁ]', 'IXIL', 'IZAMAL', 'KANAS[IÍ]N', 'KANTUNIL', 'KAUA', 'KINCHIL', 'KOPOM[AÁ]', 'MAMA', 'MAN[IÍ]', 'MAXCAN[UÚ]', 'MAYAP[AÁ]N', 'M[EÉ]RIDA', 'MOCOCH[AÁ]', 'MOTUL', 'MUNA', 'MUXUPIP', 'OPICH[EÉ]N', 'OXKUTZCAB', 'PANAB[AÁ]', 'PETO', 'PROGRESO', 'QUINTANA ROO', 'R[IÍ]O LAGARTOS', 'SACALUM', 'SAMAHIL', 'SANAHCAT', 'SAN FELIPE', 'SANTA ELENA', 'SEY[EÉ]', 'SINANCH[EÉ]', 'SOTUTA', 'SUCIL[AÁ]', 'SUDZAL', 'SUMA', 'TAHDZI[UÚ]', 'TAHMEK', 'TEABO', 'TECOH', 'TEKAL DE VENEGAS', 'TEKANT[OÓ]', 'TEKAX', 'TEKIT', 'TEKOM', 'TELCHAC PUEBLO', 'TELCHAC PUERTO', 'TEMAX', 'TEMOZ[OÓ]N', 'TEPAK[AÁ]N', 'TETIZ', 'TEYA', 'TICUL', 'TIMUCUY', 'TINUM', 'TIXCACALCUPUL', 'TIXKOKOB', 'TIXMEHUAC', 'TIXP[EÉ]HUAL', 'TIZIM[IÍ]N', 'TUNK[AÁ]S', 'TZUCACAB', 'UAYMA', 'UC[UÚ]', 'UM[AÁ]N', 'VALLADOLID', 'XOCCHEL', 'YAXCAB[AÁ]', 'YAXKUKUL', 'YOBA[IÍ]N']
            patrones_ciudades = {'ABALAÁ': 'ABALÁ', 'ACANCEH': 'ACANCEH', 'AKIL': 'AKIL', 'BACA': 'BACA', 'BOKOBAÁ': 'BOKOBÁ', 'BUCTZOTZ': 'BUCTZOTZ', 'CACALCHEÉN': 'CACALCHÉN', 'CALOTMUL': 'CALOTMUL', 'CANSAHCAB': 'CANSAHCAB', 'CANTAMAYEC': 'CANTAMAYEC', 'CELESTUÚN': 'CELESTÚN', 'CENOTILLO': 'CENOTILLO', 'CONKAL': 'CONKAL', 'CUNCUNUL': 'CUNCUNUL', 'CUZAMAÁ': 'CUZAMÁ', 'CHACSINKIÍN': 'CHACSINKÍN', 'CHANKOM': 'CHANKOM', 'CHAPAB': 'CHAPAB', 'CHEMAX': 'CHEMAX', 'CHICXULUB PUEBLO': 'CHICXULUB PUEBLO', 'CHICHIMILAÁ': 'CHICHIMILÁ', 'CHIKINDZONOT': 'CHIKINDZONOT', 'CHOCHOLAÁ': 'CHOCHOLÁ', 'CHUMAYEL': 'CHUMAYEL', 'DZAÁN': 'DZÁN', 'DZEMUL': 'DZEMUL', 'DZIDZANTUÚN': 'DZIDZANTÚN', 'DZILAM DE BRAVO': 'DZILAM DE BRAVO', 'DZILAM GONZAÁLEZ': 'DZILAM GONZÁLEZ', 'DZITAÁS': 'DZITÁS', 'DZONCAUICH': 'DZONCAUICH', 'ESPITA': 'ESPITA', 'HALACHOÓ': 'HALACHÓ', 'HOCABAÁ': 'HOCABÁ', 'HOCTUÚN': 'HOCTÚN', 'HOMUÚN': 'HOMÚN', 'HUHIÍ': 'HUHÍ', 'HUNUCMAÁ': 'HUNUCMÁ', 'IXIL': 'IXIL', 'IZAMAL': 'IZAMAL', 'KANASIÍN': 'KANASÍN', 'KANTUNIL': 'KANTUNIL', 'KAUA': 'KAUA', 'KINCHIL': 'KINCHIL', 'KOPOMAÁ': 'KOPOMÁ', 'MAMA': 'MAMA', 'MANIÍ': 'MANÍ', 'MAXCANUÚ': 'MAXCANÚ', 'MAYAPAÁN': 'MAYAPÁN', 'MEÉRIDA': 'MÉRIDA', 'MOCOCHAÁ': 'MOCOCHÁ', 'MOTUL': 'MOTUL', 'MUNA': 'MUNA', 'MUXUPIP': 'MUXUPIP', 'OPICHEÉN': 'OPICHÉN', 'OXKUTZCAB': 'OXKUTZCAB', 'PANABAÁ': 'PANABÁ', 'PETO': 'PETO', 'PROGRESO': 'PROGRESO', 'QUINTANA ROO': 'QUINTANA ROO', 'RIÍO LAGARTOS': 'RÍO LAGARTOS', 'SACALUM': 'SACALUM', 'SAMAHIL': 'SAMAHIL', 'SANAHCAT': 'SANAHCAT', 'SAN FELIPE': 'SAN FELIPE', 'SANTA ELENA': 'SANTA ELENA', 'SEYEÉ': 'SEYÉ', 'SINANCHEÉ': 'SINANCHÉ', 'SOTUTA': 'SOTUTA', 'SUCILAÁ': 'SUCILÁ', 'SUDZAL': 'SUDZAL', 'SUMA': 'SUMA', 'TAHDZIUÚ': 'TAHDZIÚ', 'TAHMEK': 'TAHMEK', 'TEABO': 'TEABO', 'TECOH': 'TECOH', 'TEKAL DE VENEGAS': 'TEKAL DE VENEGAS', 'TEKANTOÓ': 'TEKANTÓ', 'TEKAX': 'TEKAX', 'TEKIT': 'TEKIT', 'TEKOM': 'TEKOM', 'TELCHAC PUEBLO': 'TELCHAC PUEBLO', 'TELCHAC PUERTO': 'TELCHAC PUERTO', 'TEMAX': 'TEMAX', 'TEMOZOÓN': 'TEMOZÓN', 'TEPAKAÁN': 'TEPAKÁN', 'TETIZ': 'TETIZ', 'TEYA': 'TEYA', 'TICUL': 'TICUL', 'TIMUCUY': 'TIMUCUY', 'TINUM': 'TINUM', 'TIXCACALCUPUL': 'TIXCACALCUPUL', 'TIXKOKOB': 'TIXKOKOB', 'TIXMEHUAC': 'TIXMEHUAC', 'TIXPEÉHUAL': 'TIXPÉHUAL', 'TIZIMIÍN': 'TIZIMÍN', 'TUNKAÁS': 'TUNKÁS', 'TZUCACAB': 'TZUCACAB', 'UAYMA': 'UAYMA', 'UCUÚ': 'UCÚ', 'UMAÁN': 'UMÁN', 'VALLADOLID': 'VALLADOLID', 'XOCCHEL': 'XOCCHEL', 'YAXCABAÁ': 'YAXCABÁ', 'YAXKUKUL': 'YAXKUKUL', 'YOBAIÍN': 'YOBAÍN'}
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado

        elif re.search(r'ZACA', estado_republica, re.IGNORECASE):  
            ciudades_clave = ['APOZOL', 'APULCO', 'ATOLINGA', 'BENITO JU[AÁ]REZ', 'CALERA', 'CAÑITAS DE FELIPE PESCADOR', 'CONCEPCI[OÓ]N DEL ORO', 'CUAUHT[EÉ]MOC', 'CHALCHIHUITES', 'FRESNILLO', 'TRINIDAD GARC[IÍ]A DE LA CADENA', 'GENARO CODINA', 'GENERAL ENRIQUE ESTRADA', 'GENERAL FRANCISCO R. MURGU[IÍ]A', 'EL PLATEADO DE JOAQU[IÍ]N AMARO', 'GENERAL P[AÁ]NFILO NATERA', 'GUADALUPE', 'HUANUSCO', 'JALPA', 'JEREZ', 'JIM[EÉ]NEZ DEL TEUL', 'JUAN ALDAMA', 'JUCHIPILA', 'LORETO', 'LUIS MOYA', 'MAZAPIL', 'MELCHOR OCAMPO', 'MEZQUITAL DEL ORO', 'MIGUEL AUZA', 'MOMAX', 'MONTE ESCOBEDO', 'MORELOS', 'MOYAHUA DE ESTRADA', 'NOCHISTL[AÁ]N DE MEJ[IÍ]A', 'NORIA DE [AÁ]NGELES', 'OJOCALIENTE', 'P[AÁ]NUCO', 'PINOS', 'R[IÍ]O GRANDE', 'SAIN ALTO', 'EL SALVADOR', 'SOMBRERETE', 'SUSTICAC[AÁ]N', 'TABASCO', 'TEPECHITL[AÁ]N', 'TEPETONGO', 'TE[UÚ]L DE GONZ[AÁ]LEZ ORTEGA', 'TLALTENANGO DE S[AÁ]NCHEZ ROM[AÁ]N', 'VALPARA[IÍ]SO', 'VETAGRANDE', 'VILLA DE COS', 'VILLA GARC[IÍ]A', 'VILLA GONZ[AÁ]LEZ ORTEGA', 'VILLA HIDALGO', 'VILLANUEVA', 'CIUDAD DE ZACATECAS', 'TRANCOSO', 'SANTA MAR[IÍ]A DE LA PAZ', 'MUNICIPIO DE ZACATE', 'ZACATECAS']
            patrones_ciudades = {'APOZOL': 'APOZOL', 'APULCO': 'APULCO', 'ATOLINGA': 'ATOLINGA', 'BENITO JUAÁREZ': 'BENITO JUÁREZ', 'CALERA': 'CALERA', 'CAÑITAS DE FELIPE PESCADOR': 'CAÑITAS DE FELIPE PESCADOR', 'CONCEPCIOÓN DEL ORO': 'CONCEPCIÓN DEL ORO', 'CUAUHTEÉMOC': 'CUAUHTÉMOC', 'CHALCHIHUITES': 'CHALCHIHUITES', 'FRESNILLO': 'FRESNILLO', 'TRINIDAD GARCIÍA DE LA CADENA': 'TRINIDAD GARCÍA DE LA CADENA', 'GENARO CODINA': 'GENARO CODINA', 'GENERAL ENRIQUE ESTRADA': 'GENERAL ENRIQUE ESTRADA', 'GENERAL FRANCISCO R. MURGUIÍA': 'GENERAL FRANCISCO R. MURGUÍA', 'EL PLATEADO DE JOAQUIÍN AMARO': 'EL PLATEADO DE JOAQUÍN AMARO', 'GENERAL PAÁNFILO NATERA': 'GENERAL PÁNFILO NATERA', 'GUADALUPE': 'GUADALUPE', 'HUANUSCO': 'HUANUSCO', 'JALPA': 'JALPA', 'JEREZ': 'JEREZ', 'JIMEÉNEZ DEL TEUL': 'JIMÉNEZ DEL TEUL', 'JUAN ALDAMA': 'JUAN ALDAMA', 'JUCHIPILA': 'JUCHIPILA', 'LORETO': 'LORETO', 'LUIS MOYA': 'LUIS MOYA', 'MAZAPIL': 'MAZAPIL', 'MELCHOR OCAMPO': 'MELCHOR OCAMPO', 'MEZQUITAL DEL ORO': 'MEZQUITAL DEL ORO', 'MIGUEL AUZA': 'MIGUEL AUZA', 'MOMAX': 'MOMAX', 'MONTE ESCOBEDO': 'MONTE ESCOBEDO', 'MORELOS': 'MORELOS', 'MOYAHUA DE ESTRADA': 'MOYAHUA DE ESTRADA', 'NOCHISTLAÁN DE MEJIÍA': 'NOCHISTLÁN DE MEJÍA', 'NORIA DE AÁNGELES': 'NORIA DE ÁNGELES', 'OJOCALIENTE': 'OJOCALIENTE', 'PAÁNUCO': 'PÁNUCO', 'PINOS': 'PINOS', 'RIÍO GRANDE': 'RÍO GRANDE', 'SAIN ALTO': 'SAIN ALTO', 'EL SALVADOR': 'EL SALVADOR', 'SOMBRERETE': 'SOMBRERETE', 'SUSTICACAÁN': 'SUSTICACÁN', 'TABASCO': 'TABASCO', 'TEPECHITLAÁN': 'TEPECHITLÁN', 'TEPETONGO': 'TEPETONGO', 'TEUÚL DE GONZAÁLEZ ORTEGA': 'TEÚL DE GONZÁLEZ ORTEGA', 'TLALTENANGO DE SAÁNCHEZ ROMAÁN': 'TLALTENANGO DE SÁNCHEZ ROMÁN', 'VALPARAIÍSO': 'VALPARAÍSO', 'VETAGRANDE': 'VETAGRANDE', 'VILLA DE COS': 'VILLA DE COS', 'VILLA GARCIÍA': 'VILLA GARCÍA', 'VILLA GONZAÁLEZ ORTEGA': 'VILLA GONZÁLEZ ORTEGA', 'VILLA HIDALGO': 'VILLA HIDALGO', 'VILLANUEVA': 'VILLANUEVA', 'CIUDAD DE ZACATECAS': 'CIUDAD DE ZACATECAS', 'TRANCOSO': 'TRANCOSO', 'SANTA MARIÍA DE LA PAZ': 'SANTA MARÍA DE LA PAZ', 'MUNICIPIO DE ZACATE': 'CIUDAD DE ZACATE', 'ZACATECAS': 'ZACATECAS' }
            resultado = ciudades_regex(parrafo_municipio, ciudades_clave, patrones_ciudades)
            
            return resultado
        
    except Exception as e:
        return ''    
    
def municipio(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto)
        
        ciudades = []
        municipios = [ r"municipio", r"Municipio", r"MUNICIPIO", r"Alcaldia", r"ALCALDIA" ]

        for palabra in municipios:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.start()) 
                fin = min(len(texto), coincidencia.end() + 35) 
                contexto = parrafo[inicio:fin]
                ciudades.append(contexto)
            
        ciudad = ' '.join(ciudades)
            
        la_ciudad = pre_municipio(ciudad, estado(texto))
            
        return la_ciudad
    except Exception as e:
        return ''
    
def second_match_colonia(texto):             
    def limpiar_texto(texto):
        texto = re.sub(r'\s+', ' ', texto) 
        texto = re.sub(r'^\s+|\s+$', '', texto)
        return texto
    
    primer_patron = r'NOMBRE'
    segundo_patron = r'26284'
    tercer_patron = r'21'
    cuarto_patron = r'14'
    quinto_patron = r'CP|CERRO DE SAN'

    primer_match = re.search(primer_patron, texto)
    if primer_match:
        return limpiar_texto(texto[:primer_match.start()])

    segundo_match = re.search(segundo_patron, texto)
    if segundo_match:
        return limpiar_texto(texto[:segundo_match.start()])

    tercer_match = re.search(tercer_patron, texto)
    if tercer_match:
        return limpiar_texto(texto[:tercer_match.start()])
    
    cuarto_match = re.search(cuarto_patron, texto)
    if cuarto_match:
        return limpiar_texto(texto[:cuarto_match.start()])
    
    quinto_match = re.search(quinto_patron, texto)
    if quinto_match:
        return limpiar_texto(texto[:quinto_match.start()])

    return limpiar_texto(texto)

def pre_colonia(texto):
    
    texto = texto.upper()          
    
    def limpiar_texto(texto):
        return texto.replace(':', '').replace(';', '').replace('O FRACC', '').replace('"', '').replace(r'/', '').replace('/', '').replace('>', '').replace('<', '').replace('|', '').replace(',', '').replace('-', '').replace(')', '').replace('.', '').replace('11','').replace('13','').replace('ASENTAMIENTO','').replace('COLONIA','').replace('SA DE CV','').replace('#','').replace('12','').replace('SECCIORX','')

    primer_patron = r'1\s*\.\s*11\s*\.\s*4'
    segundo_patron = r'NOMBRE'
    tercer_patron = r'13'
    cuarto_patron = r'C[OÓ]DIGO'
    quinto_patron = r'[OC]P'
    sexto_patron = r'11'

    primer_match = re.search(primer_patron, texto)
    if primer_match:
        return second_match_colonia(limpiar_texto(texto[:primer_match.start()]))

    segundo_match = re.search(segundo_patron, texto)
    if segundo_match:
        return second_match_colonia(limpiar_texto(texto[:segundo_match.start()]))

    tercer_match = re.search(tercer_patron, texto)
    if tercer_match:
        return second_match_colonia(limpiar_texto(texto[:tercer_match.start()]))
    
    cuarto_match = re.search(cuarto_patron, texto)
    if cuarto_match:
        return second_match_colonia(limpiar_texto(texto[:cuarto_match.start()]))
    
    quinto_match = re.search(quinto_patron, texto)
    if quinto_match:
        return second_match_colonia(limpiar_texto(texto[:quinto_match.start()]))
    
    sexto_match = re.search(sexto_patron, texto)
    if sexto_match:
        return second_match_colonia(limpiar_texto(texto[:sexto_match.start()]))

    return ""

def colonia(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto[:7500]) 
        parrafo = parrafo.replace('Asentamientos', '')
        
        colonias = []
        fraccionamientos = [ r"Asentamiento", r'Colonia', r'asentamiento', 'colonia', r"ASENTAMIENTO", r'COLONIA', r'Fracciomaniento', r'FRACCIONAMIENTO', r'fraccionamiento' ]

        for palabra in fraccionamientos:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.end()) 
                fin = min(len(texto), coincidencia.end() + 100) 
                contexto = parrafo[inicio:fin]
                colonias.append(pre_colonia(contexto))
                
        colonias = [x for x in colonias if x and x.strip()]
        
        colonia = colonias[0]
            
        return colonia
    except Exception as e:
        return '' 
    
def second_match_calle(texto):             
    def limpiar_texto(texto):
        texto = re.sub(r'\s+', ' ', texto) 
        texto = re.sub(r'^\s+|\s+$', '', texto)
        return texto
    
    primer_patron = r'TIPO DE VIALIDAD'
    segundo_patron = r'TIPO VIALIDAD'
    tercer_patron = r'UBICADA'
    cuarto_patron = r'SUBD'
    quinto_patron = r'A FICO'
    sexto_patron = r'1 11 2'
    
    primer_match = re.search(primer_patron, texto)
    if primer_match:
        return limpiar_texto(texto[:primer_match.start()])

    segundo_match = re.search(segundo_patron, texto)
    if segundo_match:
        return limpiar_texto(texto[:segundo_match.start()])
    
    tercer_match = re.search(tercer_patron, texto)
    if tercer_match:
        return limpiar_texto(texto[:tercer_match.start()])
    
    cuarto_match = re.search(cuarto_patron, texto)
    if cuarto_match:
        return limpiar_texto(texto[:cuarto_match.start()])
    
    quinto_match = re.search(quinto_patron, texto)
    if quinto_match:
        return limpiar_texto(texto[:quinto_match.start()])
    
    sexto_match = re.search(sexto_patron, texto)
    if sexto_match:
        return limpiar_texto(texto[:sexto_match.start()])

    return limpiar_texto(texto)

def pre_calle(texto):
    
    texto = texto.upper()          
    
    def limpiar_texto(texto):
        return texto.replace('|', ' ').replace('AVALÚOS GLISON', ' ').replace('\\', ' ').replace('"', ' ').replace('(', ' ').replace(')', '').replace(';', ' ').replace(':', ' ').replace(r'/', ' ').replace('.', ' ').replace('DOMICILIO', ' ')

    primer_patron = r'1\s*\.\s*11\s*\.\s*2'
    segundo_patron = r'1 11\.\s*NOM|11\.\s*NOM|11 NOM'
    tercer_patron = r'1. NOM|1.1 2|1 11.'
    cuarto_patron = r'NOMBRE'
    quinto_patron = r'10. COLO|COLONIA|PODFRACCIONA|FRACCIONA'

    primer_match = re.search(primer_patron, texto)
    if primer_match:
        return second_match_calle(limpiar_texto(texto[:primer_match.start()]))

    segundo_match = re.search(segundo_patron, texto)
    if segundo_match:
        return second_match_calle(limpiar_texto(texto[:segundo_match.start()]))
    
    tercer_match = re.search(tercer_patron, texto)
    if tercer_match:
        return second_match_calle(limpiar_texto(texto[:tercer_match.start()]))
    
    cuarto_match = re.search(cuarto_patron, texto)
    if cuarto_match:
        return second_match_calle(limpiar_texto(texto[:cuarto_match.start()]))
    
    quinto_match = re.search(quinto_patron, texto)
    if quinto_match:
        return second_match_calle(limpiar_texto(texto[:quinto_match.start()]))

    return ""

def calle(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto[:7500])
        parrafo = parrafo.replace(',','.')
        
        calles = []
        avenidas = [ r"y número", r"y numero", r"domicilio", r"casa habitación", r"y numer", r"y nomeio", r"y adams", r"1.11.1"  ]

        for palabra in avenidas:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo, re.IGNORECASE)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.end()) 
                fin = min(len(texto), coincidencia.end() + 150) 
                contexto = parrafo[inicio:fin]
                calles.append(pre_calle(contexto))
                
        calles = [x for x in calles if x and x.strip()]
        
        calle = calles[0]
            
        return calle
    except Exception as e:
        return ''    
    
def eliminar_33(text):
    pattern = r"33[\s.,]*N.*"
    matches = list(re.finditer(pattern, text))
    
    if matches:
        
        last_match = matches[-1]
        return text[:last_match.start()]
    else:
        pattern_guion = r"33[\s.,]*-.*"
        matches_guion = list(re.finditer(pattern_guion, text))
        
        if matches_guion:
            last_match_guion = matches_guion[-1]
            return text[:last_match_guion.start()]
        else:
            return text

def extract_characters(text):
    text = eliminar_33(text)
    
    pattern = r"\$(.*)"
    match = re.search(pattern, text)
    
    if match:
        after_dollar = match.group(1)
        
        if '.' in after_dollar:
            split_index = after_dollar.rfind('.')
        elif ',' in after_dollar:
            split_index = after_dollar.rfind(',')
        else:
            split_index = -1  
            
        if split_index != -1:
            part1 = after_dollar[:split_index]
            part2 = after_dollar[split_index+1:]
            
            numbers_part1 = ''.join(re.findall(r'\d+', part1))
            numbers_part2 = ''.join(re.findall(r'\d+', part2))[:2]
            
            combined_numbers = f"{numbers_part1}.{numbers_part2}" if numbers_part1 and numbers_part2 else numbers_part1 or numbers_part2
            return combined_numbers
        else:
            return ''.join(re.findall(r'\d+', after_dollar))
    else:
        return ''
    
def second_pre_fecha(texto):
    
    texto = texto.replace('de',' ')
    texto = re.search(r'\d.*', texto).group() if re.search(r'\d', texto) else texto
    
    match_year = re.search(r'\b(\d{4})\b', texto)
    if not match_year:
        return ''  
    
    year = match_year.group(1)
    texto = texto[:match_year.start()]

    patrones_mes = {
        r'e.*o': "01", r'f.*e': "02", r'm.*zo': "03", r'a.*l': "04",
        r'm.*y': "05", r'jun': "06", r'jul': "07", r'a.*o': "08",
        r's.*e': "09", r'n.*e': "11", r'o.*e': "10", r'd.*re': "12"
    }
    
    month = None
    for patron, numero in patrones_mes.items():
        match_month = re.search(patron, texto, re.IGNORECASE)
        if match_month:
            month = numero
            break
    
    if not month:
        return ''
    
    match_day = re.search(r'\b(\d{2})\b', texto)
    if not match_day:
        return '' 
    
    day = match_day.group(1)
    
    return f"{year}-{month}-{day}" 

def pre_fecha(texto: str):
    
    def agregar_cero(texto):
        texto_modificado = re.sub(r'\b(\d{1})\b', r'0\1', texto)
        return texto_modificado.replace('-','/').replace('.','/')
    
    texto = agregar_cero(texto)
    
    patron = r'\b\d{2}[/\-]\d{2}[/\-]\d{4}\b'
    
    coincidencias = re.findall(patron, texto)
    if not coincidencias:
        return second_pre_fecha(texto)
    
    dia, mes, year = coincidencias[0].split('/')
    return f"{year}-{mes}-{dia}" 


def fecha(texto):
    try: 
        parrafo = re.sub(r'\s+', ' ', texto)
        parrafo = parrafo.replace(',','.')
        
        fechas = []
        avaluos = [ r"fecha del", r"del avalúo", r"del avaluo", r"fecha" ]

        for palabra in avaluos:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo, re.IGNORECASE)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.end()) 
                fin = min(len(texto), coincidencia.end() + 75) 
                contexto = parrafo[inicio:fin]
                fechas.append(pre_fecha(contexto))
                
        fechas = [x for x in fechas if x and x.strip()]
    
        la_fecha = fechas[0] 
        
        if len(la_fecha) == 0:
            la_fecha = pre_fecha(parrafo)
            
        return la_fecha
    except Exception as e:
        return ''    

def valor(texto):
    try:
        parrafo = re.sub(r'\s+', ' ', texto)
        parrafo = parrafo.replace('|','')
        parrafo = parrafo.replace('!','')
        parrafo = parrafo.replace(']','')
        
        boleano = 'NO'
        
        precios = []
        valores = [ r"valor concluido", r"Valor Concluido", r"VALOR CONCLUIDO" ]

        for palabra in valores:
            coincidencias = re.finditer(rf'{re.escape(palabra)}', parrafo)
        
            for coincidencia in coincidencias:
                inicio = max(0, coincidencia.start()) 
                fin = min(len(texto), coincidencia.end() + 25) 
                contexto = parrafo[inicio:fin]
                
                if 'Geo' in contexto:
                    pass
                else:
                    if len(extract_characters(contexto)) == 0:
                        pass
                    else: 
                        precios.append(extract_characters(contexto))
                        boleano = 'SI'
                        
        el_precio = precios[0]

        return el_precio, boleano 
    except Exception as e:
        return '', 'NO'

def extractor(pdf):
    
    paginas = paginas_con_texto(pdf)
    texto = extraer_texto_azure_ocr(pdf, paginas)
    
    avaluo, boolean_avaluo = valor(texto)
    codigo, boolean_codigo_de_barras = codigo_de_barras(pdf)

    diccionario = dict()
    diccionario['validez_del_formato'] = validez(texto)
    diccionario['opcion_de_firma'] = opcion_de_firma(texto)
    diccionario['legibilidad'] = legibilidad(texto)
    diccionario['codigo_de_barras'] = codigo
    diccionario['boolean_codigo_de_barras'] = boolean_codigo_de_barras
    diccionario['CB_Nomenclatura_Completez'] = boolean_codigo_de_barras
    diccionario['estado'] = estado(texto)
    diccionario['municipio'] = municipio(texto)
    diccionario['colonia'] = colonia(texto)
    diccionario['calle'] = calle(texto)
    diccionario['fecha'] = fecha(texto)
    diccionario['avaluo'] = avaluo
    diccionario['boolean_avaluo'] = boolean_avaluo
    
    return diccionario