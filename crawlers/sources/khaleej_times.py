"""
Khaleej Times Crawler
Crawls business and tax news from khaleejtimes.com
One of the oldest English-language newspapers in the UAE
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article


class KhaleejTimesCrawler(BaseCrawler):
    """Crawler for Khaleej Times - UAE business and tax news"""

    @property
    def source_id(self) -> str:
        return "khaleej-times"

    @property
    def source_name(self) -> str:
        return "Khaleej Times"

    @property
    def source_type(self) -> str:
        return "news"

    @property
    def base_url(self) -> str:
        return "https://www.khaleejtimes.com"

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
        """Crawl Khaleej Times for tax/invoice news"""
        articles = []

        urls_to_crawl = [
            f"{self.base_url}/business",
            f"{self.base_url}/uae",
            f"{self.base_url}/business/economy",
            f"{self.base_url}/business/corporate",
        ]

        for page_url in urls_to_crawl:
            html_content = self.fetch_page(page_url)
            if not html_content:
                continue

            soup = self.parse_html(html_content)

            selectors = [
                'article',
                '.article-card',
                '.story-card',
                '[class*="article"]',
                '[class*="story"]',
                '.listing-item',
                '.post-item',
                '.card',
            ]

            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found and len(found) > 2:
                    items = found
                    break

            for item in items[:25]:
                try:
                    title_elem = item.select_one('h2 a, h3 a, .headline a, a.title, a[class*="title"]')
                    if not title_elem:
                        title_elem = item.select_one('h2, h3, .headline, .title')
                    if not title_elem:
                        continue

                    title = clean_text(title_elem.get_text())
                    if not title or len(title) < 15:
                        continue

                    link = item.select_one('a[href]')
                    if not link:
                        continue
                    href = link.get('href', '')
                    if not href or href.startswith(('javascript:', '#', 'mailto:')):
                        continue
                    url = href if href.startswith('http') else f"{self.base_url}{href}"

                    # Filter for tax/invoice related content
                    tax_keywords = [
                        'tax', 'vat', 'invoice', 'e-invoice', 'excise',
                        'corporate tax', 'fta', 'compliance', 'filing',
                        'ministry of finance', 'zatca', 'customs',
                    ]
                    if not any(kw in title.lower() for kw in tax_keywords):
                        continue

                    summary_elem = item.select_one('p, .summary, .description, .excerpt, .teaser')
                    summary = title
                    if summary_elem:
                        summary_text = clean_text(summary_elem.get_text())
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text[:300]

                    date_elem = item.select_one('time, .date, [class*="date"], [class*="time"]')
                    published_at = datetime.utcnow()
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text()
                        parsed = parse_date(date_text)
                        if parsed:
                            published_at = parsed

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
