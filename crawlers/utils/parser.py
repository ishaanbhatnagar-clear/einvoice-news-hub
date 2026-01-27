"""
HTML parsing utilities for the eInvoice News Crawler
"""

import re
import html
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
import html2text
from dateutil import parser as date_parser


def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""

    # Unescape HTML entities
    text = html.unescape(text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def extract_text_from_html(html_content: str, max_length: int = 500) -> str:
    """Extract clean text from HTML content"""
    if not html_content:
        return ""

    # Convert HTML to text
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.ignore_emphasis = True

    text = h.handle(html_content)
    text = clean_text(text)

    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'

    return text


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string into datetime object"""
    if not date_str:
        return None

    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        return None


def extract_summary(soup: BeautifulSoup, selectors: list) -> str:
    """Extract summary text using multiple CSS selectors"""
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = clean_text(element.get_text())
            if len(text) > 50:  # Minimum length for a valid summary
                return text[:300] + '...' if len(text) > 300 else text

    return ""


def extract_date(soup: BeautifulSoup, selectors: list) -> Optional[datetime]:
    """Extract date using multiple CSS selectors"""
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            # Try datetime attribute first
            date_str = element.get('datetime') or element.get_text()
            parsed = parse_date(date_str)
            if parsed:
                return parsed

    return None


def generate_article_id(source_id: str, url: str, date: datetime = None) -> str:
    """Generate a unique article ID"""
    import hashlib

    # Use URL hash for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

    # Include date if available
    if date:
        date_str = date.strftime('%Y-%m-%d')
        return f"{source_id}-{date_str}-{url_hash}"

    return f"{source_id}-{url_hash}"


def categorize_article(title: str, summary: str) -> list:
    """Categorize article based on title and summary content"""
    text = (title + ' ' + summary).lower()
    categories = []

    # Keyword mapping for categories
    category_keywords = {
        'mandate': ['mandate', 'mandatory', 'required', 'obligation', 'compulsory'],
        'regulation': ['regulation', 'regulatory', 'law', 'legislation', 'directive', 'framework'],
        'deadline': ['deadline', 'due date', 'effective date', 'implementation date', 'timeline'],
        'partnership': ['partner', 'partnership', 'collaboration', 'alliance', 'joint'],
        'product': ['launch', 'release', 'new feature', 'solution', 'platform', 'tool', 'product'],
        'compliance': ['compliance', 'compliant', 'certified', 'certification', 'audit'],
        'expansion': ['expand', 'expansion', 'new office', 'new market', 'growth'],
        'update': ['update', 'change', 'modification', 'amendment', 'revision']
    }

    for category, keywords in category_keywords.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)

    # Default to 'update' if no categories found
    if not categories:
        categories = ['update']

    # Limit to 2 most relevant categories
    return categories[:2]


def is_einvoice_related(title: str, summary: str) -> bool:
    """Check if article is related to e-invoicing"""
    text = (title + ' ' + summary).lower()

    keywords = [
        'e-invoice', 'einvoice', 'e-invoicing', 'einvoicing',
        'electronic invoice', 'electronic invoicing',
        'e-receipt', 'digital invoice', 'tax invoice',
        'zatca', 'fatoorah', 'fta', 'vat', 'gst',
        'peppol', 'ubl', 'xrechnung', 'factur-x',
        'sdi', 'chorus pro', 'ksef', 'cfdi', 'nf-e',
        'b2b invoice', 'b2g invoice', 'clearance',
        'tax compliance', 'tax digitalization'
    ]

    return any(keyword in text for keyword in keywords)
