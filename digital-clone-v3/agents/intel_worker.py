"""
Intel Worker v3 — Real Data Sources
====================================
Razvedka s realnymi istochnikami:
- RSS lenty (TechCrunch, VentureBeat, ArsTechnica)
- HackerNews API (oficialnyy, besplatnyy)
- Reddit JSON API (besplatnyy, bez auth)
- Web scraping (bazovyy)

Integration:
- Rezultaty sobirayutsya i summariziruyutsya cherez LLM
- Podderzhka keshirovaniya dlya skorosti
- Fallback na LLM-only esli vse istochniki nedostupny
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("intel_worker")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class NewsItem:
    """Odna novostnaya zapis."""

    title: str
    url: str
    source: str
    published: Optional[str] = None
    summary: str = ""
    score: int = 0  # dlya HN — kolichestvo oches

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published,
            "summary": self.summary[:200] if self.summary else "",
            "score": self.score,
        }


@dataclass
class TrendReport:
    """Itogovyy otchet o trendah."""

    topic: str
    generated_at: str
    sources_used: List[str]
    items: List[NewsItem]
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "generated_at": self.generated_at,
            "sources_used": self.sources_used,
            "items_count": len(self.items),
            "items": [i.to_dict() for i in self.items[:20]],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------


class _HNFetcher:
    """HackerNews API client."""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    TOP_STORIES_URL = f"{{BASE_URL}}/topstories.json"
    ITEM_URL = f"{{BASE_URL}}/item/{{item_id}}.json"

    async def fetch_top(self, limit: int = 10) -> List[NewsItem]:
        """Fetch top stories from HN."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Get top story IDs
                resp = await client.get(self.TOP_STORIES_URL.format(BASE_URL=self.BASE_URL))
                resp.raise_for_status()
                story_ids = resp.json()[:limit * 2]  # berem s zapasom

                # 2. Fetch each story
                items: List[NewsItem] = []
                for story_id in story_ids[:limit]:
                    try:
                        item_resp = await client.get(
                            self.ITEM_URL.format(BASE_URL=self.BASE_URL, item_id=story_id)
                        )
                        item_resp.raise_for_status()
                        data = item_resp.json()
                        if data and data.get("title"):
                            items.append(NewsItem(
                                title=data["title"],
                                url=data.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                source="hackernews",
                                published=str(data.get("time", "")),
                                score=data.get("score", 0),
                            ))
                    except Exception as exc:
                        logger.debug("HN item fetch error: %s", exc)
                        continue

                return items
        except Exception as exc:
            logger.warning("HackerNews fetch failed: %s", exc)
            return []


