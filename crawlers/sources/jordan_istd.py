"""
Jordan ISTD (Income and Sales Tax Department) Crawler
Crawls official e-invoicing news from istd.gov.jo
Jordan's e-invoicing system is called "JoFotara"
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article


class JordanISTDCrawler(BaseCrawler):
    """Crawler for Jordan Income and Sales Tax Department - JoFotara e-invoicing"""

    @property
    def source_id(self) -> str:
        return "jordan-istd"

    @property
    def source_name(self) -> str:
        return "Jordan ISTD"

    @property
    def source_type(self) -> str:
        return "official"

    @property
    def base_url(self) -> str:
        return "https://www.istd.gov.jo"

    @property
    def region(self) -> str:
        return "middle-east"

    @property
    def country(self) -> str:
        return "JO"

    @property
    def country_name(self) -> str:
        return "Jordan"

    def crawl(self) -> List[Dict]:
        """Crawl Jordan ISTD news and announcements"""
        articles = []

        # ISTD URLs - both English and Arabic
        urls_to_crawl = [
            f"{self.base_url}/en/NewsPage",
            f"{self.base_url}/en/news",
            f"{self.base_url}/ar/NewsPage",
            f"{self.base_url}/English/Pages/News.aspx",
            f"{self.base_url}/Arabic/Pages/News.aspx",
            "https://jofotara.gov.jo/en/news",
            "https://jofotara.gov.jo/ar/news",
        ]

        for page_url in urls_to_crawl:
            html_content = self.fetch_page(page_url)
            if not html_content:
                continue

            soup = self.parse_html(html_content)

            # Try various common selectors for news items
            selectors = [
                'article',
                '.news-item',
                '.news-card',
                '.announcement',
                '[class*="news"]',
                '[class*="announcement"]',
                '.card',
                '.list-item',
                '.entry',
                '.post',
                'table tr',
                '.ms-rtestate-field',  # SharePoint
            ]

            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found and len(found) > 1:
                    items = found
                    break

            # If no structured items, look for links
            if not items:
                links = soup.select('a[href]')
                for link in links[:30]:
                    try:
                        text = clean_text(link.get_text())
                        href = link.get('href', '')

                        if not text or len(text) < 15:
                            continue

                        if href.startswith(('javascript:', '#', 'mailto:')):
                            continue

                        keywords = [
                            'invoice', 'e-invoice', 'einvoice', 'jofotara', 'فاتورة',
                            'tax', 'vat', 'sales tax', 'income tax',
                            'electronic', 'digital', 'compliance', 'mandate',
                            'registration', 'update', 'news', 'announcement',
                        ]

                        if not any(kw in text.lower() for kw in keywords):
                            continue

                        url = href if href.startswith('http') else f"{self.base_url}{href}"

                        article_id = generate_article_id(self.source_id, url, datetime.utcnow())
                        categories = categorize_article(text, text)

                        article = self.create_article(
                            article_id=article_id,
                            title=text,
                            summary=f"Official update from Jordan ISTD: {text}",
                            url=url,
                            categories=categories,
                            published_at=datetime.utcnow()
                        )

                        if not any(a['title'] == text for a in articles):
                            articles.append(article)

                    except Exception:
                        continue
                continue

            # Process structured items
            for item in items[:20]:
                try:
                    if item.select_one('th'):
                        continue

                    title_elem = item.select_one('a, h2, h3, h4, .title, td:first-child')
                    if not title_elem:
                        continue

                    title = clean_text(title_elem.get_text())
                    if not title or len(title) < 10:
                        continue

                    link = item.select_one('a[href]')
                    url = page_url
                    if link:
                        href = link.get('href', '')
                        if href and not href.startswith(('javascript:', '#', 'mailto:')):
                            url = href if href.startswith('http') else f"{self.base_url}{href}"

                    summary_elem = item.select_one('p, .summary, .description, .excerpt')
                    summary = title
                    if summary_elem:
                        summary_text = clean_text(summary_elem.get_text())
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text

                    date_elem = item.select_one('time, .date, [class*="date"], td:last-child')
                    published_at = datetime.utcnow()
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text()
                        parsed = parse_date(date_text)
                        if parsed:
                            published_at = parsed

                    keywords = [
                        'invoice', 'e-invoice', 'einvoice', 'jofotara',
                        'tax', 'vat', 'electronic', 'compliance',
                        'mandate', 'registration', 'b2b', 'b2c',
                    ]

                    content_lower = (title + ' ' + summary).lower()
                    if not any(kw in content_lower for kw in keywords):
                        continue

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

                    if not any(a['title'] == title for a in articles):
                        articles.append(article)

                except Exception:
                    continue

        return articles
