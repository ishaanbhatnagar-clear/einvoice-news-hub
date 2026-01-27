"""
VATupdate News Crawler
Crawls e-invoicing news from vatupdate.com - a leading VAT/e-invoicing news aggregator
"""

from typing import List, Dict
from datetime import datetime, timedelta
import re

from sources.base import BaseCrawler
from utils import clean_text, parse_date, generate_article_id, categorize_article

# Country detection keywords for VATupdate articles
COUNTRY_KEYWORDS = {
    # Middle East
    'SA': ['saudi', 'zatca', 'ksa', 'fatoorah'],
    'AE': ['uae', 'emirates', 'dubai', 'fta '],
    'EG': ['egypt', 'egyptian', 'eta '],
    'BH': ['bahrain'],
    'OM': ['oman'],
    'QA': ['qatar'],
    'KW': ['kuwait'],
    'JO': ['jordan'],
    # Europe
    'EU': ['european union', 'eu ', 'vida', 'european commission'],
    'DE': ['germany', 'german', 'xrechnung', 'zugferd'],
    'FR': ['france', 'french', 'chorus pro', 'factur-x'],
    'IT': ['italy', 'italian', 'sdi '],
    'ES': ['spain', 'spanish', 'verifactu', 'ticketbai'],
    'PL': ['poland', 'polish', 'ksef'],
    'BE': ['belgium', 'belgian'],
    'NL': ['netherlands', 'dutch'],
    'PT': ['portugal', 'portuguese', 'saf-t'],
    'GR': ['greece', 'greek', 'mydata'],
    'RO': ['romania', 'romanian'],
    'HR': ['croatia', 'croatian'],
    # Americas
    'BR': ['brazil', 'brazilian', 'nf-e', 'nfe'],
    'MX': ['mexico', 'mexican', 'cfdi'],
    'CL': ['chile', 'chilean', 'dte'],
    'CO': ['colombia', 'colombian', 'dian'],
    'AR': ['argentina'],
    # Asia-Pacific
    'IN': ['india', 'indian', 'gst', 'gstn'],
    'AU': ['australia', 'australian'],
    'SG': ['singapore'],
    'MY': ['malaysia', 'myinvois'],
    'VN': ['vietnam'],
    'PH': ['philippines', 'eis'],
    'CN': ['china', 'chinese', 'fapiao'],
    # Africa
    'KE': ['kenya', 'kenyan', 'tims'],
    'NG': ['nigeria', 'nigerian'],
    'ZA': ['south africa'],
}

REGION_MAPPING = {
    'SA': 'middle-east', 'AE': 'middle-east', 'EG': 'middle-east',
    'BH': 'middle-east', 'OM': 'middle-east', 'QA': 'middle-east',
    'KW': 'middle-east', 'JO': 'middle-east',
    'EU': 'europe', 'DE': 'europe', 'FR': 'europe', 'IT': 'europe',
    'ES': 'europe', 'PL': 'europe', 'BE': 'europe', 'NL': 'europe',
    'PT': 'europe', 'GR': 'europe', 'RO': 'europe', 'HR': 'europe',
    'BR': 'americas', 'MX': 'americas', 'CL': 'americas',
    'CO': 'americas', 'AR': 'americas',
    'IN': 'asia-pacific', 'AU': 'asia-pacific', 'SG': 'asia-pacific',
    'MY': 'asia-pacific', 'VN': 'asia-pacific', 'PH': 'asia-pacific',
    'CN': 'asia-pacific',
    'KE': 'africa', 'NG': 'africa', 'ZA': 'africa',
}

COUNTRY_NAMES = {
    'SA': 'Saudi Arabia', 'AE': 'UAE', 'EG': 'Egypt', 'BH': 'Bahrain',
    'OM': 'Oman', 'QA': 'Qatar', 'KW': 'Kuwait', 'JO': 'Jordan',
    'EU': 'European Union', 'DE': 'Germany', 'FR': 'France', 'IT': 'Italy',
    'ES': 'Spain', 'PL': 'Poland', 'BE': 'Belgium', 'NL': 'Netherlands',
    'PT': 'Portugal', 'GR': 'Greece', 'RO': 'Romania', 'HR': 'Croatia',
    'BR': 'Brazil', 'MX': 'Mexico', 'CL': 'Chile', 'CO': 'Colombia', 'AR': 'Argentina',
    'IN': 'India', 'AU': 'Australia', 'SG': 'Singapore', 'MY': 'Malaysia',
    'VN': 'Vietnam', 'PH': 'Philippines', 'CN': 'China',
    'KE': 'Kenya', 'NG': 'Nigeria', 'ZA': 'South Africa',
}


