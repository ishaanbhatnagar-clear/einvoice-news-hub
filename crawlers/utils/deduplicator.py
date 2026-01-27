"""
Deduplication utilities for the eInvoice News Crawler
"""

import hashlib
from typing import List, Dict
from difflib import SequenceMatcher


def compute_content_hash(title: str, url: str) -> str:
    """Compute a hash for detecting duplicate content"""
    content = f"{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.md5(content.encode()).hexdigest()


def compute_title_similarity(title1: str, title2: str) -> float:
    """Compute similarity ratio between two titles"""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def deduplicate_articles(articles: List[Dict], similarity_threshold: float = 0.85) -> List[Dict]:
    """
    Remove duplicate articles based on URL and title similarity

    Args:
        articles: List of article dictionaries
        similarity_threshold: Minimum similarity ratio to consider as duplicate (0-1)

    Returns:
        List of deduplicated articles
    """
    if not articles:
        return []

    seen_urls = set()
    seen_hashes = set()
    unique_articles = []

    for article in articles:
        url = article.get('url', '').lower().strip()
        title = article.get('title', '').strip()

        # Skip if URL already seen
        if url in seen_urls:
            continue

        # Compute content hash
        content_hash = compute_content_hash(title, url)

        # Skip if hash already seen
        if content_hash in seen_hashes:
            continue

        # Check title similarity with existing articles
        is_duplicate = False
        for existing in unique_articles:
            existing_title = existing.get('title', '').strip()
            if compute_title_similarity(title, existing_title) >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_urls.add(url)
            seen_hashes.add(content_hash)
            unique_articles.append(article)

    return unique_articles


def merge_with_existing(new_articles: List[Dict], existing_articles: List[Dict], max_articles: int = 500) -> List[Dict]:
    """
    Merge new articles with existing ones, removing duplicates

    Args:
        new_articles: Newly crawled articles
        existing_articles: Previously stored articles
        max_articles: Maximum number of articles to keep

    Returns:
        Merged and deduplicated article list
    """
    # Combine new and existing
    all_articles = new_articles + existing_articles

    # Deduplicate
    unique_articles = deduplicate_articles(all_articles)

    # Sort by published date (newest first)
    unique_articles.sort(
        key=lambda x: x.get('publishedAt', ''),
        reverse=True
    )

    # Limit to max articles
    return unique_articles[:max_articles]
