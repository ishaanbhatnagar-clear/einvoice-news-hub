"""
UAE Federal Tax Authority Crawler
Crawls official announcements from tax.gov.ae
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article


class UAEFTACrawler(BaseCrawler):
    """Crawler for UAE Federal Tax Authority announcements"""

    @property
    def source_id(self) -> str:
        return "uae-fta"

    @property
    def source_name(self) -> str:
        return "UAE FTA"

    @property
    def source_type(self) -> str:
        return "official"

    @property
    def base_url(self) -> str:
        return "https://tax.gov.ae"

    @property
    def region(self) -> str:
        return "middle-east"

    @property
    def country(self) -> str:
        return "AE"

    @property
    def country_name(self) -> str:
        return "UAE"

    def crawl(self) -> List[Dict]:
        """Crawl UAE FTA announcements page"""
        articles = []

        urls_to_crawl = [
            f"{self.base_url}/en/announcements.aspx",
            f"{self.base_url}/en/news.aspx",
        ]

        for page_url in urls_to_crawl:
            html_content = self.fetch_page(page_url)
            if not html_content:
                continue

            soup = self.parse_html(html_content)

            # FTA uses table-based or list-based announcements
            selectors = [
                'table tr',
                '.announcement-item',
                '.news-item',
                'article',
                '.list-item',
                '[class*="announcement"]',
                '[class*="news"]',
            ]

            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found and len(found) > 1:
                    items = found
                    break

            for item in items[:20]:
                try:
                    # Skip header rows
                    if item.select_one('th'):
                        continue

                    # Extract title from link or text
                    title_elem = item.select_one('a, td:first-child, .title, h3, h4')
                    if not title_elem:
                        continue

                    title = clean_text(title_elem.get_text())
                    if not title or len(title) < 10:
                        continue

                    # Extract URL
                    link = item.select_one('a[href]')
                    url = ""
                    if link:
                        href = link.get('href', '')
                        # Skip javascript: links and other invalid hrefs
                        if href and not href.startswith(('javascript:', '#', 'mailto:')):
                            url = href if href.startswith('http') else f"{self.base_url}{href}"

                    if not url:
                        url = page_url

                    # Extract date
                    date_elem = item.select_one('time, .date, td:last-child, [class*="date"]')
                    published_at = datetime.utcnow()
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text()
                        parsed = parse_date(date_text)
                        if parsed:
                            published_at = parsed

                    # Filter for tax/invoice related content
                    tax_keywords = [
                        'vat', 'tax', 'invoice', 'e-invoice', 'einvoice',
                        'excise', 'corporate', 'return', 'refund', 'compliance',
                        'registration', 'deadline', 'penalty', 'fta',
                    ]

                    if not any(kw in title.lower() for kw in tax_keywords):
                        continue

                    # Generate article
                    article_id = generate_article_id(self.source_id, url, published_at)
                    categories = categorize_article(title, title)

                    article = self.create_article(
                        article_id=article_id,
                        title=title,
                        summary=title,  # FTA announcements are usually title-only
                        url=url,
                        categories=categories,
                        published_at=published_at
                    )

                    if not any(a['title'] == title for a in articles):
                        articles.append(article)

                except Exception:
                    continue

        return articles