class _RedditFetcher:
    """Reddit JSON API client (bez auth)."""

    async def fetch_subreddit(self, subreddit: str, limit: int = 10) -> List[NewsItem]:
        """Fetch hot posts from subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        headers = {"User-Agent": "JarvisBot/1.0 (DigitalClone)"}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                items: List[NewsItem] = []
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    if post.get("title"):
                        items.append(NewsItem(
                            title=post["title"],
                            url=f"https://reddit.com{post.get('permalink', '')}",
                            source=f"reddit/r/{subreddit}",
                            score=post.get("score", 0),
                        ))
                return items
        except Exception as exc:
            logger.warning("Reddit fetch failed: %s", exc)
            return []


class _RSSFetcher:
    """RSS feed fetcher."""

    DEFAULT_FEEDS = {
        "techcrunch": "https://techcrunch.com/feed/",
        "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
        "verge": "https://www.theverge.com/rss/index.xml",
    }

    async def fetch_feed(self, feed_url: str, limit: int = 10) -> List[NewsItem]:
        """Fetch and parse RSS feed."""
        try:
            import feedparser
            import httpx

            # Download feed
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()
                content = resp.text

            # Parse
            parsed = feedparser.parse(content)
            items: List[NewsItem] = []
            for entry in parsed.entries[:limit]:
                items.append(NewsItem(
                    title=entry.get("title", "Bez nazvaniya"),
                    url=entry.get("link", ""),
                    source=parsed.feed.get("title", "RSS"),
                    published=entry.get("published", ""),
                    summary=entry.get("summary", ""),
                ))
            return items
        except Exception as exc:
            logger.warning("RSS fetch failed for %s: %s", feed_url, exc)
            return []

    async def fetch_default_feeds(self, limit: int = 5) -> List[NewsItem]:
        """Fetch all default feeds."""
        all_items: List[NewsItem] = []
        for name, url in self.DEFAULT_FEEDS.items():
            items = await self.fetch_feed(url, limit=limit)
            for item in items:
                item.source = name
            all_items.extend(items)
        return all_items


# ---------------------------------------------------------------------------
# IntelWorker v3
# ---------------------------------------------------------------------------


class IntelWorker:
    """
    Vorker razvedki s realnymi istochnikami.

    Novoe v v3:
    - HackerNews API
    - Reddit JSON API
    - RSS agregator
    - Keshirovanie rezultatov
    """

    def __init__(self, llm_router=None, mcp_layer=None):
        self.llm = llm_router
        self.mcp = mcp_layer

        # Fetchers
        self._hn = _HNFetcher()
        self._reddit = _RedditFetcher()
        self._rss = _RSSFetcher()

        # Cache: topic -> (timestamp, report)
        self._cache: Dict[str, tuple[float, TrendReport]] = {}
        self._cache_ttl = 3600  # 1 chas

    async def execute(self, task, thought_chain):
        """Glavniy vhod"""
        action = task.description.lower()

        if "konkurent" in action or "competitor" in action:
            return await self.analyze_competitors(task.context)
        elif "trend" in action or "trend" in action:
            return await self.analyze_trends(task.context)
        elif "digest" in action or "daydzhest" in action:
            return await self.daily_digest(task.context)
        elif "mind map" in action or "karta" in action:
            return await self.generate_mind_map(task.context)
        else:
            return await self.research_topic(task.context)

    # -- real data sources ---------------------------------------------------

    async def _fetch_real_data(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        limit: int = 10,
    ) -> TrendReport:
        """Sobrat realnye dannye iz istochnikov.

        Args:
            topic: Tema dlya poiska.
            sources: Spisok istochnikov ("hackernews", "reddit", "rss").
            limit: Limit zapisey na istochnik.

        Returns:
            TrendReport s sobrannymi dannymi.
        """
        sources = sources or ["hackernews", "reddit", "rss"]
        all_items: List[NewsItem] = []
        sources_used: List[str] = []

        tasks = []

        if "hackernews" in sources:
            tasks.append(("hackernews", self._hn.fetch_top(limit)))
        if "reddit" in sources:
            # Vyberem subreddit po teme
            subreddit = self._topic_to_subreddit(topic)
            tasks.append(("reddit", self._reddit.fetch_subreddit(subreddit, limit)))
        if "rss" in sources:
            tasks.append(("rss", self._rss.fetch_default_feeds(limit)))

        # Parallelnyy zapros
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        for (name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("Source %s failed: %s", name, result)
                continue
            if result:
                all_items.extend(result)
                sources_used.append(name)

        # Sortiruem po score (esli est)
        all_items.sort(key=lambda x: x.score, reverse=True)

        return TrendReport(
            topic=topic,
            generated_at=datetime.now().isoformat(),
            sources_used=sources_used,
            items=all_items,
        )

    def _topic_to_subreddit(self, topic: str) -> str:
        """Map topic to relevant subreddit."""
        topic_lower = topic.lower()
        mapping = {
            "ai": "artificial",
            "machine learning": "MachineLearning",
            "startup": "startups",
            "python": "Python",
            "javascript": "javascript",
            "crypto": "CryptoCurrency",
            "web3": "web3",
            "marketing": "marketing",
            "productivity": "productivity",
        }
        for key, sub in mapping.items():
            if key in topic_lower:
                return sub
        return "technology"  # default

    # -- public methods ------------------------------------------------------

    async def analyze_trends(self, context: Dict) -> Dict:
        """Analiz trendov s realnymi dannymi."""
        topic = context.get("topic", "AI agenty")
        platform = context.get("platform", "all")

        # Proveryaem kesh
        cached = self._get_cached(topic)
        if cached:
            logger.info("Using cached trend data for: %s", topic)
            report = cached
        else:
            # Sobiraem realnye dannye
            logger.info("Fetching real trend data for: %s", topic)
            report = await self._fetch_real_data(topic, limit=8)

            # Summariziruem cherez LLM
            if self.llm is not None and report.items:
                report.summary = await self._summarize_items(report.items, topic)

            # Keshiruem
            self._cache[topic] = (time.time(), report)

        # Formatiruem otvet
        lines = [
            f"<b>Trendy: {topic}</b>",
            f"Istochniki: {', '.join(report.sources_used)}",
            f"Novostey sobrano: {len(report.items)}",
            "",
        ]

        for i, item in enumerate(report.items[:10], 1):
            lines.append(f"{i}. {item.title}")
            if item.score:
                lines.append(f"   Oches: {item.score}")
            lines.append(f"   {item.url}")
            lines.append("")

        if report.summary:
            lines.append("<b>Summary:</b>")
            lines.append(report.summary)

        return {
            "type": "trend_analysis",
            "topic": topic,
            "platform": platform,
            "trends": "\n".join(lines),
            "raw_report": report.to_dict(),
            "generated_at": report.generated_at,
        }

    async def daily_digest(self, context: Dict) -> Dict:
        """Ezhednevnyy daydzhest s realnymi dannymi."""
        interests = context.get("interests", ["AI", "avtomatizaciya", "startapy"])

        all_items: List[NewsItem] = []
        for topic in interests:
            report = await self._fetch_real_data(topic, limit=5)
            all_items.extend(report.items)

        # Sortiruem po vremeni/score
        all_items.sort(key=lambda x: x.score, reverse=True)

        lines = [f"<b>Daily Digest</b> — {datetime.now().strftime('%Y-%m-%d')}", ""]
        for i, item in enumerate(all_items[:15], 1):
            lines.append(f"{i}. [{item.source}] {item.title}")

        return {
            "type": "daily_digest",
            "date": datetime.now().isoformat(),
            "content": "\n".join(lines),
            "items_count": len(all_items),
        }

    async def analyze_competitors(self, context: Dict) -> Dict:
        """Analiz konkurentov (cherez LLM + web search esli dostupen)."""
        niche = context.get("niche", "AI avtomatizaciya")

        prompt = f"""Provedi analiz konkurentov v nishe: {niche}

        Day:
        1. Top-5 konkurentov (kto, chem zanimaetsya, auditoriya)
        2. Ih silnye storony
        3. Ih slabye storony
        4. Chem my mozhem otlichcatsya
        5. Rekomendacii po positioning
        """

        analysis = ""
        if self.llm is not None:
            try:
                analysis = await self.llm.complete(prompt, max_tokens=2000)
            except Exception as exc:
                logger.warning("LLM competitor analysis failed: %s", exc)
                analysis = f"(Oshibka LLM: {exc})"
        else:
            analysis = "(LLM nedostupen — ne udalos provesti analiz)"

        return {
            "type": "competitor_analysis",
            "niche": niche,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }

    async def generate_mind_map(self, context: Dict) -> Dict:
        """Mind map generaciya."""
        topic = context.get("topic", "AI avtomatizaciya")

        prompt = f"""Sozdai mind map (kartu znaniy) po teme: {topic}

        Format (Markdown):
        # {topic}
        ## Osnovnaya vetka 1
        - Podtema 1.1
          - Detal 1.1.1
          - Detal 1.1.2
        - Podtema 1.2
        ## Osnovnaya vetka 2
        ...

        Sdelay strukturirovanno, 3-5 osnovnyh vetok, s detalyami.
        """

        mind_map = ""
        if self.llm is not None:
            try:
                mind_map = await self.llm.complete(prompt, max_tokens=2000)
            except Exception as exc:
                logger.warning("LLM mind map failed: %s", exc)
                mind_map = f"(Oshibka: {exc})"
        else:
            mind_map = "(LLM nedostupen)"

        return {
            "type": "mind_map",
            "topic": topic,
            "format": "markdown",
            "content": mind_map,
            "generated_at": datetime.now().isoformat()
        }

    async def research_topic(self, context: Dict) -> Dict:
        """Issledovanie temy."""
        topic = context.get("topic", "")
        depth = context.get("depth", "medium")

        # Pytayemsya sobrat realnye dannye
        real_data = await self._fetch_real_data(topic, limit=5)

        prompt = f"""Provedi issledovanie temy: {topic}
