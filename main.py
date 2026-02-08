import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pyrogram import Client
import asyncio
from fastapi.responses import HTMLResponse # Asegúrate de que esta línea esté arriba con los imports

app = FastAPI(title="Infinite Cloud API")

# 1. Configuración de credenciales (Se configuran en el panel de Render)
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# 2. Inicialización del cliente de Telegram
# 'in_memory=True' evita que Render intente escribir archivos de sesión permanentes
tg_app = Client(
    "cloud_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True 
)

@app.get("/")
def home():
    return {
        "message": "Servidor de Nube Infinita Activo",
        "endpoints": {
            "upload": "/upload/ (POST)",
            "download": "/download/{message_id} (GET)"
        }
    }

# --- ENDPOINT PARA SUBIR ---
@app.post("/upload/")
async def upload_to_telegram(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    
    try:
        # Guardamos el archivo en el disco temporal de Render
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Enviamos a Telegram
        async with tg_app:
            sent_msg = await tg_app.send_document(
                chat_id=int(CHAT_ID),
                document=temp_path,
                caption=f"Archivo: {file.filename}"
            )
        
        return {
            "status": "success",
            "filename": file.filename,
            "telegram_id": sent_msg.id,
            "info": "Guarda el telegram_id para descargar el archivo después."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Limpieza: Borrar el temporal de Render
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- ENDPOINT PARA DESCARGAR ---
@app.get("/download/{message_id}")
async def download_from_telegram(message_id: int):
    # Creamos un nombre temporal para la descarga
    download_path = f"download_{message_id}"
    
    try:
        async with tg_app:
            # Buscamos el mensaje en Telegram y descargamos el archivo
            file_path = await tg_app.download_media(
                message=f"{CHAT_ID}/{message_id}",
                file_name=download_path
            )
            
            if not file_path:
                raise HTTPException(status_code=404, detail="Archivo no encontrado en Telegram")

            # Retornamos el archivo al usuario
            return FileResponse(
                path=file_path, 
                filename=os.path.basename(file_path),
                background=asyncio.create_task(delete_after_send(file_path))
            )

    except Exception as e:
        if os.path.exists(download_path):
            os.remove(download_path)
        raise HTTPException(status_code=500, detail=str(e))

# Función auxiliar para borrar el archivo de Render después de enviarlo al usuario


@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>API Activa</h1><p>Archivo index.html no encontrado en el repositorio.</p>"
async def delete_after_send(path: str):
    await asyncio.sleep(60) # Espera 1 minuto para asegurar que se envió
    if os.path.exists(path):
        os.remove(path)
