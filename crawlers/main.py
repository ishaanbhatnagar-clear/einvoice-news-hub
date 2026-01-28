#!/usr/bin/env python3
"""
eInvoice News Crawler - Main Orchestrator
Runs all configured crawlers and updates the news.json data file
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sources import (
    ZATCACrawler,
    EYCrawler,
    AvalaraCrawler,
    PageroCrawler,
    EDICOMCrawler,
    VertexCrawler,
    SovosCrawler,
    LinkedInCrawler,
    VATUpdateCrawler,
    UAEFTACrawler,
    PageroAtlasCrawler,
    ComarchCrawler,
    EgyptETACrawler,
    OmanOTACrawler,
    JordanISTDCrawler,
    BahrainNBRCrawler,
    QatarGTACrawler,
)
from utils import merge_with_existing, deduplicate_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
NEWS_FILE = DATA_DIR / 'news.json'

# Crawler configurations
CRAWLERS = [
    # News Aggregators (HIGH VALUE)
    VATUpdateCrawler,

    # Official Government Sources - Middle East
    ZATCACrawler,        # Saudi Arabia
    UAEFTACrawler,       # UAE
    EgyptETACrawler,     # Egypt
    OmanOTACrawler,      # Oman
    JordanISTDCrawler,   # Jordan
    BahrainNBRCrawler,   # Bahrain
    QatarGTACrawler,     # Qatar

    # Advisory (Big 4)
    EYCrawler,

    # Vendors with Compliance Content
    PageroAtlasCrawler,
    EDICOMCrawler,
    VertexCrawler,
    SovosCrawler,
    ComarchCrawler,

    # Other Vendors (may be blocked)
    AvalaraCrawler,
    PageroCrawler,

    # Social
    LinkedInCrawler,
]


def load_existing_news() -> Dict:
    """Load existing news data from file"""
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load existing news: {e}")

    return {
        'lastUpdated': None,
        'crawlStatus': 'unknown',
        'totalArticles': 0,
        'articles': []
    }


def save_news(news_data: Dict) -> None:
    """Save news data to file"""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {news_data['totalArticles']} articles to {NEWS_FILE}")


def run_crawler(crawler_class) -> List[Dict]:
    """Run a single crawler and return articles"""
    crawler = crawler_class()
    return crawler.safe_crawl()


def run_all_crawlers() -> List[Dict]:
    """Run all crawlers in parallel and collect articles"""
    all_articles = []

    # Use ThreadPoolExecutor for parallel crawling
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all crawlers
        future_to_crawler = {
            executor.submit(run_crawler, crawler): crawler
            for crawler in CRAWLERS
        }

        # Collect results as they complete
        for future in as_completed(future_to_crawler):
            crawler = future_to_crawler[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
                logger.info(f"{crawler.__name__}: Collected {len(articles)} articles")
            except Exception as e:
                logger.error(f"{crawler.__name__}: Failed - {e}")

    return all_articles


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("eInvoice News Crawler - Starting")
    logger.info("=" * 60)

    start_time = datetime.utcnow()
    crawl_status = 'success'

    try:
        # Load existing news
        existing_data = load_existing_news()
        existing_articles = existing_data.get('articles', [])
        logger.info(f"Loaded {len(existing_articles)} existing articles")

        # Run all crawlers
        new_articles = run_all_crawlers()
        logger.info(f"Crawled {len(new_articles)} new articles")

        # Merge and deduplicate
        merged_articles = merge_with_existing(
            new_articles,
            existing_articles,
            max_articles=500  # Keep last 500 articles
        )
        logger.info(f"After deduplication: {len(merged_articles)} articles")

        # Prepare output data
        news_data = {
            'lastUpdated': datetime.utcnow().isoformat() + 'Z',
            'crawlStatus': crawl_status,
            'totalArticles': len(merged_articles),
            'articles': merged_articles
        }

        # Save to file
        save_news(news_data)

    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        crawl_status = 'failed'

        # Save error status
        news_data = load_existing_news()
        news_data['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
        news_data['crawlStatus'] = crawl_status
        save_news(news_data)

        sys.exit(1)

    # Summary
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"Crawl completed in {elapsed:.1f} seconds")
    logger.info(f"Status: {crawl_status}")
    logger.info(f"Total articles: {news_data['totalArticles']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
