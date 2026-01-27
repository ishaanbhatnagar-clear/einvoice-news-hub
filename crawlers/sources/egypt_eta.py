"""
Egypt ETA (E-Invoicing Tax Authority) Crawler
Crawls official e-invoicing news from invoicing.eta.gov.eg
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article


class EgyptETACrawler(BaseCrawler):
    """Crawler for Egypt's E-Invoicing Tax Authority portal"""

    @property
    def source_id(self) -> str:
        return "egypt-eta"

    @property
    def source_name(self) -> str:
        return "Egypt ETA"

    @property
    def source_type(self) -> str:
        return "official"

    @property
    def base_url(self) -> str:
        return "https://invoicing.eta.gov.eg"

    @property
    def region(self) -> str:
        return "middle-east"

    @property
    def country(self) -> str:
        return "EG"

    @property
    def country_name(self) -> str:
        return "Egypt"

    def crawl(self) -> List[Dict]:
        """Crawl Egypt ETA e-invoicing portal"""
        articles = []

        # ETA has multiple potential news/updates URLs
        urls_to_crawl = [
            self.base_url,
            f"{self.base_url}/news",
            f"{self.base_url}/updates",
            f"{self.base_url}/announcements",
            "https://www.eta.gov.eg/en/news",
            "https://www.eta.gov.eg/ar/news",
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
                '.announcement',
                '.update-item',
                '[class*="news"]',
                '[class*="announcement"]',
                '.card',
                '.list-item',
                'table tr',
                '.post',
            ]

            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found and len(found) > 1:
                    items = found
                    break

            # If no structured items found, try to extract from any visible text
            if not items:
                # Look for any links with relevant keywords
                links = soup.select('a[href]')
                for link in links[:30]:
                    try:
                        text = clean_text(link.get_text())
                        href = link.get('href', '')

                        if not text or len(text) < 15:
                            continue

                        # Filter for relevant content
                        einvoice_keywords = [
                            'invoice', 'e-invoice', 'einvoice', 'فاتورة',
                            'tax', 'vat', 'electronic', 'digital',
                            'compliance', 'mandate', 'registration',
                            'update', 'news', 'announcement', 'deadline',
                        ]

                        if not any(kw in text.lower() for kw in einvoice_keywords):
                            continue

                        url = href if href.startswith('http') else f"{self.base_url}{href}"

                        article_id = generate_article_id(self.source_id, url, datetime.utcnow())
                        categories = categorize_article(text, text)

                        article = self.create_article(
                            article_id=article_id,
                            title=text,
                            summary=f"Official update from Egypt Tax Authority: {text}",
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
                    # Skip header rows
                    if item.select_one('th'):
                        continue

                    # Extract title
                    title_elem = item.select_one('a, h2, h3, h4, .title, td:first-child')
                    if not title_elem:
                        continue

                    title = clean_text(title_elem.get_text())
                    if not title or len(title) < 10:
                        continue

                    # Extract URL
                    link = item.select_one('a[href]')
                    url = page_url
                    if link:
                        href = link.get('href', '')
                        if href:
                            url = href if href.startswith('http') else f"{self.base_url}{href}"

                    # Extract summary
                    summary_elem = item.select_one('p, .summary, .description, .excerpt')
                    summary = title
                    if summary_elem:
                        summary_text = clean_text(summary_elem.get_text())
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text

                    # Extract date
                    date_elem = item.select_one('time, .date, [class*="date"], td:last-child')
                    published_at = datetime.utcnow()
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text()
                        parsed = parse_date(date_text)
                        if parsed:
                            published_at = parsed

                    # Filter for e-invoice/tax related content
                    einvoice_keywords = [
                        'invoice', 'e-invoice', 'einvoice', 'فاتورة',
                        'tax', 'vat', 'electronic', 'compliance',
                        'mandate', 'registration', 'b2b', 'b2c',
                    ]

                    content_lower = (title + ' ' + summary).lower()
                    if not any(kw in content_lower for kw in einvoice_keywords):
                        continue

                    # Generate article
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
