#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config import CHROMA_DB_PATH, logger
import chromadb

print(f"🔍 Проверка базы: {CHROMA_DB_PATH}")
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Список коллекций
collections = [c.name for c in client.list_collections()]
print(f"📦 Коллекции: {collections}")

if "legal_docs" in collections:
    coll = client.get_collection("legal_docs")
    total = coll.count()
    print(f"✅ 'legal_docs': {total} записей")
    
    # Пример метаданных
    sample = coll.get(include=["metadatas"], limit=3)
    if sample["metadatas"]:
        print("📋 Примеры файлов:")
        for m in sample["metadatas"]:
            print(f"   • {m.get('filename', 'N/A')}")
    else:
        print("⚠ Нет метаданных в выборке")
else:
    print("❌ Коллекция 'legal_docs' не найдена!")