"""
Utility modules for the eInvoice News Crawler
"""

from .parser import (
    clean_text,
    extract_text_from_html,
    parse_date,
    extract_summary,
    extract_date,
    generate_article_id,
    categorize_article,
    is_einvoice_related
)

from .deduplicator import (
    compute_content_hash,
    compute_title_similarity,
    deduplicate_articles,
    merge_with_existing
)

__all__ = [
    'clean_text',
    'extract_text_from_html',
    'parse_date',
    'extract_summary',
    'extract_date',
    'generate_article_id',
    'categorize_article',
    'is_einvoice_related',
    'compute_content_hash',
    'compute_title_similarity',
    'deduplicate_articles',
    'merge_with_existing'
]
