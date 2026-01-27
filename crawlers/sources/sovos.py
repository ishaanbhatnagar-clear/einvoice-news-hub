"""
Sovos Blog Crawler
Crawls e-invoicing news from Sovos blog
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article, is_einvoice_related
from sources.ey import COUNTRY_KEYWORDS, REGION_MAPPING, COUNTRY_NAMES


class SovosCrawler(BaseCrawler):
    """Crawler for Sovos Blog"""

    @property
    def source_id(self) -> str:
        return "sovos"

    @property
    def source_name(self) -> str:
        return "Sovos"

    @property
    def source_type(self) -> str:
        return "vendor"

    @property
    def base_url(self) -> str:
        return "https://sovos.com"

    def detect_country(self, title: str, summary: str) -> tuple:
        text = (title + ' ' + summary).lower()
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return (country_code, COUNTRY_NAMES.get(country_code), REGION_MAPPING.get(country_code, 'global'))
        return (None, 'Global', 'global')

    def crawl(self) -> List[Dict]:
        articles = []

        # Sovos has multiple relevant sections
        urls_to_crawl = [
            f"{self.base_url}/blog/",
            f"{self.base_url}/regulatory-updates/",
            f"{self.base_url}/blog/vat/",
        ]

        for news_url in urls_to_crawl:
            html_content = self.fetch_page(news_url)

        if not html_content:
            return articles

        soup = self.parse_html(html_content)
        news_items = soup.select('.blog-post, .post, article, .card, [class*="blog"], [class*="post"]')

        for item in news_items[:25]:
            try:
                title_elem = item.select_one('h2, h3, h4, .title, a')
                if not title_elem:
                    continue

                title = clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue

                link = item.select_one('a[href]')
                url = link.get('href', '') if link else ''
                if url and not url.startswith('http'):
                    url = f"{self.base_url}{url}"
                if not url:
                    continue

                date_elem = item.select_one('.date, time, [class*="date"]')
                published_at = parse_date(date_elem.get('datetime') or date_elem.get_text()) if date_elem else datetime.utcnow()

                summary_elem = item.select_one('.summary, .excerpt, p')
                summary = clean_text(summary_elem.get_text())[:300] if summary_elem else title

                if not is_einvoice_related(title, summary):
                    continue

                country_code, country_name, region = self.detect_country(title, summary)
                article_id = generate_article_id(self.source_id, url, published_at)
                categories = categorize_article(title, summary)

                articles.append(self.create_article(
                    article_id=article_id, title=title, summary=summary, url=url,
                    categories=categories, published_at=published_at,
                    region=region, country=country_code, country_name=country_name
                ))
            except Exception:
                continue

        return articles
