import asyncio
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env', override=True)

from core.video_creator import VideoCreator
from core.llm_router import LLMRouter

async def test():
    llm = LLMRouter()
    vc = VideoCreator(llm_router=llm, project_root='.')
    result = await vc.create_video(
        topic="Снеговик демон в моём доме хоррор",
        style="blender_3d",
        duration=25.0
    )
    print("Result:", result)

asyncio.run(test())
