"""
Pagero Regulatory Atlas Crawler
Crawls country-specific e-invoicing compliance information from pagero.com
"""

from typing import List, Dict
from datetime import datetime

from sources.base import BaseCrawler
from utils import clean_text, generate_article_id, categorize_article


# Middle East countries to crawl
MIDDLE_EAST_COUNTRIES = [
    ('saudi-arabia', 'SA', 'Saudi Arabia'),
    ('united-arab-emirates', 'AE', 'UAE'),
    ('egypt', 'EG', 'Egypt'),
    ('bahrain', 'BH', 'Bahrain'),
    ('oman', 'OM', 'Oman'),
    ('qatar', 'QA', 'Qatar'),
    ('jordan', 'JO', 'Jordan'),
    ('kuwait', 'KW', 'Kuwait'),
]

EUROPE_COUNTRIES = [
    ('germany', 'DE', 'Germany'),
    ('france', 'FR', 'France'),
    ('italy', 'IT', 'Italy'),
    ('spain', 'ES', 'Spain'),
    ('poland', 'PL', 'Poland'),
    ('belgium', 'BE', 'Belgium'),
    ('portugal', 'PT', 'Portugal'),
    ('greece', 'GR', 'Greece'),
    ('romania', 'RO', 'Romania'),
    ('croatia', 'HR', 'Croatia'),
]

REGION_MAPPING = {
    'SA': 'middle-east', 'AE': 'middle-east', 'EG': 'middle-east',
    'BH': 'middle-east', 'OM': 'middle-east', 'QA': 'middle-east',
    'JO': 'middle-east', 'KW': 'middle-east',
    'DE': 'europe', 'FR': 'europe', 'IT': 'europe', 'ES': 'europe',
    'PL': 'europe', 'BE': 'europe', 'PT': 'europe', 'GR': 'europe',
    'RO': 'europe', 'HR': 'europe',
}


class PageroAtlasCrawler(BaseCrawler):
    """Crawler for Pagero Regulatory Atlas - Country compliance pages"""

    @property
    def source_id(self) -> str:
        return "pagero-atlas"

    @property
    def source_name(self) -> str:
        return "Pagero Regulatory Atlas"

    @property
    def source_type(self) -> str:
        return "vendor"

    @property
    def base_url(self) -> str:
        return "https://www.pagero.com"

    def crawl(self) -> List[Dict]:
        """Crawl Pagero country compliance pages"""
        articles = []

        # Prioritize Middle East countries
        countries_to_crawl = MIDDLE_EAST_COUNTRIES + EUROPE_COUNTRIES

        for slug, country_code, country_name in countries_to_crawl:
            try:
                page_url = f"{self.base_url}/compliance/regulatory-updates/{slug}"
                html_content = self.fetch_page(page_url)

                if not html_content:
                    continue

                soup = self.parse_html(html_content)

                # Extract main content
                content_selectors = [
                    '.content-main',
                    'main',
                    '.page-content',
                    'article',
                    '[class*="content"]',
                ]

                main_content = None
                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

                if not main_content:
                    main_content = soup

                # Extract page title
                title_elem = main_content.select_one('h1, .page-title, .title')
                title = f"{country_name} E-Invoicing Compliance Update"
                if title_elem:
                    title_text = clean_text(title_elem.get_text())
                    if title_text:
                        title = title_text

                # Extract summary from first paragraphs
                paragraphs = main_content.select('p')
                summary_parts = []
                for p in paragraphs[:3]:
                    text = clean_text(p.get_text())
                    if text and len(text) > 30:
                        summary_parts.append(text)
                        if len(' '.join(summary_parts)) > 200:
                            break

                summary = ' '.join(summary_parts)[:300]
                if not summary:
                    summary = f"E-invoicing regulatory updates and compliance requirements for {country_name}"

                # Extract key dates/deadlines if present
                deadline_keywords = ['deadline', 'effective', 'mandatory', 'january', 'july', '2026', '2027']
                has_deadline = any(kw in summary.lower() for kw in deadline_keywords)

                # Generate article
                region = REGION_MAPPING.get(country_code, 'global')
                article_id = generate_article_id(self.source_id, page_url, datetime.utcnow())

                categories = ['compliance', 'regulation']
                if has_deadline:
                    categories.append('deadline')

                article = self.create_article(
                    article_id=article_id,
                    title=title,
                    summary=summary if summary else title,
                    url=page_url,
                    categories=categories,
                    published_at=datetime.utcnow(),
                    region=region,
                    country=country_code,
                    country_name=country_name
                )

                articles.append(article)

            except Exception:
                continue

        return articles
