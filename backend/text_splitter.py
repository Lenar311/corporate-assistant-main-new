# text_splitter.py — утилиты для разбиения текста

import re
from typing import List


def _count_tokens(text: str) -> int:
    """
    Простая эвристика подсчёта токенов (1 токен ≈ 4 символа).
    Для точного подсчёта нужен токенизатор модели, но это достаточно для chunking.
    """
    return len(text) // 4


def simple_text_splitter(text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
    """
    Разбивает текст на перекрывающиеся чанки с учётом структуры документов.
    
    Args:
        text: Исходный текст
        chunk_size: Максимальный размер чанка в **символах** (рекомендуется 2048 для jina-embeddings-v3)
        overlap: Количество символов перекрытия между чанками
    
    Returns:
        Список чанков
    """
    if not text or len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Если это не последний чанк — ищем семантический разрыв
        if end < len(text):
            # Расширяем окно поиска вокруг конца чанка
            search_start = max(start, end - overlap)
            search_end = min(len(text), end + overlap)

            # Приоритет разрывов: заголовок нового раздела > конец предложения > абзац > пробел
            break_point = -1

            # 1. Ищем начало нового структурного элемента (ГОСТ/ЕСКД)
            # В simple_text_splitter, в списке приоритетов:
            struct_pattern = r'\n\s*(?:\d+(?:\.\d+)*[^\n]{0,100}|Приложение\s+[А-ЯA-Z]|Пункт\s+\d+|Раздел\s+[IVXLCDM\d]+|Глава\s+[IVXLCDM\d]+)\b'
            match = re.search(struct_pattern, text[search_start:search_end], re.IGNORECASE)
            if match:
                pos = search_start + match.start()
                if pos > start:  # Не разбивать в самом начале
                    break_point = pos

            # 2. Если не нашли — ищем конец предложения
            if break_point == -1:
                for match in re.finditer(r'[.!?]\s', text[search_start:search_end]):
                    pos = search_start + match.end()
                    if pos > end:
                        break_point = pos
                        break

            # 3. Если не нашли — ищем пустую строку (абзац)
            if break_point == -1:
                for match in re.finditer(r'\n\s*\n', text[search_start:search_end]):
                    pos = search_start + match.start()
                    if pos > end:
                        break_point = pos
                        break

            # 4. Если не нашли — ищем пробел
            if break_point == -1:
                for match in re.finditer(r'\s', text[search_start:search_end]):
                    pos = search_start + match.end()
                    if pos > end:
                        break_point = pos
                        break

            # Применяем найденный разрыв
            if break_point != -1 and break_point > start:
                end = break_point

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Сдвигаем начало следующего чанка
        next_start = end - overlap
        if next_start <= start:  # Избегаем бесконечного цикла
            next_start = end
        start = next_start

    return chunks