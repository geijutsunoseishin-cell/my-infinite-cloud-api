import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pyrogram import Client

app = FastAPI(title="Infinite Cloud API")

# 1. Configuración de credenciales
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# 2. Inicialización del cliente de Telegram
tg_app = Client(
    "cloud_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True 
)

# --- INTERFAZ VISUAL ---
# Esta es la única función para "/"
@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <body style='font-family:sans-serif; text-align:center; padding-top:50px;'>
            <h1>✅ API Online</h1>
            <p>Pero no encontré el archivo <b>index.html</b> en tu repositorio de GitHub.</p>
            <p>Endpoints disponibles: <a href='/docs'>/docs</a></p>
        </body>
        """

# --- ENDPOINT PARA SUBIR ---
@app.post("/upload/")
async def upload_to_telegram(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        async with tg_app:
            sent_msg = await tg_app.send_document(
                chat_id=int(CHAT_ID),
                document=temp_path,
                caption=f"Archivo: {file.filename}"
            )
        
        return {
            "status": "success",
            "filename": file.filename,
            "telegram_id": sent_msg.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- ENDPOINT PARA DESCARGAR ---
@app.get("/download/{message_id}")
async def download_from_telegram(message_id: int):
    download_path = f"download_{message_id}"
    try:
        async with tg_app:
            file_path = await tg_app.download_media(
                message=f"{CHAT_ID}/{message_id}",
                file_name=download_path
            )
            
            if not file_path:
                raise HTTPException(status_code=404, detail="Archivo no encontrado")

            return FileResponse(
                path=file_path, 
                filename=os.path.basename(file_path),
                background=asyncio.create_task(delete_after_send(file_path))
            )
    except Exception as e:
        if os.path.exists(download_path):
            os.remove(download_path)
        raise HTTPException(status_code=500, detail=str(e))

# --- LIMPIEZA POST-ENVÍO ---
async def delete_after_send(path: str):
    await asyncio.sleep(60) 
    if os.path.exists(path):
        os.remove(path)
