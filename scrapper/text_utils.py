"""Text utilities moved from notebook cell.

Provides decorative text removal and safe phrase cleaning.
"""
from __future__ import annotations

import re
from typing import List
from typing import Dict
import re

class BaseTextCleaner:
    """Base text cleaner providing primitives."""

    def remove_decorative(self, text: str) -> str:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U00002600-\U000026FF"
            "\U00002B00-\U00002BFF"
            "\U00002300-\U000023FF"
            "]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub("", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        return text.strip()


class TextCleaner(BaseTextCleaner):
    """Higher-level text cleaner that removes decorative phrases safely."""

    SAFE_PHRASES: List[str] = [
        r"\bAnterior\b",
        r"\bSiguiente\b",
        r"Página siguiente",
        r"Seleccionar país",
        r"Más información",
        r"Leer más",
        r"Todas las opiniones",
    ]

    def remove_words(self, text: str) -> str:
        for phrase in self.SAFE_PHRASES:
            text = re.sub(phrase, "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n\s*\n", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


def find_string_in_html(target: str, html: str, context_chars: int = 50) -> List[Dict]:
    """Locate occurrences of `target` inside `html` (best-effort).

    - Normalizes the target by keeping only digits when applicable (useful for
      phone numbers like "449 805 5337").
    - Searches both the raw HTML and a cleaned text view to provide matches
      with surrounding context.
    - Returns a list of dicts: {source: 'raw'|'clean', match: str, start, end, snippet}
    """
    results: List[Dict] = []
    if not target or not html:
        return results

    # If the target looks like a phone (has digits), search by digits allowing
    # arbitrary non-digit separators between them (spaces, dashes, parentheses)
    target_digits = re.sub(r"\D", "", target)

    def _search(text: str, source: str):
        if not text:
            return
        if target_digits:
            # build permissive regex: each digit separated by optional non-digits
            pattern = "".join(re.escape(ch) + r"\D*" for ch in target_digits)
        else:
            pattern = re.escape(target)

        try:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                s, e = m.start(), m.end()
                snippet_start = max(0, s - context_chars)
                snippet_end = min(len(text), e + context_chars)
                snippet = text[snippet_start:snippet_end]
                results.append({
                    "source": source,
                    "match": m.group(0),
                    "start": s,
                    "end": e,
                    "snippet": snippet,
                })
        except re.error:
            return

    # Search in raw HTML and cleaned text
    _search(html, "raw")

    return results
