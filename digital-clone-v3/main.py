#!/usr/bin/env python3
"""
Digital Clone v3 — tochka vhoda
Zapusk: python main.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Load .env before any imports that read environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(str(env_path), override=True)
except ImportError:
    pass

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.jarvis_v3 import JarvisOrchestrator, IntentType
from core.llm_router import LLMRouter
from core.mcp_layer import MCPLayer
from core.autonomous_loop import AutonomousLoop
from core.telegram_bot import JarvisTelegramBot
from agents.content_worker import ContentWorker
from agents.video_worker import VideoWorker
from agents.dev_worker import DevWorker
from agents.intel_worker import IntelWorker
from agents.sell_worker import SellWorker
from skills.engine import SkillRegistry, SkillRouter, SkillExecutor
from skills.business_models import list_business_models, recommend_model


async def main():
    """Glavnaya funkciya zapuska"""
    print("=" * 60)
    print("  Digital Clone v3 — Jarvis Agent")
    print("  Architecture: OpenManus-style + Multi-LLM + MCP")
    print("=" * 60)
    
    # 1. Inicializaciya LLM Router (s fallback)
    print("\n[1/7] Initializing LLM Router...")
    llm = LLMRouter()
    health = await llm.health_check()
    print(f"      Providers: {health}")
    
    # 2. Inicializaciya MCP Layer
    print("\n[2/7] Initializing MCP Layer...")
    mcp = MCPLayer()
    tools = list(mcp.tools.keys())
    print(f"      Tools registered: {len(tools)}")
    print(f"      {', '.join(tools[:10])}...")

    # 2b. Registraciya Real Tools (tg_publish_post, shorts_generate, etc.)
    from core.real_tools import RealTools
    real_tools = RealTools(llm_router=llm, project_root=str(PROJECT_ROOT))
    mcp.register_real_tools(real_tools)
    real_tools_count = len([t for t in mcp.tools.keys() if t in (
        "tg_publish_post", "shorts_generate", "content_publish_full",
        "video_publish_full", "tg_send_video", "video_create_hybrid"
    )])
    print(f"      Real tools registered: {real_tools_count}")

    # 3. Inicializaciya Skills Engine
    print("\n[3/7] Initializing Skills Engine...")
    registry = SkillRegistry()
    router = SkillRouter(registry)
    executor = SkillExecutor(registry, llm, mcp)
    print(f"      Skills registered: {len(registry.skills)}")
    
    # 4. Inicializaciya vorokerov
    print("\n[4/7] Registering Workers...")
    jarvis = JarvisOrchestrator()
    jarvis.llm_router = llm
    jarvis.mcp_layer = mcp
    jarvis.memory = None  # Will be initialized later
    
    jarvis.register_worker("content", ContentWorker(llm, mcp))
    jarvis.register_worker("video", VideoWorker(llm, mcp))
    jarvis.register_worker("dev", DevWorker(llm, mcp))
    jarvis.register_worker("intel", IntelWorker(llm, mcp))
    jarvis.register_worker("sell", SellWorker(llm, mcp))
    
    workers = list(jarvis.workers.keys())
    print(f"      Workers: {', '.join(workers)}")
    
    # 5. Biznes-modeli
    print("\n[5/7] Loading Business Models...")
    models = list_business_models()
    for m in models:
        print(f"      - {m['name']}: {m['revenue_potential']}")

    # 6. Zapusk Autonomous Loop
    print("\n[6/7] Starting Autonomous Loop...")
    loop = AutonomousLoop(jarvis)
    schedule_path = PROJECT_ROOT / "config" / "autonomous_schedule.json"
    tasks_loaded = await loop.load_schedule(str(schedule_path))
    print(f"      Scheduled tasks: {tasks_loaded}")

    # 7. Zapusk Telegram Bot
    print("\n[7/7] Starting Telegram Bot...")
    bot = JarvisTelegramBot(jarvis=jarvis)
    if bot.token:
        print(f"      Bot token: {bot.token[:10]}...")
        # Peredaem bot v AutonomousLoop dlya uvedomleniy
        loop.telegram_bot = bot
    else:
        print("      WARNING: TG_BOT_TOKEN not set, bot will not start")

    # 8. Finalniy status
    print("\n" + "=" * 60)
    print("  System Ready!")
    print("=" * 60)
    print(f"\nStats:")
    print(f"  - LLM Providers: {len([p for p, h in health.items() if h])}/{len(health)} active")
    print(f"  - MCP Tools: {len(tools)}")
    print(f"  - Skills: {len(registry.skills)}")
    print(f"  - Workers: {len(workers)}")
    print(f"  - Business Models: {len(models)}")
    print(f"  - Autonomous Tasks: {tasks_loaded}")
    print(f"  - Telegram Bot: {'YES' if bot.token else 'NO'}")

    # Zapuskaem demo-zadachi + autonomous loop odnovremenno
    print("\n" + "=" * 60)
    print("  DEMO: Processing test tasks + Autonomous Loop")
    print("=" * 60)

    test_tasks = [
        "Sozdai post pro AI avtomatizaciyu dlya Telegram",
        "Sdelay shortc pro MCP protokol",
        "Provedi analiz konkurentov v nishe AI agentov",
        "Napishi kod dlya parsera JSON na Python",
    ]

    async def run_demo_tasks():
        """Vypolnit demo-zadachi posledovatelno."""
        for task_desc in test_tasks:
            print(f"\n  Task: {task_desc}")
            try:
                result = await jarvis.process(task_desc)
                print(f"  → Intent: {result['intent']}")
                print(f"  → Status: {result['status']}")
                if result.get('result'):
                    result_str = str(result['result'])[:100]
                    print(f"  → Preview: {result_str}...")
            except Exception as exc:
                print(f"  → ERROR: {exc}")
        print("\n  Demo tasks completed. Autonomous loop continues running...")
        # Derzhim korutinu zhivoy, chtobi loop.run() prodolzhal rabotu
        while True:
            await asyncio.sleep(3600)

    # Zapuskaem vse komponenty parallelno:
    # - AutonomousLoop (proaktivniy cikl)
    # - Telegram Bot (polling)
    # - Demo tasks (zatem beskonechniy son)
    coros = [loop.run(), run_demo_tasks()]
    if bot.token:
        coros.append(bot.start())

    await asyncio.gather(*coros)


if __name__ == "__main__":
    asyncio.run(main())
