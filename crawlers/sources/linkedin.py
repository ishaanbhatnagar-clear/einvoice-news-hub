"""
LinkedIn Company Posts Crawler
Uses Playwright for browser automation to scrape company posts
Requires LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables
"""

import os
import re
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright, Page, Browser
from utils import clean_text, generate_article_id, categorize_article, is_einvoice_related

logger = logging.getLogger(__name__)

# Company pages to crawl
COMPANY_PAGES = [
    {
        'slug': 'e-invoice-app',
        'name': 'e-invoice-app',
        'url': 'https://www.linkedin.com/company/e-invoice-app/posts/'
    },
    # Add more company pages here as needed
    # {
    #     'slug': 'avalaborations',
    #     'name': 'Avalara',
    #     'url': 'https://www.linkedin.com/company/avalara/posts/'
    # },
]


class LinkedInCrawler:
    """Crawler for LinkedIn company posts using Playwright"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logged_in = False

    @property
    def source_id(self) -> str:
        return "linkedin"

    @property
    def source_name(self) -> str:
        return "LinkedIn"

    @property
    def source_type(self) -> str:
        return "social"

    def _get_credentials(self) -> tuple:
        """Get LinkedIn credentials from environment variables"""
        email = os.environ.get('LINKEDIN_EMAIL')
        password = os.environ.get('LINKEDIN_PASSWORD')

        if not email or not password:
            logger.warning("LinkedIn credentials not found in environment variables")
            logger.warning("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD to enable LinkedIn crawling")
            return None, None

        return email, password

    def _login(self, page: Page, email: str, password: str) -> bool:
        """Log in to LinkedIn"""
        try:
            logger.info("Logging in to LinkedIn...")

            # Go to login page
            page.goto('https://www.linkedin.com/login', wait_until='networkidle')
            time.sleep(2)

            # Fill credentials
            page.fill('#username', email)
            page.fill('#password', password)

            # Click login button
            page.click('button[type="submit"]')

            # Wait for navigation
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # Check if login was successful
            if 'feed' in page.url or 'mynetwork' in page.url or 'company' in page.url:
                logger.info("LinkedIn login successful")
                return True

            # Check for security challenge
            if 'checkpoint' in page.url or 'challenge' in page.url:
                logger.warning("LinkedIn security challenge detected - manual intervention may be required")
                return False

            logger.warning(f"LinkedIn login may have failed. Current URL: {page.url}")
            return False

        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False

    def _parse_relative_time(self, time_str: str) -> datetime:
        """Parse LinkedIn's relative time strings like '2h', '3d', '1w'"""
        now = datetime.utcnow()

        if not time_str:
            return now

        time_str = time_str.lower().strip()

        # Match patterns like "2h", "3d", "1w", "2mo"
        match = re.match(r'(\d+)\s*([hdwmo]+)', time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit == 'h':
                return now - timedelta(hours=value)
            elif unit == 'd':
                return now - timedelta(days=value)
            elif unit == 'w':
                return now - timedelta(weeks=value)
            elif unit in ('mo', 'm'):
                return now - timedelta(days=value * 30)

        # Check for "Just now" or "now"
        if 'now' in time_str or 'just' in time_str:
            return now

        return now

    def _extract_posts(self, page: Page, company_slug: str, company_name: str) -> List[Dict]:
        """Extract posts from a company page"""
        posts = []

        try:
            # Wait for posts to load
            page.wait_for_selector('[data-urn*="activity"], .feed-shared-update-v2, .update-components-actor', timeout=10000)
            time.sleep(2)

            # Scroll to load more posts
            for _ in range(3):
                page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(1)

            # Find all post containers
            post_selectors = [
                '[data-urn*="activity"]',
                '.feed-shared-update-v2',
                '.occludable-update',
            ]

            post_elements = []
            for selector in post_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    post_elements = elements
                    break

            logger.info(f"Found {len(post_elements)} posts on {company_name} page")

            for i, post_elem in enumerate(post_elements[:15]):  # Limit to 15 posts
                try:
                    # Extract post text
                    text_selectors = [
                        '.feed-shared-text',
                        '.update-components-text',
                        '.break-words',
                        'span[dir="ltr"]'
                    ]

                    post_text = ""
                    for selector in text_selectors:
                        text_elem = post_elem.query_selector(selector)
                        if text_elem:
                            post_text = text_elem.inner_text()
                            if post_text and len(post_text) > 20:
                                break

                    if not post_text or len(post_text) < 20:
                        continue

                    post_text = clean_text(post_text)

                    # Extract time
                    time_selectors = [
                        '.update-components-actor__sub-description',
                        'time',
                        '.feed-shared-actor__sub-description',
                        'span.visually-hidden'
                    ]

                    time_str = ""
                    for selector in time_selectors:
                        time_elem = post_elem.query_selector(selector)
                        if time_elem:
                            time_str = time_elem.inner_text()
                            if re.search(r'\d+[hdwmo]', time_str.lower()):
                                break

                    published_at = self._parse_relative_time(time_str)

                    # Extract post URL
                    post_url = f"https://www.linkedin.com/company/{company_slug}/posts/"
                    link_elem = post_elem.query_selector('a[href*="activity"]')
                    if link_elem:
                        href = link_elem.get_attribute('href')
                        if href:
                            post_url = href if href.startswith('http') else f"https://www.linkedin.com{href}"

                    # Create title from first line or truncate
                    title = post_text.split('\n')[0][:100]
                    if len(title) < len(post_text):
                        title = title.rstrip('.') + '...'

                    summary = post_text[:300]
                    if len(post_text) > 300:
                        summary = summary.rstrip('.') + '...'

                    # Check if e-invoice related
                    if not is_einvoice_related(title, summary):
                        continue

                    # Generate ID and categorize
                    article_id = generate_article_id('linkedin', post_url, published_at)
                    categories = categorize_article(title, summary)

                    post = {
                        'id': article_id,
                        'title': title,
                        'summary': summary,
                        'url': post_url,
                        'source': {
                            'id': 'linkedin',
                            'name': f'LinkedIn ({company_name})',
                            'type': 'social'
                        },
                        'region': 'global',
                        'country': None,
                        'countryName': 'Global',
                        'categories': categories,
                        'publishedAt': published_at.isoformat(),
                        'crawledAt': datetime.utcnow().isoformat()
                    }

                    posts.append(post)
                    logger.info(f"Extracted post: {title[:50]}...")

                except Exception as e:
                    logger.debug(f"Failed to extract post {i}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to extract posts from {company_name}: {e}")

        return posts

    def crawl(self) -> List[Dict]:
        """Crawl LinkedIn company posts"""
        articles = []

        # Get credentials
        email, password = self._get_credentials()
        if not email or not password:
            logger.warning("Skipping LinkedIn crawl - no credentials provided")
            return articles

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )

                # Create context with realistic viewport
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = context.new_page()

                # Login
                if not self._login(page, email, password):
                    logger.error("Failed to login to LinkedIn")
                    browser.close()
                    return articles

                # Crawl each company page
                for company in COMPANY_PAGES:
                    try:
                        logger.info(f"Crawling LinkedIn page: {company['name']}")

                        page.goto(company['url'], wait_until='networkidle')
                        time.sleep(3)

                        posts = self._extract_posts(page, company['slug'], company['name'])
                        articles.extend(posts)

                        logger.info(f"LinkedIn ({company['name']}): Found {len(posts)} e-invoice related posts")

                        # Rate limiting between pages
                        time.sleep(2)

                    except Exception as e:
                        logger.error(f"Failed to crawl {company['name']}: {e}")
                        continue

                browser.close()

        except Exception as e:
            logger.error(f"LinkedIn crawl failed: {e}")

        return articles

    def safe_crawl(self) -> List[Dict]:
        """Wrapper around crawl with error handling"""
        try:
            articles = self.crawl()
            logger.info(f"LinkedIn: Found {len(articles)} articles")
            return articles
        except Exception as e:
            logger.error(f"LinkedIn: Crawl failed - {e}")
            return []
