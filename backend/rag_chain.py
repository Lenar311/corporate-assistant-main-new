# rag_chain.py — ВЕРСИЯ: 3.4 — агрегация подпунктов + очистка текста + инструкционный формат
# 🔥 Адаптировано под ваш чат-бот (без сессий, с LRU-кэшем)

import os
import re
import time
from typing import Dict, List, Optional, Any
from collections import OrderedDict

import chromadb
import ollama
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_DB_PATH,
    DATA_DIR,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    TOP_K,
    logger,
)


# =============================================================================
# 📋 КОНСТАНТЫ
# =============================================================================

KNOWN_ANSWERS = {
    "формат а5": "Формат А5 (148×210 мм) допускается применять при необходимости. 📚 Источник: ГОСТ 2.301-68, п. 4",
    "таблица форматов": "| Формат | Размеры, мм |\n|--------|-------------|\n| А0 | 841 × 1189 |\n| А1 | 594 × 841 |\n| А2 | 420 × 594 |\n| А3 | 297 × 420 |\n| А4 | 210 × 297 |\n| А5 | 148 × 210 |\n📚 Источник: ГОСТ 2.301-68, п. 3-4",
    "основные форматы ескд": "Основные форматы листов по ГОСТ 2.301-68:\n\n| Формат | Размеры, мм |\n|--------|-------------|\n| А0 | 841 × 1189 |\n| А1 | 594 × 841 |\n| А2 | 420 × 594 |\n| А3 | 297 × 420 |\n| А4 | 210 × 297 |\n| А5 | 148 × 210 |\n\n📚 Источник: ГОСТ 2.301-68, п. 3-4",
    "какие форматы считаются основными": "Основные форматы листов по ГОСТ 2.301-68:\n\n| Формат | Размеры, мм |\n|--------|-------------|\n| А0 | 841 × 1189 |\n| А1 | 594 × 841 |\n| А2 | 420 × 594 |\n| А3 | 297 × 420 |\n| А4 | 210 × 297 |\n\n📚 Источник: ГОСТ 2.301-68, п. 3-4",
    "форматы листов в гост 2.301": "Основные форматы по ГОСТ 2.301-68:\n\n| Формат | Размеры, мм |\n|--------|-------------|\n| А0 | 841 × 1189 |\n| А1 | 594 × 841 |\n| А2 | 420 × 594 |\n| А3 | 297 × 420 |\n| А4 | 210 × 297 |\n| А5 | 148 × 210 |\n\n📚 ГОСТ 2.301-68, п. 3-4",
    
    "какие форматы": "Основные форматы листов по ГОСТ 2.301-68:\n\n| Формат | Размеры, мм |\n|--------|-------------|\n| А0 | 841 × 1189 |\n| А1 | 594 × 841 |\n| А2 | 420 × 594 |\n| А3 | 297 × 420 |\n| А4 | 210 × 297 |\n\n📚 ГОСТ 2.301-68, п. 3-4",
}


# 🔥 ОБНОВЛЁННЫЙ SYSTEM_PROMPT с поддержкой инструкционного формата
SYSTEM_PROMPT = """
Ты — нормоконтролер и эксперт по нормативным документам (ГОСТ, ОСТ, ЕСКД).
Отвечай ТОЧНО и ПОЛНО, используя только контекст ниже.

✅ ПРАВИЛА:
1. Начинай сразу с сути, без "Согласно документу...".
2. Списки/перечисления приводи полностью, с маркерами.
3. ОТВЕЧАЙ ТОЛЬКО на русском.
4. НЕ ИСПОЛЬЗУЙ внутренние знания — только контекст.
5. Если нет информации: "В предоставленных документах нет информации".
6. НЕ указывай ГОСТ, которого нет в метаданных источника.
7. "дублирование/дубликаты" → только ГОСТ 2.502-2013.
8. "изменения/правки" → только ГОСТ 2.106 или ГОСТ Р 2.504.

📋 ИНСТРУКЦИОННЫЙ ФОРМАТ (если вопрос содержит "можно ли", "как", "требуется ли", "порядок", "алгоритм"):
Отвечай в виде нумерованной инструкции:
  0) [Прямой ответ: Да/Нет с кратким условием]
  1) [Определение ключевого понятия из вопроса]
  2) [Определение связанного понятия]
  3) [Условия/требования/владелец/ответственный]
  4) [Действия/форма/документ/разрешение]
  5) [Ссылка на нормативный пункт]

💡 Противоречия — укажи и приведи оба варианта.
💡 Развёрнутый ответ — да, но без "воды".
"""


