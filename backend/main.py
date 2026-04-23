# main.py
import os
import sys
import re
import json
import logging
import warnings
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# === ПОДАВЛЕНИЕ ЛИШНИХ СООБЩЕНИЙ ===
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "critical"
os.environ["SENTENCE_TRANSFORMERS_VERBOSITY"] = "critical"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(level=logging.ERROR, force=True)
for lib_name in ["chromadb", "sentence_transformers", "huggingface_hub", 
                 "transformers", "httpx", "httpcore", "urllib3"]:
    logging.getLogger(lib_name).setLevel(logging.ERROR)

os.environ["TORCH_DISTRIBUTED_DEBUG"] = "OFF"

# Настройка кодировки для Windows
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import (
    DATA_DIR, CHATS_DIR, OLLAMA_MODEL, EMBEDDING_MODEL,
    APP_NAME, APP_VERSION, HOST, PORT, DEBUG, MAX_FILE_SIZE_MB,
    logger
)
from document_processor import DocumentProcessor
from rag_chain import RAGChain

# === Модели данных ===
class ChatRequest(BaseModel):
    message: str
    chat_id: str

class ChatResponse(BaseModel):
    response: str
    chat_id: str
    sources: List[str]

class ChatCreate(BaseModel):
    name: Optional[str] = "Новый чат"

class ChatUpdate(BaseModel):
    name: Optional[str] = None
    pinned: Optional[bool] = None

# === Управление чатами ===
class ChatManager:
    def __init__(self):
        self.chats_dir = CHATS_DIR
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_chat()

    def _get_chat_path(self, chat_id: str) -> Path:
        return self.chats_dir / f"{chat_id}.json"

    def _ensure_default_chat(self):
        if not self.get_all_chats():
            self.create_chat("Новый чат")

    def get_all_chats(self) -> List[Dict]:
        chats = []
        for file_path in self.chats_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat = json.load(f)
                    chats.append(chat)
            except Exception as e:
                logger.error(f"Ошибка загрузки чата: {e}")
        chats.sort(key=lambda x: (not x.get("pinned", False), -datetime.fromisoformat(x["updated_at"]).timestamp()))
        return chats

    def get_chat(self, chat_id: str) -> Optional[Dict]:
        try:
            with open(self._get_chat_path(chat_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

    def create_chat(self, name: str = "Новый чат") -> Dict[str, Any]:
        chat_id = str(uuid.uuid4())
        chat = {
            "id": chat_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "pinned": False,
            "messages": []
        }
        with open(self._get_chat_path(chat_id), 'w', encoding='utf-8') as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        logger.info(f"Создан чат: {name}")
        return chat

    def update_chat(self, chat_id: str, updates: Dict) -> Optional[Dict]:
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        chat.update(updates)
        chat["updated_at"] = datetime.now().isoformat()
        with open(self._get_chat_path(chat_id), 'w', encoding='utf-8') as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        return chat

    def add_message(self, chat_id: str, role: str, content: str, sources: Optional[List[str]] = None) -> Optional[Dict]:
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "sources": sources or []
        }
        chat["messages"].append(message)
        chat["updated_at"] = datetime.now().isoformat()
        with open(self._get_chat_path(chat_id), 'w', encoding='utf-8') as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        return message

    def delete_chat(self, chat_id: str) -> bool:
        try:
            self._get_chat_path(chat_id).unlink()
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
            return False

chat_manager = ChatManager()

# === Глобальные переменные ===
doc_processor = None
rag_chain = None

# === Lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global doc_processor, rag_chain
    
    logger.info("=" * 50)
    logger.info(f"Запуск {APP_NAME} v{APP_VERSION}")
    logger.info(f"Хост: {HOST}, Порт: {PORT}")
    logger.info(f"Ollama модель: {OLLAMA_MODEL}")
    logger.info(f"Эмбеддинг модель: {EMBEDDING_MODEL}")
    logger.info("=" * 50)

    try:
        logger.info("Инициализация компонентов...")
        doc_processor = DocumentProcessor()
        rag_chain = RAGChain()
        logger.info("✅ Система готова к работе")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")

    yield
    
    logger.info("Завершение работы приложения")

# === Создание приложения ===
app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= ЭНДПОИНТЫ =============

@app.get("/")
async def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "ollama_model": OLLAMA_MODEL,
        "embedding_model": EMBEDDING_MODEL
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ollama_available": rag_chain is not None,
        "chromadb_available": doc_processor is not None,
        "documents_count": doc_processor.collection.count() if doc_processor else 0
    }

