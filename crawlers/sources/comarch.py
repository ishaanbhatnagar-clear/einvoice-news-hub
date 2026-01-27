"""
Comarch Legal Regulation Changes Crawler
Crawls e-invoicing country updates from Comarch
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article

# Country detection
COUNTRY_KEYWORDS = {
    'SA': ['saudi', 'zatca'],
    'AE': ['uae', 'emirates'],
    'EG': ['egypt'],
    'DE': ['germany', 'german'],
    'FR': ['france', 'french'],
    'IT': ['italy', 'italian'],
    'ES': ['spain', 'spanish'],
    'PL': ['poland', 'polish', 'ksef'],
    'BE': ['belgium', 'belgian'],
    'BR': ['brazil', 'brazilian'],
    'MX': ['mexico', 'mexican'],
    'IN': ['india', 'indian'],
    'MY': ['malaysia'],
    'PH': ['philippines'],
}

REGION_MAPPING = {
    'SA': 'middle-east', 'AE': 'middle-east', 'EG': 'middle-east',
    'DE': 'europe', 'FR': 'europe', 'IT': 'europe', 'ES': 'europe',
    'PL': 'europe', 'BE': 'europe',
    'BR': 'americas', 'MX': 'americas',
    'IN': 'asia-pacific', 'MY': 'asia-pacific', 'PH': 'asia-pacific',
}

COUNTRY_NAMES = {
    'SA': 'Saudi Arabia', 'AE': 'UAE', 'EG': 'Egypt',
    'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
    'PL': 'Poland', 'BE': 'Belgium',
    'BR': 'Brazil', 'MX': 'Mexico',
    'IN': 'India', 'MY': 'Malaysia', 'PH': 'Philippines',
}


class ComarchCrawler(BaseCrawler):
    """Crawler for Comarch Legal Regulation Changes"""

    @property
    def source_id(self) -> str:
        return "comarch"

    @property
    def source_name(self) -> str:
        return "Comarch"

    @property
    def source_type(self) -> str:
        return "vendor"

    @property
    def base_url(self) -> str:
        return "https://www.comarch.com"

    def detect_country(self, title: str, summary: str) -> tuple:
        text = (title + ' ' + summary).lower()
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return (
                        country_code,
                        COUNTRY_NAMES.get(country_code),
                        REGION_MAPPING.get(country_code, 'global')
                    )
        return (None, 'Global', 'global')

    def crawl(self) -> List[Dict]:
        """Crawl Comarch legal regulation changes"""
        articles = []

        news_url = f"{self.base_url}/trade-and-services/data-management/legal-regulation-changes"
        html_content = self.fetch_page(news_url)

        if not html_content:
            return articles

        soup = self.parse_html(html_content)

        # Find article/news items
        selectors = [
            'article',
            '.news-item',
            '.regulation-item',
            '.card',
            '[class*="item"]',
            '.post',
        ]

        items = []
        for selector in selectors:
            found = soup.select(selector)
            if found and len(found) > 2:
                items = found
                break

        # Also try links in main content
        if not items:
            items = soup.select('a[href*="legal-regulation"], a[href*="e-invoicing"], a[href*="e-receipt"]')

        for item in items[:25]:
            try:
                # Extract title
                if item.name == 'a':
                    title = clean_text(item.get_text())
                    url = item.get('href', '')
                else:
                    title_elem = item.select_one('h2, h3, h4, a, .title')
                    if not title_elem:
                        continue
                    title = clean_text(title_elem.get_text())

                    link = item.select_one('a[href]')
                    url = link.get('href', '') if link else ''

                if not title or len(title) < 15:
                    continue

                if url and not url.startswith('http'):
                    url = f"{self.base_url}{url}"

                if not url:
                    continue

                # Extract date
                date_elem = item.select_one('.date, time, [class*="date"]') if item.name != 'a' else None
                published_at = datetime.utcnow()
                if date_elem:
                    parsed = parse_date(date_elem.get_text())
                    if parsed:
                        published_at = parsed

                # Extract summary
                summary = title
                if item.name != 'a':
                    summary_elem = item.select_one('p, .excerpt, .summary')
                    if summary_elem:
                        summary = clean_text(summary_elem.get_text())[:300]

                # Filter for e-invoicing content
                einvoice_keywords = ['e-invoice', 'einvoice', 'e-receipt', 'electronic invoice', 'vat', 'tax', 'mandate']
                if not any(kw in (title + summary).lower() for kw in einvoice_keywords):
                    continue

                # Detect country
                country_code, country_name, region = self.detect_country(title, summary)

                article_id = generate_article_id(self.source_id, url, published_at)
                categories = categorize_article(title, summary)

                article = self.create_article(
                    article_id=article_id,
                    title=title,
                    summary=summary,
                    url=url,
                    categories=categories,
                    published_at=published_at,
                    region=region,
                    country=country_code,
                    country_name=country_name
                )

                if not any(a['url'] == url for a in articles):
                    articles.append(article)

            except Exception:
                continue

        return articles