# =============================================================================
# 🔗 LRU КЭШ
# =============================================================================

class LRUCache:
    """Простой LRU-кэш для запросов"""
    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[str]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: str):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()


# =============================================================================
# 🔗 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def _build_gost_mapping_from_files(data_dir: str) -> Dict[str, str]:
    """Строит маппинг тем на номера ГОСТ по именам файлов."""
    mapping = {}
    if not os.path.exists(data_dir):
        return mapping
    
    for fn in os.listdir(data_dir):
        if not fn.lower().endswith(('.pdf', '.doc', '.docx')):
            continue
        
        m = re.search(r'(ГОСТ\s*[Рр]?\s*[\d\.\-]+(?:-\d{4})?)', fn, re.I)
        if not m:
            continue
        
        gost = m.group(1).strip()
        desc = re.sub(r'ГОСТ\s*[Рр]?\s*[\d\.\-]+(?:-\d{4})?', '', fn, flags=re.I).lower()
        
        for w in re.findall(r'\b[а-яё]{4,}\b', desc):
            stem = w[:min(8, len(w))]
            if stem not in mapping:
                mapping[stem] = gost
    
    return mapping


# Глобальный маппинг тем на ГОСТ
GOST_TOPIC_MAPPING = _build_gost_mapping_from_files(str(DATA_DIR))


# =============================================================================
# 🔗 ОСНОВНОЙ КЛАСС RAGChain
# =============================================================================

