import os
import uvicorn
import shutil

from tika import parser 
from extractorAvaluos import *

from typing import List
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()

@app.post("/AVALUOS/")
async def upload_files(files: List[UploadFile] = File(...)):
    diccionario = dict()
    for file in files:
        try:
            diccionario[file.filename] = extractor(file.filename)
            
        except Exception as e:
            diccionario[file.filename] = str(e)
    
    return diccionario
    
if __name__ == "__main__":
    uvicorn.run(app)
    
    
