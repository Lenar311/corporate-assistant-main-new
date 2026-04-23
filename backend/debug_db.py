# debug_db.py — проверка метаданных в ChromaDB
import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_DB_PATH, EMBEDDING_MODEL, logger

print(f"🔍 Подключение к базе: {CHROMA_DB_PATH}")
print(f"📦 Модель эмбеддингов: {EMBEDDING_MODEL}\n")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection("legal_docs")

# Загружаем ту же модель, что использовалась при индексации
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

# Кодируем запрос через нашу модель (не query_texts!)
query_text = "6.1 нормоконтроль содержание"
prefixed = f"query: {query_text}"
query_embedding = embedding_model.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True).tolist()

# Ищем фрагменты по ГОСТ 2.111-2013
results = collection.query(
    query_embeddings=[query_embedding],  # ✅ query_embeddings, а не query_texts
    n_results=10,
    where={"standard_number": "ГОСТ 2.111-2013"},
    include=["documents", "metadatas", "distances"]
)

print(f"🔍 Найдено фрагментов: {len(results['documents'][0])}\n")

if len(results['documents'][0]) == 0:
    print("❌ Не найдено фрагментов с standard_number='ГОСТ 2.111-2013'")
    print("\n🔍 Попробуем без фильтра по ГОСТ:")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        include=["documents", "metadatas", "distances"]
    )
    print(f"   Найдено: {len(results['documents'][0])} фрагментов\n")

for i, (doc, meta, dist) in enumerate(zip(
    results["documents"][0], 
    results["metadatas"][0], 
    results["distances"][0]
), 1):
    clause = meta.get("clause", "N/A")
    section = meta.get("section_title", "")[:50]
    filename = meta.get("filename", "")[:60]
    print(f"[{i}] clause={clause}, section='{section}', dist={dist:.4f}")
    print(f"    Файл: {filename}")
    print(f"    Текст[:250]: {doc.strip()[:250]}...")
    print()