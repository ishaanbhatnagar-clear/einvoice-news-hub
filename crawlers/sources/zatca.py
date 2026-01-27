"""
ZATCA (Saudi Arabia) News Crawler
Crawls news from the Zakat, Tax and Customs Authority website
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article, is_einvoice_related


class ZATCACrawler(BaseCrawler):
    """Crawler for ZATCA (Zakat, Tax and Customs Authority) Saudi Arabia"""

    @property
    def source_id(self) -> str:
        return "zatca"

    @property
    def source_name(self) -> str:
        return "ZATCA"

    @property
    def source_type(self) -> str:
        return "official"

    @property
    def base_url(self) -> str:
        return "https://zatca.gov.sa"

    @property
    def region(self) -> str:
        return "middle-east"

    @property
    def country(self) -> str:
        return "SA"

    @property
    def country_name(self) -> str:
        return "Saudi Arabia"

    def crawl(self) -> List[Dict]:
        """Crawl ZATCA news page"""
        articles = []

        # ZATCA English news page
        news_url = f"{self.base_url}/en/MediaCenter/News/Pages/default.aspx"
        html_content = self.fetch_page(news_url)

        if not html_content:
            return articles

        soup = self.parse_html(html_content)

        # Find news items - ZATCA uses SharePoint-style lists
        news_items = soup.select('.news-item, .ms-rtestate-field, .news-list-item, [class*="news"]')

        # Also try common news selectors
        if not news_items:
            news_items = soup.select('article, .item, .post, li[class*="news"]')

        for item in news_items[:20]:  # Limit to 20 most recent
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
                if link:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = f"{self.base_url}{url}"
                else:
                    continue

                # Extract date
                date_elem = item.select_one('.date, time, [class*="date"], span[class*="time"]')
                published_at = None
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.get_text()
                    published_at = parse_date(date_text)

                if not published_at:
                    published_at = datetime.utcnow()

                # Extract summary
                summary_elem = item.select_one('.summary, .description, .excerpt, p')
                summary = ""
                if summary_elem:
                    summary = clean_text(summary_elem.get_text())[:300]

                if not summary:
                    summary = title

                # Check if e-invoice related
                if not is_einvoice_related(title, summary):
                    # For ZATCA, include all tax-related news
                    keywords = ['tax', 'vat', 'zakat', 'customs', 'invoice', 'e-invoice', 'fatoorah']
                    if not any(kw in (title + summary).lower() for kw in keywords):
                        continue

                # Generate ID and categorize
                article_id = generate_article_id(self.source_id, url, published_at)
                categories = categorize_article(title, summary)

                article = self.create_article(
                    article_id=article_id,
                    title=title,
                    summary=summary,
                    url=url,
                    categories=categories,
                    published_at=published_at
                )

                articles.append(article)

            except Exception as e:
                continue

        return articles
