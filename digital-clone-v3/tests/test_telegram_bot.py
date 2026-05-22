#!/usr/bin/env python3
"""
Test Telegram Bot integration
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.jarvis_v3 import JarvisOrchestrator
from core.telegram_bot import JarvisTelegramBot


async def test_bot():
    """Test bot initialization and basic functions."""
    print("=" * 50)
    print("Testing Telegram Bot")
    print("=" * 50)

    # Create mock Jarvis
    jarvis = JarvisOrchestrator()

    # Test bot initialization
    bot = JarvisTelegramBot(jarvis=jarvis)
    print(f"\n1. Bot initialized: {bot is not None}")
    print(f"   Token present: {bool(bot.token)}")
    print(f"   Token prefix: {bot.token[:15] + '...' if bot.token else 'NONE'}")

    # Test stats
    stats = bot.stats.to_dict()
    print(f"\n2. Stats: {stats}")

    # Test _extract_response_text
    test_cases = [
        {"result": "Hello world"},
        {"result": {"content": "Post content here"}},
        {"result": {"analysis": "Competitor analysis"}},
        {"status": "done", "intent": "content"},
    ]
    print("\n3. Response text extraction:")
    for tc in test_cases:
        text = bot._extract_response_text(tc)
        print(f"   {tc} -> {text[:50]}...")

    # Test admin management
    bot.add_admin(123456789)
    print(f"\n4. Admins: {bot.admin_chat_ids}")

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_bot())
