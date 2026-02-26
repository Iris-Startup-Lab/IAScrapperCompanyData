"""HTML cleaning utilities moved from notebook cell.

Contains Cloudflare email decoding and HTML extraction into normalized text.
"""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, Comment


class BaseCleaner:
    """Base cleaner with Cloudflare email decoding."""

    @staticmethod
    def decode_cloudflare_email(cfemail: str) -> str:
        try:
            n = int(cfemail[:2], 16)
            return "".join(chr(int(cfemail[i:i+2], 16) ^ n) for i in range(2, len(cfemail), 2))
        except Exception:
            return ""


class HtmlCleaner(BaseCleaner):
    """Cleaner that strips scripts, decodes protected emails and extracts meaningful text."""

    def clean_html(self, html: str) -> str:
        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Remove scripts, styles, noscript and comments
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # 2. Decode Cloudflare emails
        for tag in soup.find_all(attrs={"data-cfemail": True}):
            decoded = self.decode_cloudflare_email(tag["data-cfemail"])
            if decoded:
                tag.string = decoded

        for a in soup.find_all("a", href=True):
            if "/cdn-cgi/l/email-protection#" in a["href"]:
                encoded_hash = a["href"].split("#")[-1]
                real_email = self.decode_cloudflare_email(encoded_hash)
                if real_email:
                    a["href"] = f"mailto:{real_email}"
                    a.string = real_email

        # 3. Remove hidden elements
        for hidden in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
            hidden.decompose()

        # 4. Extract meaningful content
        lines = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "a"]):
            text = elem.get_text(" ", strip=True)
            if not text:
                continue
            text = re.sub(r"\s+", " ", text)
            if len(text) < 3:
                continue
            if elem.name == "a" and elem.has_attr("href"):
                href = elem["href"].strip()
                if href not in text:
                    text = f"{text}: {href}"
            lines.append(text)

        # 5. Normalize whitespace
        texto = "\n".join(lines)
        texto = texto.replace("\xa0", " ")
        texto = re.sub(r"\n\s*\n", "\n", texto)
        texto = re.sub(r"[ \t]+", " ", texto)

        # 6. Smart deduplication
        seen = set()
        dedup_lines = []
        for line in texto.split("\n"):
            line = line.strip()
            if not line:
                continue
            normalized_key = re.sub(r":\s*(https?://|/).*?$", "", line).strip().lower()
            if normalized_key not in seen:
                seen.add(normalized_key)
                dedup_lines.append(line)

        return "\n".join(dedup_lines)