Glubina: {depth}

Poslednie novosti po teme:
{self._format_items_for_prompt(real_data.items[:5])}

Day:
1. Kratkoe obyasnenie (chto eto, zachem nuzhno)
2. Klyuchevye koncepcii (5-7 terminov s obyasneniyami)
3. Instrumenty i texnologii
4. Luchshie praktiki
5. Istocniki dlya dalneyshego izucheniya
"""

        research = ""
        if self.llm is not None:
            try:
                research = await self.llm.complete(prompt, max_tokens=2000)
            except Exception as exc:
                logger.warning("LLM research failed: %s", exc)
                research = f"(Oshibka LLM: {exc})"
        else:
            # Bez LLM — vozvrashaem suxie fakty
            research = self._format_items_for_prompt(real_data.items)

        return {
            "type": "research",
            "topic": topic,
            "depth": depth,
            "content": research,
            "sources": real_data.sources_used,
            "items_count": len(real_data.items),
        }

    # -- helpers -------------------------------------------------------------

    def _get_cached(self, topic: str) -> Optional[TrendReport]:
        """Poluchit zakeshirovannyy otchet."""
        if topic in self._cache:
            ts, report = self._cache[topic]
            if time.time() - ts < self._cache_ttl:
                return report
            del self._cache[topic]
        return None

    async def _summarize_items(self, items: List[NewsItem], topic: str) -> str:
        """Summarizovat spisok novostey cherez LLM."""
        if not items or self.llm is None:
            return ""

        prompt = (
            f"Summarizuy klyuchevye trendy po teme '{topic}' na osnove etix novostey:\n\n"
        )
        for i, item in enumerate(items[:10], 1):
            prompt += f"{i}. {item.title}\n"

        prompt += (
            "\nDay:\n"
            "1. Top-3 trenda\n"
            "2. Chto eto znachit dlya biznesa\n"
            "3. Rekomendacii po deystviyam\n"
            "Otvet na russkom yazyke."
        )

        try:
            return await self.llm.complete(prompt, max_tokens=1000)
        except Exception as exc:
            logger.warning("Summarization failed: %s", exc)
            return ""

    @staticmethod
    def _format_items_for_prompt(items: List[NewsItem]) -> str:
        """Formatirovat novosti dlya vstavki v prompt."""
        if not items:
            return "(Novostey ne naydeno)"
        lines = []
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item.title} ({item.source})")
        return "\n".join(lines)
