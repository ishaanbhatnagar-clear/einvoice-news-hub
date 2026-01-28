"""
Base crawler class for all source crawlers
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limit: 10 requests per minute per crawler
CALLS_PER_MINUTE = 10
RATE_PERIOD = 60


class BaseCrawler(ABC):
    """Abstract base class for all source crawlers"""

    # Default headers to mimic a browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this source"""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this source"""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Type of source: official, advisory, vendor, social"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the source"""
        pass

    @property
    def region(self) -> str:
        """Default region for articles from this source"""
        return "global"

    @property
    def country(self) -> Optional[str]:
        """Default country code for articles from this source"""
        return None

    @property
    def country_name(self) -> Optional[str]:
        """Default country name for articles from this source"""
        return None

    @sleep_and_retry
    @limits(calls=CALLS_PER_MINUTE, period=RATE_PERIOD)
    def fetch_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch a page with rate limiting

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object"""
        return BeautifulSoup(html_content, 'lxml')

    @abstractmethod
    def crawl(self) -> List[Dict]:
        """
        Crawl the source and return list of articles

        Returns:
            List of article dictionaries with structure:
            {
                'id': str,
                'title': str,
                'summary': str,
                'url': str,
                'source': {'id': str, 'name': str, 'type': str},
                'region': str,
                'country': str or None,
                'countryName': str or None,
                'categories': List[str],
                'publishedAt': str (ISO format),
                'crawledAt': str (ISO format)
            }
        """
        pass

    def create_article(
        self,
        article_id: str,
        title: str,
        summary: str,
        url: str,
        categories: List[str],
        published_at: datetime,
        region: str = None,
        country: str = None,
        country_name: str = None
    ) -> Dict:
        """Create a standardized article dictionary"""
        return {
            'id': article_id,
            'title': title,
            'summary': summary,
            'url': url,
            'source': {
                'id': self.source_id,
                'name': self.source_name,
                'type': self.source_type
            },
            'region': region or self.region,
            'country': country or self.country,
            'countryName': country_name or self.country_name,
            'categories': categories,
            'publishedAt': published_at.isoformat() if published_at else datetime.utcnow().isoformat(),
            'crawledAt': datetime.utcnow().isoformat()
        }

    def is_valid_url(self, url: str) -> bool:
        """
        Validate that a URL is properly formed and usable.
        Rejects javascript:, mailto:, tel:, and malformed URLs.
        """
        if not url:
            return False

        # Check for invalid schemes
        invalid_prefixes = ('javascript:', 'mailto:', 'tel:', '#', 'void(')
        if any(url.lower().startswith(prefix) or prefix in url.lower() for prefix in invalid_prefixes):
            return False

        # Parse and validate URL structure
        try:
            parsed = urlparse(url)
            # Must have a valid scheme and netloc
            if parsed.scheme not in ('http', 'https'):
                return False
            if not parsed.netloc or '.' not in parsed.netloc:
                return False
            return True
        except Exception:
            return False

    def safe_crawl(self) -> List[Dict]:
        """Wrapper around crawl with error handling and URL validation"""
        try:
            articles = self.crawl()
            # Filter out articles with invalid URLs
            valid_articles = []
            for article in articles:
                if self.is_valid_url(article.get('url', '')):
                    valid_articles.append(article)
                else:
                    logger.warning(f"{self.source_name}: Skipping article with invalid URL: {article.get('url', 'N/A')}")

            logger.info(f"{self.source_name}: Found {len(valid_articles)} valid articles (filtered {len(articles) - len(valid_articles)} invalid)")
            return valid_articles
        except Exception as e:
            logger.error(f"{self.source_name}: Crawl failed - {e}")
            return []
