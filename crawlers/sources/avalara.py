"""
Avalara Blog Crawler
Crawls e-invoicing news from Avalara blog
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article, is_einvoice_related
from sources.ey import COUNTRY_KEYWORDS, REGION_MAPPING, COUNTRY_NAMES


class AvalaraCrawler(BaseCrawler):
    """Crawler for Avalara Blog"""

    @property
    def source_id(self) -> str:
        return "avalara"

    @property
    def source_name(self) -> str:
        return "Avalara"

    @property
    def source_type(self) -> str:
        return "vendor"

    @property
    def base_url(self) -> str:
        return "https://www.avalara.com"

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
        """Crawl Avalara blog"""
        articles = []

        news_url = f"{self.base_url}/blog/en/north-america"
        html_content = self.fetch_page(news_url)

        if not html_content:
            return articles

        soup = self.parse_html(html_content)

        # Find blog posts
        news_items = soup.select('.blog-post, .post, article, .card, [class*="blog"]')

        for item in news_items[:25]:
            try:
                # Extract title
                title_elem = item.select_one('h2, h3, h4, .title, a[class*="title"]')
                if not title_elem:
                    continue

                title = clean_text(title_elem.get_text())
                if not title or len(title) < 10:
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
                date_elem = item.select_one('.date, time, [class*="date"]')
                published_at = None
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.get_text()
                    published_at = parse_date(date_text)

                if not published_at:
                    published_at = datetime.utcnow()

                # Extract summary
                summary = ""
                summary_elem = item.select_one('.summary, .excerpt, p, [class*="desc"]')
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

            except Exception:
                continue

        return articles
