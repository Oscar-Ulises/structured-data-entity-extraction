# structured-data-entity-extraction

---

## 📄 Description

Open source extractor for entity recognition in **structured commercial documents**.  
All processing is local and reproducible.  
Built to parse and analyze *actas comerciales* using OCR and deterministic logic.

> “Structured data refers to information with a high degree of organization, such that inclusion in a relational database is seamless and readily searchable…”  
> — Wikipedia ([Structured data](https://en.wikipedia.org/wiki/Structured_data))

---

## 🧱 Architecture Overview

- Text Extraction (OCR) via [Tesseract](https://github.com/tesseract-ocr/tesseract) and Azure OCR  
- Rule-based entity extraction using regular expressions and keyword matching  
- Output returned as dictionary for downstream usage

---

## 📦 Dependencies

```python
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
```

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## 🧠 Core Function

```python
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
```

---

## 📊 Extracted Entities

| Field                        | Description                                     |
|-----------------------------|-------------------------------------------------|
| `validez_del_formato`       | Format compliance status                        |
| `opcion_de_firma`           | Presence of signature option                    |
| `legibilidad`               | OCR readability rating                          |
| `codigo_de_barras`          | Detected barcode value                          |
| `boolean_codigo_de_barras`  | Presence of barcode (True/False)                |
| `CB_Nomenclatura_Completez` | Redundant flag for barcode completeness         |
| `estado`                    | Detected state name                             |
| `municipio`                 | Detected municipality name                      |
| `colonia`                   | Extracted neighborhood                          |
| `calle`                     | Street name                                     |
| `fecha`                     | Date of record                                  |
| `avaluo`                    | Extracted property value                        |
| `boolean_avaluo`            | Presence of value detected (True/False)         |

---

## 🪪 License

This project is licensed under the MIT License.  
Use, modify, and distribute freely.
