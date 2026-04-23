"""Центральная конфигурация проекта"""
import os
import logging
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["CHROMA_TELEMETRY"] = "false"
os.environ["CHROMA_TELEMETRY_IMPL"] = "none"
# =============================================================================
# 📁 ПУТИ И ДИРЕКТОРИИ (ВСЕ КАК Path ОБЪЕКТЫ)
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
CHATS_DIR = DATA_DIR / "chats"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
INDEX_STATE_PATH = DATA_DIR / "index_state.json"
CACHE_FILE = DATA_DIR / "answer_cache.json"

# =============================================================================
# 🤖 МОДЕЛИ
# =============================================================================

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_USE_ONNX = os.getenv("EMBEDDING_USE_ONNX", "false").lower() == "true"

# LLM (Ollama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "minicpm-v")

# =============================================================================
# ⚙️ НАСТРОЙКИ RAG
# =============================================================================

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "3600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "1000"))
TOP_K = int(os.getenv("TOP_K", "15"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

# =============================================================================
# 🎯 ПАРАМЕТРЫ ГЕНЕРАЦИИ
# =============================================================================

OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

# =============================================================================
# 🌐 СЕРВЕР
# =============================================================================

APP_NAME = os.getenv("APP_NAME", "Corporate Assistant")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# =============================================================================
# 📄 ДОКУМЕНТЫ
# =============================================================================

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "30"))

# =============================================================================
# 📝 ЛОГИРОВАНИЕ
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "")

def setup_logging() -> logging.Logger:
    """Настраивает и возвращает логгер"""
    logger = logging.getLogger("chatbot")
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if LOG_FILE:
        try:
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠ Не удалось создать файл лога {LOG_FILE}: {e}")
    
    return logger

# Создаем логгер
logger = setup_logging()

# =============================================================================
# 📂 СОЗДАНИЕ ДИРЕКТОРИЙ
# =============================================================================

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Директории созданы:")
    logger.info(f"   DATA_DIR: {DATA_DIR}")
    logger.info(f"   CHROMA_DB_PATH: {CHROMA_DB_PATH}")
    logger.info(f"   CACHE_FILE: {CACHE_FILE}")
except Exception as e:
    print(f"⚠ Ошибка при создании директорий: {e}")

# =============================================================================
# 🔧 КЭШ ЭМБЕДДИНГ-МОДЕЛИ
# =============================================================================

_embedding_model_cache = None
_embedding_model_lock = threading.Lock()

def get_embedding_model():
    """Возвращает кэшированную эмбеддинг-модель"""
    global _embedding_model_cache
    
    if _embedding_model_cache is None:
        with _embedding_model_lock:
            if _embedding_model_cache is None:
                logger.info(f"🔧 Загрузка эмбеддинг-модели: {EMBEDDING_MODEL}")
                
                from sentence_transformers import SentenceTransformer
                _embedding_model_cache = SentenceTransformer(EMBEDDING_MODEL)
                    
                logger.info("✅ Эмбеддинг-модель загружена")
    
    return _embedding_model_cache

# =============================================================================
# 📊 ВЫВОД КОНФИГУРАЦИИ
# =============================================================================

logger.info("=" * 60)
logger.info(f"📋 Конфигурация загружена:")
logger.info(f"   EMBEDDING_MODEL: {EMBEDDING_MODEL}")
logger.info(f"   OLLAMA_MODEL: {OLLAMA_MODEL}")
logger.info(f"   TOP_K: {TOP_K}")
logger.info("=" * 60)