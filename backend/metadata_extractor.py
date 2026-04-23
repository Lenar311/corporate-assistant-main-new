# metadata_extractor.py

import re
from typing import Dict

def extract_metadata(text: str, filename: str) -> Dict[str, str]:
    if not filename:
        filename = ""
    
    metadata = {
        "filename": filename,
        "doc_type": "unknown",
        "standard_number": "",
        "date": "",
        "section": "",
        "page": ""
    }

    # Определяем тип документа
    fn_lower = filename.lower()
    if "гост" in fn_lower:
        metadata["doc_type"] = "ГОСТ"
    elif "сп" in fn_lower:
        metadata["doc_type"] = "СП"

    # 🔥 Извлекаем номер ГОСТ из имени файла (приоритет!)
    gost_match = re.search(r'(ГОСТ\s*[Рр]?\s*[\d\.\-]+(?:-\d{4})?)', filename, re.IGNORECASE)
    if gost_match:
        metadata["standard_number"] = gost_match.group(1).strip()
    else:
        # Если не нашли в имени — пробуем в тексте
        for pattern in [r'ГОСТ\s*[Рр]?\s*[\d\.\-]+(?:-\d{4})?']:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                metadata["standard_number"] = match.group(0).strip()
                break

    return metadata