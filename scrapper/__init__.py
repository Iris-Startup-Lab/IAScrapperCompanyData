"""Scrapper package exports.

Modules:
- fetcher: DuckDuckGo-based scraping and fetch utilities
- cleaner: HTML cleaning utilities (Cloudflare email decoding, extractor)
- text_utils: text cleaning utilities (emoji and decorative phrase removal)
"""

from .fetcher import DuckDuckGoScraper
from .cleaner import HtmlCleaner
from .text_utils import TextCleaner, find_string_in_html

__all__ = ["DuckDuckGoScraper", "HtmlCleaner", "TextCleaner", "find_string_in_html"]
