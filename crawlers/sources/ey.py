"""
EY Tax Alerts Crawler
Crawls tax news and alerts from EY website
"""

from typing import List, Dict, Optional
from datetime import datetime
import re

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article, is_einvoice_related


# Country mapping for EY articles based on keywords
COUNTRY_KEYWORDS = {
    'SA': ['saudi', 'zatca', 'kingdom of saudi arabia', 'ksa'],
    'AE': ['uae', 'emirates', 'dubai', 'abu dhabi', 'fta'],
    'EG': ['egypt', 'egyptian'],
    'BH': ['bahrain', 'bahraini'],
    'OM': ['oman', 'omani'],
    'QA': ['qatar', 'qatari'],
    'KW': ['kuwait', 'kuwaiti'],
    'JO': ['jordan', 'jordanian'],
    'EU': ['european union', 'eu ', 'vida', 'european commission'],
    'DE': ['germany', 'german', 'xrechnung'],
    'FR': ['france', 'french', 'chorus pro'],
    'IT': ['italy', 'italian', 'sdi '],
    'ES': ['spain', 'spanish', 'sii ', 'ticketbai'],
    'PL': ['poland', 'polish', 'ksef'],
    'IN': ['india', 'indian', 'gst', 'gstn'],
    'BR': ['brazil', 'brazilian', 'nf-e', 'nfe'],
    'MX': ['mexico', 'mexican', 'cfdi'],
}

REGION_MAPPING = {
    'SA': 'middle-east', 'AE': 'middle-east', 'EG': 'middle-east',
    'BH': 'middle-east', 'OM': 'middle-east', 'QA': 'middle-east',
    'KW': 'middle-east', 'JO': 'middle-east',
    'EU': 'europe', 'DE': 'europe', 'FR': 'europe', 'IT': 'europe',
    'ES': 'europe', 'PL': 'europe',
    'IN': 'asia-pacific',
    'BR': 'americas', 'MX': 'americas',
}

COUNTRY_NAMES = {
    'SA': 'Saudi Arabia', 'AE': 'UAE', 'EG': 'Egypt',
    'BH': 'Bahrain', 'OM': 'Oman', 'QA': 'Qatar',
    'KW': 'Kuwait', 'JO': 'Jordan',
    'EU': 'European Union', 'DE': 'Germany', 'FR': 'France',
    'IT': 'Italy', 'ES': 'Spain', 'PL': 'Poland',
    'IN': 'India', 'BR': 'Brazil', 'MX': 'Mexico',
}


class EYCrawler(BaseCrawler):
    """Crawler for EY Tax Alerts"""

    @property
    def source_id(self) -> str:
        return "ey"

    @property
    def source_name(self) -> str:
        return "EY"

    @property
    def source_type(self) -> str:
        return "advisory"

    @property
    def base_url(self) -> str:
        return "https://www.ey.com"

    def detect_country(self, title: str, summary: str) -> tuple:
        """Detect country from article content"""
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
        """Crawl EY tax alerts"""
        articles = []

        # EY tax alerts page
        urls_to_try = [
            f"{self.base_url}/en_gl/tax/tax-alerts",
            f"{self.base_url}/en_us/insights/tax"
        ]

        for news_url in urls_to_try:
            html_content = self.fetch_page(news_url)
            if html_content:
                break
        else:
            return articles

        soup = self.parse_html(html_content)

        # Find article items
        article_selectors = [
            '.ey-card', '.article-card', '.insight-card',
            '[class*="card"]', 'article', '.item'
        ]

        news_items = []
        for selector in article_selectors:
            items = soup.select(selector)
            if items:
                news_items = items
                break

        for item in news_items[:30]:
            try:
                # Extract title
                title_elem = item.select_one('h2, h3, h4, .title, [class*="title"]')
                if not title_elem:
                    link = item.select_one('a[href]')
                    if link:
                        title_elem = link

                if not title_elem:
                    continue

                title = clean_text(title_elem.get_text())
                if not title or len(title) < 15:
                    continue

                # Extract URL
                link = item.select_one('a[href]')
                url = ""
                if link:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = f"{self.base_url}{url}"

                if not url:
                    continue

                # Extract date
                date_elem = item.select_one('.date, time, [class*="date"], [class*="time"]')
                published_at = None
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.get_text()
                    published_at = parse_date(date_text)

                if not published_at:
                    published_at = datetime.utcnow()

                # Extract summary
                summary = ""
                summary_elem = item.select_one('.summary, .description, .excerpt, p, [class*="desc"]')
                if summary_elem:
                    summary = clean_text(summary_elem.get_text())[:300]

                if not summary:
                    summary = title

                # Check if e-invoice related
                if not is_einvoice_related(title, summary):
                    continue

                # Detect country
                country_code, country_name, region = self.detect_country(title, summary)

                # Generate ID and categorize
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

                articles.append(article)

            except Exception as e:
                continue

        return articles