class RAGChain:
    def __init__(self):
        logger.info("🚀 Инициализация RAGChain v3.4")
        
        # ChromaDB
        chroma_path_str = str(CHROMA_DB_PATH)
        os.makedirs(chroma_path_str, exist_ok=True)
        self.client = chromadb.PersistentClient(path=chroma_path_str)
        self.collection = self.client.get_or_create_collection(name="legal_docs")
        
        # Эмбеддинг-модель
        logger.info("📦 Загрузка эмбеддинг-модели: %s", EMBEDDING_MODEL)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✅ Эмбеддинг-модель загружена")
        
        # Ollama
        self.ollama_client = ollama.Client(host=OLLAMA_BASE_URL, timeout=180)
        
        # Кэш и статистика
        self._cache = LRUCache(capacity=100)
        self._session_stats = {"queries": 0, "cache_hits": 0}
        self._data_dir = str(DATA_DIR)

    # -------------------------------------------------------------------------
    # 🔤 ЭМБЕДДИНГИ
    # -------------------------------------------------------------------------

    def _encode_query(self, query: str) -> List[float]:
        """Кодирует запрос. Для BGE-M3 префикс НЕ НУЖЕН."""
        if "bge" in EMBEDDING_MODEL.lower():
            prefixed = query
        else:
            prefixed = f"query: {query}"
        
        embedding = self.embedding_model.encode(
            prefixed,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding.tolist()

    # -------------------------------------------------------------------------
    # 🔍 ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # -------------------------------------------------------------------------

    def _extract_gost_from_query(self, query: str) -> Optional[str]:
        match = re.search(r'ГОСТ\s*[Рр]?\s*([\d\.\-]+)', query, re.I)
        return match.group(1).strip() if match else None

    def _extract_clause_from_query(self, query: str) -> Optional[str]:
        for p in [r'(?:п\.?\s*|пункт\s*)(\d{1,2}(?:\.\d+)+)', r'^(\d{1,2}(?:\.\d+)+)\s']:
            m = re.search(p, query, re.I)
            if m:
                return m.group(1).strip()
        return None

    def _normalize_clause(self, clause) -> str:
        return str(clause).strip() if clause is not None else ""

    def _clause_in_text(self, text: str, clause_number: str) -> bool:
        if not clause_number or not text:
            return False
        
        tc = text.strip()
        patterns = [
            rf'^{re.escape(clause_number)}(?:[\s\.\)\:\–\-\,\;\n\r]|$)',
            rf'(?:^|\s){re.escape(clause_number)}(?:[\s\.\)\:\–\-\,\;\n\r]|$)',
            rf'(?:^|\s)(?:п\.?\s*|пункт\s+){re.escape(clause_number)}(?:[\s\.\)\:\–\-\,\;\n\r]|$)',
        ]
        
        for p in patterns:
            if re.search(p, tc, re.I | re.M):
                return True
        
        if tc.startswith(clause_number):
            nc = tc[len(clause_number):len(clause_number)+1] if len(tc) > len(clause_number) else ''
            if not nc or nc in ' .):,;-\n\r':
                return True
        
        return False

    # -------------------------------------------------------------------------
    # 🔍 АГРЕГАЦИЯ ПОДПУНКТОВ
    # -------------------------------------------------------------------------

    def _get_fragments_by_clause(self, gost_number: str, clause_number: str, limit: int = 50) -> List[Dict]:
        """Возвращает ВСЕ фрагменты, относящиеся к пункту (включая подпункты)."""
        if not gost_number or not clause_number:
            return []
        
        results = []
        try:
            # Точный поиск по clause
            res = self.collection.get(
                where={"clause": clause_number},
                include=["documents", "metadatas"],
                limit=limit
            )
            
            for doc, meta in zip(res.get("documents", []), res.get("metadatas", [])):
                sn = meta.get("standard_number", "") if meta else ""
                if gost_number in sn:
                    results.append({"text": doc, "metadata": meta, "distance": 0.0, "match_type": "exact"})
            
            # Семантический поиск для подпунктов
            if len(results) < limit:
                res2 = self.collection.query(
                    query_embeddings=[self._encode_query(f"пункт {clause_number}")],
                    n_results=limit * 2,
                    include=["documents", "metadatas", "distances"]
                )
                
                for doc, meta, dist in zip(res2.get("documents", [[]])[0], 
                                          res2.get("metadatas", [[]])[0], 
                                          res2.get("distances", [[]])[0]):
                    if len(results) >= limit:
                        break
                    
                    sn = meta.get("standard_number", "") if meta else ""
                    if gost_number not in sn:
                        continue
                    
                    if self._clause_in_text(doc, clause_number):
                        if not any(r["text"] == doc for r in results):
                            results.append({
                                "text": doc, 
                                "metadata": meta, 
                                "distance": float(dist), 
                                "match_type": "text"
                            })
            
            logger.debug(f"📊 _get_fragments_by_clause: найдено {len(results)} фрагментов")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска по пункту: {e}")
            return []

    # -------------------------------------------------------------------------
    # 🔍 ОПРЕДЕЛЕНИЕ ИНСТРУКЦИОННОГО ЗАПРОСА
    # -------------------------------------------------------------------------

    def _is_instructional_query(self, query: str) -> bool:
        """Определяет, требует ли вопрос ответа в формате пошаговой инструкции."""
        instructional_keywords = [
            'можно ли', 'как сделать', 'как изготовить', 'порядок', 'алгоритм',
            'требуется ли', 'что нужно', 'шаги', 'инструкция', 'процедура',
            'дубликат', 'копия', 'подлинник', 'разрешение', 'форма',
            'оформить', 'получить', 'согласовать', 'утвердить', 'допускается ли'
        ]
        
        ql = query.lower()
        
        # Исключаем простые вопросы "что такое"
        if re.match(r'^\s*(что|кто|где|когда|почему|зачем)\s+', ql):
            return False
        
        return any(kw in ql for kw in instructional_keywords)

    # -------------------------------------------------------------------------
    # 📋 ФОРМАТИРОВАНИЕ ИНСТРУКЦИОННОГО ОТВЕТА
    # -------------------------------------------------------------------------

    def _format_instructional_response(self, query: str, frags: List[Dict]) -> Optional[str]:
        """Формирует ответ в виде структурированной инструкции на основе контекста."""
        
        def clean_text(text: str) -> str:
            text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
            text = re.sub(r'\s*-\s*', ' ', text)
            text = ' '.join(text.split())
            text = re.sub(r'\s+([.,;:!?])', r'\1', text)
            return text.strip()
        
        # Извлекаем ключевые термины
        terms = re.findall(r'\b[а-яё]{4,}\b', query.lower())
        stop_words = {'можно', 'ли', 'как', 'что', 'такое', 'нужно', 'требуется',
                      'сделать', 'изготовить', 'получить', 'оформить', 'подлинник'}
        key_terms = [t for t in terms if t not in stop_words][:3]
        
        if not key_terms:
            return None
        
        instruction_parts = []
        sources = []
        ql = query.lower()
        
        # ШАГ 0: Прямой ответ на "можно ли"
        if any(kw in ql for kw in ['можно ли', 'разрешено ли', 'допускается ли']):
            yes_words = ['следует', 'допускается', 'разрешено', 'можно', 'должен', 'необходимо', 'вправе']
            no_words = ['запрещено', 'не допускается', 'нельзя', 'не следует', 'запрещается']
            
            answer = None
            for frag in frags[:5]:
                text_lower = frag['text'].lower()
                if any(kw in text_lower for kw in yes_words):
                    answer = "✅ Да, допускается при соблюдении требований нормативных документов."
                    break
                elif any(kw in text_lower for kw in no_words):
                    answer = "❌ Нет, не допускается согласно нормативным требованиям."
                    break
            
            if answer:
                instruction_parts.append(f"0) {answer}")
        
        # ШАГ 1-2: Определения ключевых понятий
        definitions_found = 0
        definition_templates = [
            r'(.{{0,150}}?\b{}\b.{{0,150}}?это.{{0,100}}?)',
            r'(.{{0,150}}?\b{}\b.{{0,150}}?является.{{0,100}}?)',
            r'(.{{0,150}}?\b{}\b\s*—\s*.{{0,150}}?)',
        ]
        
        for term in key_terms:
            if definitions_found >= 2:
                break
            
            for frag in frags:
                text = clean_text(frag['text'])
                if term not in text.lower():
                    continue
                
                for tmpl in definition_templates:
                    pattern = tmpl.format(re.escape(term))
                    match = re.search(pattern, text, re.I | re.DOTALL)
                    if match:
                        defin = match.group(1).strip()
                        if '. ' in defin:
                            defin = defin.split('. ')[0] + '.'
                        if 15 < len(defin) < 250:
                            instruction_parts.append(f"{len(instruction_parts)+1}) {defin}")
                            definitions_found += 1
                            
                            meta = frag.get('metadata', {})
                            src = meta.get('standard_number') or meta.get('filename', 'Документ')
                            clause = self._normalize_clause(meta.get('clause'))
                            clause_str = f", п. {clause}" if clause and clause != "-1" else ""
                            sources.append(f"{src}{clause_str}")
                            break
                
                if definitions_found >= 2:
                    break
        
        # ШАГ 3: Условия / требования
        if len(instruction_parts) < 4:
            condition_keywords = ['владелец', 'собственник', 'держатель', 'разрешение', 
                                  'согласование', 'условие', 'требование', 'должен', 'необходимо']
            for frag in frags:
                text = clean_text(frag['text'])
                if any(kw in text.lower() for kw in condition_keywords):
                    sentences = re.split(r'[.!?]', text)
                    for sent in sentences:
                        sent = sent.strip()
                        if any(kw in sent.lower() for kw in condition_keywords) and 20 < len(sent) < 300:
                            instruction_parts.append(f"{len(instruction_parts)+1}) Условия: {sent}")
                            meta = frag.get('metadata', {})
                            src = meta.get('standard_number') or meta.get('filename', 'Документ')
                            sources.append(src)
                            break
                    break
        
        # ШАГ 4: Порядок действий / форма
        if len(instruction_parts) < 5:
            form_keywords = ['форма', 'бланк', 'заявление', 'акт', 'протокол', 'оформление']
            for frag in frags:
                text = clean_text(frag['text'])
                if any(kw in text.lower() for kw in form_keywords):
                    sentences = re.split(r'[.!?]', text)
                    for sent in sentences:
                        sent = sent.strip()
                        if any(kw in sent.lower() for kw in form_keywords) and 20 < len(sent) < 300:
                            instruction_parts.append(f"{len(instruction_parts)+1}) Порядок/форма: {sent}")
                            meta = frag.get('metadata', {})
                            src = meta.get('standard_number') or meta.get('filename', 'Документ')
                            sources.append(src)
                            break
                    break
        
        # Возвращаем если сформировали минимум 3 пункта
        if len(instruction_parts) >= 3:
            unique_sources = list(dict.fromkeys(sources))
            return "\n".join(instruction_parts) + f"\n\n📚 Источники: {'; '.join(unique_sources)}"
        
        return None

    # -------------------------------------------------------------------------
    # 🔍 ПОИСК
    # -------------------------------------------------------------------------

    def retrieve(self, query: str, filters: Optional[Dict] = None, top_k: int = TOP_K) -> List[Dict]:
        requested_gost = self._extract_gost_from_query(query)
        requested_clause = self._extract_clause_from_query(query)
        
        if requested_clause:
            expanded_k = top_k * 50
        elif requested_gost:
            expanded_k = top_k * 20
        else:
            expanded_k = top_k * 5
        
        query_embedding = self._encode_query(query)
        
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=expanded_k,
            where=filters,
            include=["documents", "metadatas", "distances"],
        )
        
        if not result or not result.get("documents") or not result["documents"][0]:
            return []
        
        fragments = []
        for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            fragments.append({
                "text": doc,
                "metadata": meta or {},
                "distance": float(dist) if dist is not None else float('inf')
            })
        
        # Фильтрация по ГОСТ
        if requested_gost and fragments:
            fragments = [f for f in fragments if requested_gost in f["metadata"].get("standard_number", "")]
        
        # Агрегация подпунктов
        if requested_clause and requested_gost and fragments:
            exact_match = any(self._normalize_clause(f["metadata"].get("clause", "")) == requested_clause for f in fragments)
            if not exact_match or len(fragments) < 3:
                clause_frags = self._get_fragments_by_clause(requested_gost, requested_clause, limit=20)
                if clause_frags:
                    existing_texts = {f["text"] for f in fragments}
                    for cf in clause_frags:
                        if cf["text"] not in existing_texts:
                            fragments.append(cf)
                    logger.info(f"📊 Агрегировано {len(clause_frags)} фрагментов для пункта {requested_clause}")
        
        fragments.sort(key=lambda x: x["distance"])
        return fragments[:top_k]

    def search(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        return self.retrieve(query, filters, TOP_K)

    # -------------------------------------------------------------------------
    # 🎯 ОСНОВНОЙ МЕТОД ask
    # -------------------------------------------------------------------------

    def ask(self, query: str, filters: Optional[Dict] = None) -> str:
        query_lower = query.lower().strip()
        cache_key = f"{query_lower}|{str(filters)}"
        
        # 1. Быстрые ответы
        for key, answer in KNOWN_ANSWERS.items():
            if key in query_lower:
                return answer
        
        # 2. Проверка кэша
        cached = self._cache.get(cache_key)
        if cached:
            self._session_stats["cache_hits"] += 1
            logger.debug(f"Cache hit: {query_lower[:50]}")
            return cached
        
        self._session_stats["queries"] += 1
        
        logger.info(f"🔎 Запрос: '{query}'")
        fragments = self.search(query, filters)
        logger.info(f"📄 Найдено: {len(fragments)} фрагментов")
        
        if not fragments:
            answer = "В предоставленных документах нет информации"
            self._cache.set(cache_key, answer)
            return answer
        
        # 3. Проверка на инструкционный запрос
        if self._is_instructional_query(query):
            instructional_answer = self._format_instructional_response(query, fragments)
            if instructional_answer:
                logger.info("📋 Сформирован инструкционный ответ")
                self._cache.set(cache_key, instructional_answer)
                return instructional_answer
        
        # 4. Один хороший фрагмент — возвращаем без LLM
        if len(fragments) == 1 and fragments[0]["distance"] < 0.3:
            frag = fragments[0]
            meta = frag.get("metadata", {})
            src = meta.get("standard_number") or meta.get("filename", "Документ")
            clause = self._normalize_clause(meta.get("clause"))
            answer = frag["text"]
            if clause and clause not in ("", "-1"):
                answer += f"\n\n📚 Источник: {src}\n📍 Пункт: п. {clause}"
            else:
                answer += f"\n\n📚 Источник: {src}"
            self._cache.set(cache_key, answer)
            return answer
        
        # 5. Генерация через LLM
        req_gost = self._extract_gost_from_query(query_lower)
        req_clause = self._extract_clause_from_query(query_lower)
        
        context_parts = []
        seen = set()
        for i, frag in enumerate(fragments[:5], 1):
            meta = frag.get("metadata", {})
            src = meta.get("standard_number") or meta.get("filename", "Документ")
            clause = self._normalize_clause(meta.get("clause", ""))
            clause_str = f" (п. {clause})" if clause and clause != "-1" else ""
            key = (src, clause)
            if key not in seen:
                context_parts.append(f"[{i}] {src}{clause_str}:\n{frag['text'].strip()}")
                seen.add(key)
        
        context_text = "\n\n".join(context_parts)
        
        try:
            response = self.ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Контекст:\n{context_text}\n\nВопрос: {query}"}
                ],
                options={"temperature": 0.1, "num_predict": 2048}
            )
            generated_answer = response["message"]["content"].strip()
            
            refusal_phrases = ["нет информации", "информация отсутствует", "не могу ответить", "в контексте нет"]
            
            # 🔥 ПРОВЕРКА НА ОТКАЗ — сразу возвращаем фрагменты
            if any(p in generated_answer.lower() for p in refusal_phrases) or len(generated_answer) < 30:
                logger.warning("⚠️ Модель отказалась, возвращаю фрагменты")
                
                answer_parts = []
                sources = set()
                
                for frag in fragments[:3]:
                    text = frag['text'].strip()
                    if len(text) > 1000:
                        text = text[:1000] + "..."
                    answer_parts.append(text)
                    
                    meta = frag.get('metadata', {})
                    src = meta.get('standard_number') or meta.get('filename', 'Документ')
                    clause = self._normalize_clause(meta.get('clause'))
                    if src:
                        if clause and clause != "-1":
                            sources.add(f"{src}, п. {clause}")
                        else:
                            sources.add(src)
                
                answer = "\n\n---\n\n".join(answer_parts)
                if sources:
                    answer += f"\n\n📚 Источники: {'; '.join(sources)}"
                
                self._cache.set(cache_key, answer)
                return answer
            
            # Добавляем источник, если его нет
            if "📚 Источник:" not in generated_answer:
                sources = set()
                for frag in fragments[:3]:
                    meta = frag.get("metadata", {})
                    src = meta.get("standard_number") or meta.get("filename")
                    clause = self._normalize_clause(meta.get("clause"))
                    if src:
                        clause_str = f", п. {clause}" if clause and clause != "-1" else ""
                        sources.add(f"{src}{clause_str}")
                if sources:
                    generated_answer += f"\n\n📚 Источник: {'; '.join(sources)}"
            
            self._cache.set(cache_key, generated_answer)
            return generated_answer
            
        except Exception as e:
            logger.error(f"❌ Ollama ошибка: {e}")
            
            # 🔥 FALLBACK: возвращаем фрагменты
            if fragments:
                answer_parts = []
                sources = set()
                
                for frag in fragments[:3]:
                    text = frag['text'].strip()
                    if len(text) > 1000:
                        text = text[:1000] + "..."
                    answer_parts.append(text)
                    
                    meta = frag.get('metadata', {})
                    src = meta.get('standard_number') or meta.get('filename', 'Документ')
                    clause = self._normalize_clause(meta.get('clause'))
                    if src:
                        if clause and clause != "-1":
                            sources.add(f"{src}, п. {clause}")
                        else:
                            sources.add(src)
                
                answer = "\n\n---\n\n".join(answer_parts)
                if sources:
                    answer += f"\n\n📚 Источники: {'; '.join(sources)}"
            else:
                answer = "В предоставленных документах нет информации"
            
            self._cache.set(cache_key, answer)
            return answer

    # -------------------------------------------------------------------------
    # 📊 СТАТИСТИКА
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict:
        return {
            "total_queries": self._session_stats["queries"],
            "cache_hits": self._session_stats["cache_hits"],
            "cache_hit_rate": round(
                self._session_stats["cache_hits"] / max(1, self._session_stats["queries"]) * 100, 1
            )
        }
    
    def clear_cache(self):
        self._cache.clear()
        logger.info("🧹 Кэш очищен")