# === Чаты ===
@app.get("/chats")
async def get_chats():
    return chat_manager.get_all_chats()

@app.post("/chats")
async def create_chat(data: ChatCreate):
    return chat_manager.create_chat(data.name)

@app.get("/chats/{chat_id}")
async def get_chat(chat_id: str):
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat

@app.put("/chats/{chat_id}")
async def update_chat(chat_id: str, data: ChatUpdate):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    chat = chat_manager.update_chat(chat_id, updates)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    success = chat_manager.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"status": "deleted"}

# === Сообщения ===
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Чат {request.chat_id}: {request.message[:100]}...")

        chat_exists = chat_manager.get_chat(request.chat_id)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Чат не найден")

        chat_manager.add_message(request.chat_id, "user", request.message)

        query = request.message
        filters = None
        if "filter:" in query.lower():
            parts = query.split("filter:", 1)
            query = parts[0].strip()
            filters = {"doc_type": parts[1].strip().upper()}

        if rag_chain is None:
            raise HTTPException(status_code=503, detail="RAG система не инициализирована")
        
        answer = rag_chain.ask(query, filters)

        sources = []
        if hasattr(rag_chain, '_last_fragments'):
            for frag in rag_chain._last_fragments[:3]:
                meta = frag.get("metadata", {})
                source = meta.get("standard_number") or meta.get("filename")
                clause = meta.get("clause", "")
                if source:
                    clause_str = f" (п. {clause})" if clause else ""
                    sources.append(f"{source}{clause_str}")

        sources = list(dict.fromkeys(sources))
        
        chat_manager.add_message(request.chat_id, "assistant", answer, sources)

        return ChatResponse(
            response=answer,
            chat_id=request.chat_id,
            sources=sources
        )

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Документы ===
@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Файл превышает {MAX_FILE_SIZE_MB} MB")

        allowed = ['.txt', '.pdf', '.docx', '.doc']
        ext = '.' + file.filename.split('.')[-1].lower()
        if ext not in allowed:
            raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат")

        docs_dir = DATA_DIR / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        file_path = docs_dir / file.filename
        with open(file_path, 'wb') as f:
            f.write(content)

        if doc_processor:
            doc_processor.index_documents()

        return {"status": "success", "filename": file.filename}

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/list")
async def list_documents():
    docs = []
    docs_dir = DATA_DIR / "documents"
    if docs_dir.exists():
        for f in docs_dir.iterdir():
            if f.is_file():
                docs.append({
                    "filename": f.name,
                    "size": f.stat().st_size
                })
    return docs

@app.post("/documents/scan")
async def scan_documents():
    if doc_processor:
        doc_processor.index_documents()
    return {"status": "scanned"}

@app.get("/documents/formats")
async def get_formats():
    return {
        "formats": [".txt", ".pdf", ".docx", ".doc"],
        "max_size_mb": MAX_FILE_SIZE_MB
    }

# === Статистика ===
@app.get("/stats")
async def get_stats():
    docs_dir = DATA_DIR / "documents"
    documents_count = len([f for f in docs_dir.iterdir() if f.is_file()]) if docs_dir.exists() else 0
    return {
        "vector_db": {
            "document_count": doc_processor.collection.count() if doc_processor else 0,
            "embedding_model": EMBEDDING_MODEL
        },
        "documents_count": documents_count,
        "ollama_available": rag_chain is not None,
        "chats_count": len(chat_manager.get_all_chats())
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )