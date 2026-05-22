import asyncio
import sys
sys.path.insert(0, '.')

from core.video_creator import VideoCreator
from core.llm_router import LLMRouter

async def test():
    llm = LLMRouter()
    vc = VideoCreator(llm_router=llm, project_root='.')
    
    print("Создаю тестовый ролик (15 сек)...")
    result = await vc.create_video(
        topic="AI автоматизация для бизнеса",
        style="hybrid",
        duration=15.0
    )
    print(f"\nРезультат: {result}")

asyncio.run(test())
