"""
Zawya (Reuters) Crawler
Crawls MENA business and tax news from zawya.com
Part of Refinitiv/Reuters - major MENA financial news source
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article


class ZawyaCrawler(BaseCrawler):
    """Crawler for Zawya - MENA financial and tax news"""

    @property
    def source_id(self) -> str:
        return "zawya"

    @property
    def source_name(self) -> str:
        return "Zawya"

    @property
    def source_type(self) -> str:
        return "news"

    @property
    def base_url(self) -> str:
        return "https://www.zawya.com"

    @property
    def region(self) -> str:
        return "middle-east"

    @property
    def country(self) -> str:
        return None  # Covers MENA region

    @property
    def country_name(self) -> str:
        return "MENA"

    def crawl(self) -> List[Dict]:
        """Crawl Zawya for tax/invoice news"""
        articles = []

        urls_to_crawl = [
            f"{self.base_url}/mena/en/economy",
            f"{self.base_url}/mena/en/business",
            f"{self.base_url}/saudi-arabia/en/economy",
            f"{self.base_url}/uae/en/economy",
            f"{self.base_url}/mena/en/legal",
        ]

        for page_url in urls_to_crawl:
            html_content = self.fetch_page(page_url)
            if not html_content:
                continue

            soup = self.parse_html(html_content)

            selectors = [
                'article',
                '.article-card',
                '.story-item',
                '[class*="article"]',
                '[class*="story"]',
                '.news-item',
                '.card',
            ]

            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found and len(found) > 2:
                    items = found
                    break

            # Also try finding links directly
            if not items:
                items = soup.select('a[href*="/story/"]')

            for item in items[:25]:
                try:
                    if item.name == 'a':
                        title = clean_text(item.get_text())
                        href = item.get('href', '')
                    else:
                        title_elem = item.select_one('h2 a, h3 a, .headline a, a.title')
                        if not title_elem:
                            title_elem = item.select_one('h2, h3, .headline')
                        if not title_elem:
                            continue
                        title = clean_text(title_elem.get_text())
                        link = item.select_one('a[href]')
                        href = link.get('href', '') if link else ''

                    if not title or len(title) < 15:
                        continue

                    if not href or href.startswith(('javascript:', '#', 'mailto:')):
                        continue
                    url = href if href.startswith('http') else f"{self.base_url}{href}"

                    # Filter for tax/invoice related content
                    tax_keywords = ['tax', 'vat', 'invoice', 'excise', 'compliance', 'fta', 'zatca', 'zakat', 'customs']
                    if not any(kw in title.lower() for kw in tax_keywords):
                        continue

                    summary_elem = item.select_one('p, .summary, .description, .excerpt') if item.name != 'a' else None
                    summary = title
                    if summary_elem:
                        summary_text = clean_text(summary_elem.get_text())
                        if summary_text and len(summary_text) > 20:
                            summary = summary_text[:300]

                    date_elem = item.select_one('time, .date, [class*="date"]') if item.name != 'a' else None
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
