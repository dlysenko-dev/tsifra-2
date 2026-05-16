#!/usr/bin/env python3
"""
Test IntelWorker v2 — real data sources
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.intel_worker import IntelWorker


async def test_intel():
    """Test IntelWorker with real data fetchers."""
    print("=" * 60)
    print("Testing IntelWorker v2 — Real Data Sources")
    print("=" * 60)

    worker = IntelWorker(llm_router=None)

    # Test 1: HackerNews
    print("\n1. Fetching HackerNews top stories...")
    from agents.intel_worker import _HNFetcher
    hn = _HNFetcher()
    items = await hn.fetch_top(limit=5)
    print(f"   Fetched: {len(items)} items")
    for i, item in enumerate(items[:3], 1):
        print(f"   {i}. [{item.score}] {item.title[:60]}...")

    # Test 2: Reddit
    print("\n2. Fetching Reddit r/technology...")
    from agents.intel_worker import _RedditFetcher
    reddit = _RedditFetcher()
    items = await reddit.fetch_subreddit("technology", limit=5)
    print(f"   Fetched: {len(items)} items")
    for i, item in enumerate(items[:3], 1):
        print(f"   {i}. [{item.score}] {item.title[:60]}...")

    # Test 3: RSS
    print("\n3. Fetching RSS feeds...")
    from agents.intel_worker import _RSSFetcher
    rss = _RSSFetcher()
    items = await rss.fetch_default_feeds(limit=3)
    print(f"   Fetched: {len(items)} items")
    for i, item in enumerate(items[:3], 1):
        print(f"   {i}. [{item.source}] {item.title[:60]}...")

    # Test 4: Full trend analysis
    print("\n4. Running analyze_trends()...")
    result = await worker.analyze_trends({"topic": "AI automation"})
    print(f"   Type: {result['type']}")
    print(f"   Items: {result['raw_report']['items_count']}")
    print(f"   Sources: {result['raw_report']['sources_used']}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_intel())
