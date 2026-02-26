"""Fetcher module moved from notebook cell.

Provides OOP scraper implementation. Use DuckDuckGoScraper for main flow.
"""
from __future__ import annotations

import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


class BaseScraper:
    """Base scraper with shared utilities and regexes."""

    DUCKDUCKGO_URL = "https://duckduckgo.com/html/"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    KEYWORDS = [
        "email",
        "correo",
        "contacto",
        "phone",
        "telefono",
        "teléfono",
        "whatsapp",
        "wa.me",
        "tel:",
        "mailto:",
    ]

    BAD_URL_KEYWORDS = {
        "duckduckgo.com/y.js",
        "bing.com/aclick",
        "doubleclick",
        "ad_domain=",
    }

    SOCIAL_DOMAINS = {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "instagram.com",
        "www.instagram.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "linkedin.com",
    }

    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:com|mx|org|net|edu|info|biz|co|io)",
        re.IGNORECASE,
    )

    PHONE_REGEX = re.compile(r"\+?\d[\d\s\-\(\)]{6,}\d")

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(self.HEADERS)

    @staticmethod
    def extract_real_url(ddg_url: str) -> Optional[str]:
        if not ddg_url:
            return None
        if ddg_url.startswith("http"):
            return ddg_url
        parsed = urlparse(ddg_url)
        qs = parse_qs(parsed.query)
        return unquote(qs["uddg"][0]) if "uddg" in qs else None

    def is_bad_url(self, url: str) -> bool:
        if any(bad in url for bad in self.BAD_URL_KEYWORDS):
            return True
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if any(social in domain for social in self.SOCIAL_DOMAINS):
            return True
        return False

    @staticmethod
    def clean_number(text: str) -> str:
        return re.sub(r"\D", "", text)

    def is_valid_phone(self, number: str) -> bool:
        clean = self.clean_number(number)
        if len(clean) < 8 or len(clean) > 12:
            return False
        if len(clean) >= 13:
            return False
        if len(clean) >= 11 and clean.startswith(("16", "17")):
            return False
        if len(set(clean)) == 1:
            return False
        return True

    def detect_signals(self, html: str) -> Dict:
        lower_html = html.lower()
        found_keywords = [k for k in self.KEYWORDS if k in lower_html]
        email_strings = list(set(match.group(0) for match in self.EMAIL_REGEX.finditer(html)))
        phone_candidates = [match.group(0) for match in self.PHONE_REGEX.finditer(html)]
        phones = list(
            {
                self.clean_number(p)
                for p in phone_candidates
                if self.is_valid_phone(p)
            }
        )
        return {
            "keywords_found": found_keywords,
            "emails_found": email_strings,
            "phones_found": phones,
            "has_email": len(email_strings) > 0,
            "has_phone": len(phones) > 0,
        }

    def detect_framework(self, html: str) -> Dict:
        lower_html = html.lower()
        frameworks = {"react": False, "vue": False, "angular": False, "nextjs": False}
        if (
            "data-reactroot" in lower_html
            or "reactroot" in lower_html
            or "__react" in lower_html
            or "react-dom" in lower_html
            or re.search(r"<div[^>]+id=[\"\']root[\"\']", lower_html)
        ):
            frameworks["react"] = True
        if ("id=\"app\"" in lower_html or "data-v-" in lower_html or "vue.js" in lower_html or "vue.runtime" in lower_html):
            frameworks["vue"] = True
        if ("ng-app" in lower_html or "ng-version" in lower_html or "angular.js" in lower_html or "ng-" in lower_html):
            frameworks["angular"] = True
        if ("__next" in lower_html or "/_next/" in lower_html or "next.config" in lower_html):
            frameworks["nextjs"] = True

        soup = BeautifulSoup(html, "html.parser")
        body = soup.body
        meaningful_tags = 0
        if body:
            meaningful_tags = len(body.find_all(["p", "h1", "h2", "h3", "li"]))
        is_spa = any(frameworks.values())
        is_probably_html_normal = (not is_spa and meaningful_tags > 5)
        return {
            "frameworks_detected": [k for k, v in frameworks.items() if v],
            "is_spa_like": is_spa,
            "is_html_traditional": is_probably_html_normal,
        }


class DuckDuckGoScraper(BaseScraper):
    """Scraper that uses DuckDuckGo search and concurrent fetching."""

    def fetch_html(self, url: str) -> Optional[Dict]:
        try:
            time.sleep(random.uniform(1, 3))
            response = self.session.get(url, timeout=12)
            response.raise_for_status()
            html = response.content.decode("utf-8", errors="replace")
            signals = self.detect_signals(html)
            framework_info = self.detect_framework(html)
            return {"url": url, "size": len(html), "signals": signals, "framework": framework_info, "html": html}
        except Exception:
            return None

    def fetch_multiple(self, urls: List[str], max_workers: Optional[int] = None) -> List[Dict]:
        if not urls:
            return []
        if max_workers is None:
            max_workers = min(10, len(urls))
        results: List[Dict] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.fetch_html, url): url for url in urls}
            for future in tqdm(as_completed(future_to_url), total=len(future_to_url), desc="Descargando (concurrente)"):
                url = future_to_url[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                        print(f"\n✔ {url}")
                        print(f"Tamaño: {data['size']} bytes")
                        print("Señales encontradas:")
                        print(data["signals"])
                        print("Framework detectado:")
                        print(data["framework"])
                except Exception as e:
                    print(f"\n✖ Error descargando {url}: {e}")
        return results

    def main_search(self, query: str, n_sites: int = 5) -> List[Dict]:
        print(f"\n🔍 Buscando: {query}")
        print(f"📄 Recuperando resultados de DuckDuckGo (se solicitarán {n_sites} sitios)...\n")
        response = self.session.get(self.DUCKDUCKGO_URL, params={"q": query, "kl": "mx-es"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        raw_links = [self.extract_real_url(a.get("href")) for a in soup.select("a.result__a")]
        links: List[str] = []
        for link in raw_links:
            if link and not self.is_bad_url(link):
                links.append(link)
            if len(links) >= n_sites:
                break
        print(f"✅ Se encontraron {len(links)} enlaces válidos. Iniciando descargas en paralelo...\n")
        results = self.fetch_multiple(links)
        return results
