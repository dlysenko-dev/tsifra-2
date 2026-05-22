#!/usr/bin/env python3
"""
Test Stefan 3D AI style workflow.
Kimi CLI generiruet unikalnyy skript dlya Blender.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.blender_ai_workflow import BlenderAIWorkflow


async def test():
    workflow = BlenderAIWorkflow(project_root=".")

    result = await workflow.generate_scene(
        description=(
            "Snowman in a dark forest at night. "
            "The snowman is made of three spheres. "
            "Eyes glow red. "
            "Camera slowly approaches. "
            "Horror atmosphere. Blue moonlight. "
            "Trees in background. Snow on ground."
        ),
        output_dir="./output/test_stefan_snowman"
    )
    print(f"\n[DONE] Result: {result}")


if __name__ == "__main__":
    asyncio.run(test())