class VATUpdateCrawler(BaseCrawler):
    """Crawler for VATupdate - Daily VAT/e-invoicing news aggregator"""

    @property
    def source_id(self) -> str:
        return "vatupdate"

    @property
    def source_name(self) -> str:
        return "VATupdate"

    @property
    def source_type(self) -> str:
        return "aggregator"

    @property
    def base_url(self) -> str:
        return "https://www.vatupdate.com"

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

    def parse_relative_time(self, time_str: str) -> datetime:
        """Parse relative time strings like '2 hours ago', '1 day ago'"""
        now = datetime.utcnow()
        time_str = time_str.lower().strip()

        patterns = [
            (r'(\d+)\s*hour', 'hours'),
            (r'(\d+)\s*day', 'days'),
            (r'(\d+)\s*week', 'weeks'),
            (r'(\d+)\s*month', 'months'),
            (r'(\d+)\s*min', 'minutes'),
        ]

        for pattern, unit in patterns:
            match = re.search(pattern, time_str)
            if match:
                value = int(match.group(1))
                if unit == 'minutes':
                    return now - timedelta(minutes=value)
                elif unit == 'hours':
                    return now - timedelta(hours=value)
                elif unit == 'days':
                    return now - timedelta(days=value)
                elif unit == 'weeks':
                    return now - timedelta(weeks=value)
                elif unit == 'months':
                    return now - timedelta(days=value * 30)

        return now

    def crawl(self) -> List[Dict]:
        """Crawl VATupdate homepage and e-invoicing category"""
        articles = []

        urls_to_crawl = [
            self.base_url,
            f"{self.base_url}/category/e-invoicing-e-reporting/",
        ]

        for page_url in urls_to_crawl:
            html_content = self.fetch_page(page_url)
            if not html_content:
                continue

            soup = self.parse_html(html_content)

            # VATupdate uses WordPress with article cards
            article_selectors = [
                'article',
                '.post',
                '.entry',
                '.blog-post',
                '[class*="post-"]',
            ]

            post_elements = []
            for selector in article_selectors:
                elements = soup.select(selector)
                if elements:
                    post_elements = elements
                    break

            for post in post_elements[:30]:
                try:
                    # Extract title
                    title_elem = post.select_one('h2 a, h3 a, .entry-title a, .post-title a')
                    if not title_elem:
                        title_elem = post.select_one('h2, h3, .title')

                    if not title_elem:
                        continue

                    title = clean_text(title_elem.get_text())
                    if not title or len(title) < 15:
                        continue

                    # Extract URL
                    link = title_elem if title_elem.name == 'a' else post.select_one('a[href]')
                    url = ""
                    if link and link.get('href'):
                        url = link.get('href')
                        if not url.startswith('http'):
                            url = f"{self.base_url}{url}"

                    if not url or 'vatupdate.com' not in url:
                        continue

                    # Extract date
                    date_elem = post.select_one('time, .date, .post-date, .entry-date, [class*="time"]')
                    published_at = datetime.utcnow()
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text()
                        if 'ago' in date_str.lower():
                            published_at = self.parse_relative_time(date_str)
                        else:
                            parsed = parse_date(date_str)
                            if parsed:
                                published_at = parsed

                    # Extract summary/excerpt
                    summary_elem = post.select_one('.excerpt, .entry-summary, .post-excerpt, p')
                    summary = title
                    if summary_elem:
                        summary_text = clean_text(summary_elem.get_text())
                        if len(summary_text) > 30:
                            summary = summary_text[:300] + '...' if len(summary_text) > 300 else summary_text

                    # Filter for e-invoicing related content
                    einvoice_keywords = [
                        'e-invoice', 'einvoice', 'e-invoicing', 'electronic invoice',
                        'digital reporting', 'e-reporting', 'ctc', 'real-time reporting',
                        'vat reporting', 'tax digitalization', 'vida',
                    ]

                    text_lower = (title + ' ' + summary).lower()
                    if not any(kw in text_lower for kw in einvoice_keywords):
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

                    # Avoid duplicates
                    if not any(a['url'] == url for a in articles):
                        articles.append(article)

                except Exception as e:
                    continue

        return articles
