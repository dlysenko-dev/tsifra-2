"""
Blender AI Workflow - Kimi CLI pishet Python skripty dlya Blender.
Kak u Stefan 3D AI, no s Kimi CLI vmesto Claude.

Pattern:
    Opisanie tekstom -> Kimi CLI generiruet bpy skript 
    -> Blender renderit -> ffmpeg sobiraet MP4
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional


class BlenderAIWorkflow:
    """
    Agent opisyvaet scenu slovami -> Kimi CLI pishet Python skript 
    -> Blender renderit -> video gotovo.
    """

    def __init__(self, kimi_cli_path: Optional[str] = None, project_root: str = "."):
        self.project_root = Path(project_root)
        self.kimi_cli = kimi_cli_path or self._find_kimi_cli()
        self.blender = self._find_blender()
        self.has_ffmpeg = shutil.which("ffmpeg") is not None

    def _find_kimi_cli(self) -> str:
        path = shutil.which("kimi")
        if path:
            return path
        # Windows VS Code extension paths
        candidates = [
            os.path.expanduser(
                r"~\AppData\Roaming\Code\User\globalStorage"
                r"\moonshot-ai.kimi-code\bin\kimi\kimi.exe"
            ),
            os.path.expanduser(
                r"~\AppData\Roaming\Code\User\globalStorage"
                r"\moonshot-ai.kimi-code\bin\kimi\bin\kimi.exe"
            ),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise RuntimeError("kimi CLI not found")

    def _find_blender(self) -> str:
        path = shutil.which("blender")
        if path:
            return path
        candidates = [
            r"C:\Tools\Blender\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender\blender.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise RuntimeError("Blender not found")

    async def generate_scene(self, description: str, output_dir: str) -> str:
        """
        Generiruet 3D scenu cherez Kimi CLI + Blender.

        Args:
            description: Opisanie sceny na russkom ili angliyskom.
            output_dir: Kuda sohranyat rezultat.

        Returns:
            Put k gotovomu video MP4.
        """
        work_dir = Path(output_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Shag 1: Kimi CLI pishet Python skript dlya Blender
        script_path = work_dir / "scene.py"

        system_prompt = (
            "You are a 3D artist and expert in Blender Python API. "
            "Write Python scripts that create 3D scenes in Blender. "
            "Use only basic primitives (spheres, cubes, cylinders, cones). "
            "Add lighting, camera, animation. "
            "Scene should be horror/mysterious themed. "
            "Render via Eevee. Resolution 1080x1920 (vertical). "
            "30 fps. Duration 15 seconds."
        )

        # ASCII-only prompt to avoid cp1251 crash
        user_prompt = (
            f"Create a Python script for Blender.\n\n"
            f"Scene description: {description}\n\n"
            f"Requirements:\n"
            f"- Use bpy (Blender Python API)\n"
            f"- Start with clearing the scene\n"
            f"- Add lighting (SUN + POINT for atmosphere)\n"
            f"- Camera with animation (slow approach or orbit)\n"
            f"- Use primitive_uv_sphere_add, primitive_cube_add, etc.\n"
            f"- Materials via Principled BSDF\n"
            f"- Animation via keyframe_insert\n"
            f"- Render engine: BLENDER_EEVEE_NEXT\n"
            f"- Resolution: 1080x1920, fps=30, frame_end=450 (15 sec)\n"
            f"- Render to PNG frames with filepath=//frames/frame_\n"
            f"- bpy.ops.render.render(animation=True)\n\n"
            f"Return ONLY the Python code, no explanations."
        )

        print("[Kimi CLI] Generating Blender script...")
        print(f"[Kimi CLI] Using: {self.kimi_cli}")

        # Write prompt to temp file to avoid cmdline encoding issues
        prompt_file = work_dir / "_prompt.txt"
        prompt_file.write_text(user_prompt, encoding="utf-8")

        # Run Kimi CLI with prompt from file
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["CHCP"] = "65001"

        try:
            # Method 1: kimi.exe with --quiet -p <prompt>
            result = subprocess.run(
                [self.kimi_cli, "--quiet", "-p", user_prompt],
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
                errors="replace",
                env=env,
                stdin=subprocess.DEVNULL,
            )
        except Exception as exc:
            return f"[ERROR] Kimi CLI failed to start: {exc}"

        if result.returncode != 0:
            stderr = result.stderr[:800] if result.stderr else "(no stderr)"
            # Check if it's the unicode crash
            if "codec" in stderr.lower() and "can't encode" in stderr.lower():
                # Try fallback: write prompt to file and use kimi < file
                return await self._generate_with_prompt_file(
                    description, work_dir, script_path
                )
            return f"[ERROR] Kimi CLI exit {result.returncode}: {stderr}"

        stdout = result.stdout or ""
        print(f"[Kimi CLI] Response length: {len(stdout)} chars")

        # Extract Python code
        code = self._extract_python_code(stdout)
        if not code:
            print("[Kimi CLI] No Python code found, using fallback template")
            code = self._fallback_script(description)

        script_path.write_text(code, encoding="utf-8")
        print(f"[Kimi CLI] Script saved: {script_path}")

        # Shag 2: Blender renderit
        frames_dir = work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        print(f"[Blender] Rendering with {self.blender}")
        print("[Blender] This may take 15-40 minutes on GTX 1650...")

        proc = subprocess.run(
            [self.blender, "--background", "--python", str(script_path.absolute())],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hours max
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        if proc.returncode != 0:
            stderr = proc.stderr[:1000] if proc.stderr else "(no stderr)"
            stdout = proc.stdout[:500] if proc.stdout else ""
            return (
                f"[ERROR] Blender exit {proc.returncode}\n"
                f"stderr: {stderr}\nstdout: {stdout}"
            )

        # Check frames
        frame_files = sorted(frames_dir.glob("frame_*.png"))
        print(f"[Blender] Rendered {len(frame_files)} frames")

        if not frame_files:
            # Try other patterns
            frame_files = sorted(frames_dir.glob("*.png"))
            if not frame_files:
                return "[ERROR] No frames rendered"

        # Shag 3: ffmpeg sobiraet video
        if not self.has_ffmpeg:
            return f"[ERROR] ffmpeg not found. Frames at: {frames_dir}"

        video_path = work_dir / "output.mp4"

        # Find frame numbering pattern
        first_frame = frame_files[0]
        # Check if frames use 0001, 0002, etc.
        has_numbered = any(re.search(r'\d{4}', f.name) for f in frame_files[:5])

        if has_numbered:
            # Use pattern with %04d
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-framerate", "30",
                "-i", str(frames_dir / "frame_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "23",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                str(video_path),
            ]
        else:
            # Use concat demuxer
            concat_file = work_dir / "frame_list.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for frame in frame_files:
                    f.write(f"file '{frame.name}'\nduration 0.033\n")
                f.write(f"file '{frame_files[-1].name}'\n")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "23",
                str(video_path),
            ]

        print("[ffmpeg] Assembling video...")
        ffmpeg_proc = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )

        if ffmpeg_proc.returncode != 0:
            stderr = ffmpeg_proc.stderr[:500] if ffmpeg_proc.stderr else ""
            return f"[ERROR] ffmpeg: {stderr}"

        if video_path.exists():
            size_mb = video_path.stat().st_size / (1024 * 1024)
            print(f"[DONE] Video: {video_path} ({size_mb:.1f} MB)")
            return str(video_path)

        return "[ERROR] ffmpeg did not create video file"

    async def _generate_with_prompt_file(
        self, description: str, work_dir: Path, script_path: Path
    ) -> str:
        """Fallback: write prompt to file and use kimi < prompt.txt."""
        print("[Kimi CLI] Using file-based prompt (unicode workaround)")

        prompt_text = (
            f"Write a Python script for Blender 3D.\n\n"
            f"Scene: {description}\n\n"
            f"The script must:\n"
            f"1. Clear existing objects\n"
            f"2. Create 3D objects using bpy primitives\n"
            f"3. Add lighting and camera\n"
            f"4. Set animation keyframes\n"
            f"5. Render with Eevee at 1080x1920, 30fps, 450 frames\n"
            f"6. Save frames to //frames/frame_\n\n"
            f"Return ONLY Python code, no markdown."
        )

        prompt_file = work_dir / "_prompt.txt"
        prompt_file.write_text(prompt_text, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        # Try different invocation methods
        for cmd in [
            # Method A: stdin redirection
            f'cat "{prompt_file}" | "{self.kimi_cli}" --quiet',
            # Method B: direct stdin
            [sys.executable, "-c", 
             f"import subprocess, sys; "
             f"p=subprocess.Popen(['{self.kimi_cli}','--quiet'], "
             f"stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, "
             f"env={env}); "
             f"out,err=p.communicate(open('{prompt_file}','rb').read()); "
             f"sys.stdout.buffer.write(out)"],
        ]:
            try:
                if isinstance(cmd, str):
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True,
                        timeout=180, encoding="utf-8", errors="replace",
                        env=env,
                    )
                else:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True,
                        timeout=180, encoding="utf-8", errors="replace",
                        env=env,
                    )

                if result.returncode == 0 and result.stdout:
                    code = self._extract_python_code(result.stdout)
                    if code:
                        script_path.write_text(code, encoding="utf-8")
                        return None  # Success, continue to render
            except Exception:
                continue

        # All methods failed - use fallback
        print("[Kimi CLI] All methods failed, using fallback template")
        code = self._fallback_script(description)
        script_path.write_text(code, encoding="utf-8")
        return None

    def _extract_python_code(self, text: str) -> str:
        """Izvlakaet Python kod iz otveta Kimi."""
        if not text:
            return ""

        # Pattern 1: ```python ... ```
        match = re.search(r'```python\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
        else:
            # Pattern 2: ``` ... ```
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                code = match.group(1).strip()
            else:
                # Pattern 3: Look for import bpy
                if "import bpy" in text:
                    lines = text.splitlines()
                    start = 0
                    for i, line in enumerate(lines):
                        if "import bpy" in line or line.strip().startswith("import bpy"):
                            start = i
                            break
                    code = "\n".join(lines[start:]).strip()
                else:
                    code = text.strip()

        # Post-process: fix known Blender 4.2 API issues
        return self._fix_blender_api(code)

    def _fix_blender_api(self, code: str) -> str:
        """Fix known Blender 4.2 API compatibility issues."""
        # Fix 1: scene.render.frame_start/end -> scene.frame_start/end
        code = re.sub(
            r'(\bscene\.render\.frame_start\b)',
            r'scene.frame_start',
            code
        )
        code = re.sub(
            r'(\bscene\.render\.frame_end\b)',
            r'scene.frame_end',
            code
        )
        code = re.sub(
            r'(\bbpy\.context\.scene\.render\.frame_start\b)',
            r'bpy.context.scene.frame_start',
            code
        )
        code = re.sub(
            r'(\bbpy\.context\.scene\.render\.frame_end\b)',
            r'bpy.context.scene.frame_end',
            code
        )

        # Fix 2: Remove known bad Eevee attributes
        bad_eevee = [
            'eevee.use_raytracing',
            'eevee.use_ssr',
            'eevee.volumetric_scattering',
            'eevee.volumetric_samples',
        ]
        lines = code.splitlines()
        filtered = []
        for line in lines:
            stripped = line.strip()
            if any(attr in stripped for attr in bad_eevee):
                # Skip this line
                continue
            filtered.append(line)
        code = "\n".join(filtered)

        return code

    def _fallback_script(self, description: str) -> str:
        """Fallback skript esli Kimi CLI ne rabotaet."""
        print("[Fallback] Using template-based script")
        # Use the horror snowman template as fallback
        from templates import horror_snowman

        # Try to load template
        template_path = Path(__file__).parent.parent / "templates" / "horror_snowman.py"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")

        # Minimal fallback
        return '''
import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.context.scene.frame_end = 450
bpy.context.scene.render.fps = 30
bpy.context.scene.render.resolution_x = 1080
bpy.context.scene.render.resolution_y = 1920
bpy.context.scene.render.resolution_percentage = 100

# World
bpy.context.scene.world.use_nodes = True
bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.02, 0.05, 1)
bpy.context.scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.3

# Light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
light = bpy.context.active_object
light.data.energy = 2

# Camera
bpy.ops.object.camera_add(location=(0, -6, 3))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(70), 0, 0)
bpy.context.scene.camera = cam

# Snowman
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(0, 0, 0.8))
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 2.1))
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(0, 0, 3.0))

# Render
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.render.filepath = "//frames/frame_"
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(animation=True)
'''
