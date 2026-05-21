"""
Video Creator — гибридный инструмент Motion Canvas + Blender + ffmpeg
Агент описывает ролик → получает готовый MP4

Требования:
    - Blender (blender.org) — бесплатно
    - Motion Canvas — npm install (бесплатно)
    - ffmpeg — ffmpeg.org (бесплатно)
    - Node.js + npm
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SceneSegment:
    """Один сегмент ролика."""
    type: str           # "motion_canvas" | "blender_3d" | "transition"
    duration: float     # секунды
    description: str    # что происходит (для LLM)
    script_code: str = ""  # сгенерированный код
    rendered_path: str = ""  # путь к отрендеренному файлу


@dataclass
class VideoProject:
    """Проект ролика."""
    topic: str
    total_duration: float
    segments: List[SceneSegment] = field(default_factory=list)
    audio_path: str = ""
    output_path: str = ""


class VideoCreator:
    """
    Гибридный видео-генератор.
    
    Pipeline:
        1. Агент даёт описание ролика
        2. LLM разбивает на сегменты (Motion Canvas vs Blender)
        3. Генерирует код для каждого сегмента
        4. Рендерит Motion Canvas (хуки, CTA, текст)
        5. Рендерит Blender (3D сцены, персонажи)
        6. ffmpeg склеивает всё + аудио + субтитры
    """

    def __init__(self, llm_router=None, project_root: str = "."):
        self.llm = llm_router
        self.current_topic = ""
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "output" / "videos"
        self.temp_dir = self.project_root / "temp" / "video_projects"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Asset Engine + Smart Asset Finder
        try:
            from core.asset_downloader import AssetDownloader
            from core.sound_library import SoundLibrary
            from core.video_assembler import VideoAssembler
            from core.asset_finder import AssetFinder
            self._assets = AssetDownloader(output_dir=str(self.project_root / "assets"))
            self._sounds = SoundLibrary(library_dir=str(self.project_root / "assets" / "sounds"))
            self._assembler = VideoAssembler(output_dir=str(self.output_dir))
            self._asset_finder = AssetFinder(output_dir=str(self.project_root / "assets"))
            self.has_asset_engine = True
        except Exception as e:
            print(f"[WARN] Asset Engine ne inicializirovan: {e}")
            self._assets = None
            self._sounds = None
            self._assembler = None
            self._asset_finder = None
            self.has_asset_engine = False

        # Проверяем зависимости
        self._check_dependencies()

    def _check_dependencies(self):
        """Проверить что установлено ffmpeg, Blender, Node, Remotion."""
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self._blender_exe = None
        
        # 1. Portable Blender (C:\Tools\Blender) — предпочтительный вариант
        portable = Path(r"C:\Tools\Blender\blender.exe")
        if portable.exists():
            self._blender_exe = str(portable)
        
        # 2. PATH
        if self._blender_exe is None:
            self._blender_exe = shutil.which("blender")
        
        # 3. Windows Store Blender (только blender.exe, не launcher)
        if self._blender_exe is None:
            local_apps = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps"
            candidate = local_apps / "blender.exe"
            if candidate.exists():
                self._blender_exe = str(candidate)
        
        self.has_blender = self._blender_exe is not None
        self.has_node = shutil.which("node") is not None and shutil.which("npm") is not None
        
        # Remotion check: нужен node + remotion в node_modules
        remotion_cli = self.project_root / "node_modules" / ".bin" / "remotion"
        remotion_cli_win = self.project_root / "node_modules" / ".bin" / "remotion.cmd"
        self.has_remotion = (
            self.has_node and 
            (remotion_cli.exists() or remotion_cli_win.exists())
        )

        # Blender VSE Editor
        try:
            from core.blender_vse import BlenderVSEEditor
            from core.blender_vse.styles import get_style
            self._blender_vse = BlenderVSEEditor(output_dir=str(self.output_dir))
            self.has_blender_vse = True
        except Exception as e:
            self._blender_vse = None
            self.has_blender_vse = False
            print(f"[WARN] Blender VSE Editor не инициализирован: {e}")
        
        if not self.has_ffmpeg:
            print("[WARN] ffmpeg ne najden. Ustanovi: https://ffmpeg.org/download.html")
        if not self.has_blender:
            print("[WARN] Blender ne najden. Ustanovi: https://www.blender.org/download/")
        else:
            print(f"[INFO] Blender found: {self._blender_exe}")
        if not self.has_node:
            print("[WARN] Node.js ne najden. Ustanovi: https://nodejs.org/")
        if not self.has_remotion:
            print("[WARN] Remotion ne najden. Ustanovi: npm install remotion @remotion/cli")

    # ═══════════════════════════════════════════════
    # PUBLIC API — что вызывает агент
    # ═══════════════════════════════════════════════

    async def create_video(self, topic: str, style: str = "hybrid", 
                          duration: float = 15.0) -> str:
        """
        Главный метод. Агент вызывает это.
        
        Args:
            topic: Тема ролика (например: "AI заменяет менеджера")
            style: "hybrid" | "motion_canvas" | "blender_3d"
            duration: Длительность в секундах (рекомендуется 15-30 для Shorts)
        
        Returns:
            Путь к готовому MP4 файлу
        """
        self.current_topic = topic
        print(f"\n[VIDEO] Video Creator: '{topic}' ({duration}s, {style})")

        # Blender VSE — прямой вызов без сегментации
        if style == "blender_vse":
            return await self.create_video_blender_vse(topic, style="yoedit", duration=duration)
        
        project = VideoProject(topic=topic, total_duration=duration)
        
        # Шаг 1: LLM разбивает на сегменты
        segments = await self._plan_segments(topic, duration, style)
        project.segments = segments
        
        # Шаг 2: Генерируем код для каждого сегмента
        for seg in project.segments:
            if seg.type == "motion_canvas":
                seg.script_code = await self._generate_motion_canvas_code(seg)
            elif seg.type == "blender_3d":
                seg.script_code = await self._generate_blender_code(seg)
            elif seg.type == "remotion":
                seg.script_code = await self._generate_remotion_code(seg)
        
        # Шаг 3: Рендерим сегменты
        work_dir = self.temp_dir / f"project_{self._slug(topic)}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        rendered_clips = []
        for i, seg in enumerate(project.segments):
            if seg.type == "motion_canvas":
                path = await self._render_motion_canvas(seg, work_dir, i)
            elif seg.type == "blender_3d":
                path = await self._render_blender(seg, work_dir, i)
            elif seg.type == "remotion":
                path = await self._render_remotion(seg, work_dir, i)
            else:
                continue
            
            if path and Path(path).exists():
                seg.rendered_path = path
                rendered_clips.append(path)
                print(f"  [OK] Сегмент {i}: {seg.type} ({seg.duration}s)")
            else:
                print(f"  [FAIL] Сегмент {i}: {seg.type} — рендеринг провален")
        
        if not rendered_clips:
            print("[WARN] Ни один сегмент не отрендерился, использую fallback")
            fallback_path = await self._fallback_video(topic, duration, work_dir)
            if fallback_path:
                project.output_path = fallback_path
                print(f"\n[DONE] Fallback video ready: {fallback_path}")
                return fallback_path
            return "ERROR: ни один сегмент не отрендерился"
        
        # Шаг 4: Генерируем аудио (TTS)
        audio_path = await self._generate_audio(topic, work_dir)
        project.audio_path = audio_path
        
        # Шаг 5: ffmpeg — склеиваем всё
        output_path = self.output_dir / f"short_{self._slug(topic)}_{int(duration)}s.mp4"
        await self._assemble_final(rendered_clips, audio_path, str(output_path), duration)
        
        project.output_path = str(output_path)
        print(f"\n[DONE] Video ready: {output_path}")
        return str(output_path)

    async def create_video_simple(self, topic: str) -> str:
        """Уproshchennyj metod: huk → scena → CTA za 15 sekund."""
        return await self.create_video(topic, style="hybrid", duration=15.0)

    # ═══════════════════════════════════════════════
    # ASSET ENGINE (Arsenij Merzljakov style)
    # ═══════════════════════════════════════════════

    async def create_video_asset_engine(self, topic: str, duration: float = 15.0) -> str:
        """
        Sozdat rolik cherez Asset Engine: ischet assety → skleivajet v 3 sceny.

        Stil Merzljakova:
          Scena 1 (Problema)  — temno, haos, bystro
          Scena 2 (Reshenije) — svetlo, porjadok, medlenno
          Scena 3 (Rezultat)  — jarko, cifry, CTA

        Returns:
            Put k gotovomu MP4.
        """
        if not self.has_asset_engine:
            return "[ERROR] Asset Engine ne dostupen"
        if not self.has_ffmpeg:
            return "[ERROR] ffmpeg ne najden"

        print(f"\n[ASSET ENGINE] Tema: '{topic}' ({duration}s)")

        # 1. Iskat assety (parallelno)
        print("  [1] Poisk assetov...")
        video_tasks = [
            self._assets.search_and_download(topic, "video", count=3),
            self._assets.search_and_download(topic + " problem dark", "video", count=2),
            self._assets.search_and_download(topic + " success bright", "video", count=2),
        ]
        video_results = await asyncio.gather(*video_tasks, return_exceptions=True)
        all_videos = []
        for r in video_results:
            if isinstance(r, list):
                all_videos.extend(r)

        # Esli net video — sozdaem color cards
        if len(all_videos) < 3:
            print("  [INFO] Malo stock-video, ispolzuju placeholder-y")
            for color, name in [("black", "dark"), ("white", "bright"), ("red", "vivid")]:
                card = await self._assets.create_color_card(
                    color, 1080, 1920, 5.0, output_name=f"{name}_card"
                )
                if card:
                    all_videos.append(card)

        # 2. Zvuki
        print("  [2] Podgotovka zvukov...")
        sfx = []
        for cat, name in [("transition", "whoosh"), ("impact", "boom"), ("notification", "ping")]:
            s = self._sounds.get_sound(cat, name)
            if s:
                sfx.append(s)
        music = self._sounds.get_sound("ambient", "epic")

        # 3. Skleit 3 sceny
        print("  [3] Montazh 3 scen...")
        scene_durations = [duration * 0.25, duration * 0.45, duration * 0.30]
        scenes = []
        for i, (clip, dur) in enumerate(zip(all_videos[:3], scene_durations)):
            grade = ["dark", "bright", "vivid"][i]
            zoom = ["in", "none", "pulse"][i]
            speed = [1.3, 1.0, 1.1][i]
            scenes.append({
                "file": clip,
                "duration": max(2.0, dur),
                "color_grade": grade,
                "zoom": zoom,
                "speed": speed,
            })

        # Caption-y (burned in)
        captions = [
            {"text": topic[:25].upper(), "start": 0, "duration": 3, "style": "glitch"},
            {"text": "POCHEMU ETO VAZNO?", "start": scene_durations[0], "duration": 3, "style": "bold"},
            {"text": "REZULTAT: 10X", "start": scene_durations[0] + scene_durations[1], "duration": 4, "style": "neon"},
        ]

        output_name = f"merzljakov_{self._slug(topic)}_{int(duration)}s.mp4"
        result = await self._assembler.assemble_story(
            scenes=scenes,
            captions=captions,
            sound_effects=sfx,
            music=music,
            output_name=output_name,
            target_size=(1080, 1920),
            fps=30,
        )

        if result and not result.startswith("[ERROR]"):
            print(f"\n[DONE] Asset Engine video: {result}")
        else:
            print(f"\n[FAIL] Asset Engine: {result}")
        return result

    # ═══════════════════════════════════════════════
    # Blender VSE Editor (новая система монтажа шортсов)
    # ═══════════════════════════════════════════════

    async def create_video_blender_vse(
        self,
        topic: str,
        style: str = "yoedit",
        duration: float = 15.0,
        video_clips: Optional[List[str]] = None,
        texts: Optional[List[Dict]] = None,
    ) -> str:
        """
        Создать шорт через Blender VSE Video Editor.

        Args:
            topic: Тема ролика
            style: Стиль монтажа (yoedit | gadzhi | merzliakov)
            duration: Длительность в секундах
            video_clips: Список путей к видео (если None — ищем через AssetFinder)
            texts: Список текстовых блоков (если None — базовые)

        Returns:
            Путь к готовому MP4 файлу
        """
        if not self.has_blender_vse:
            return "[ERROR] Blender VSE Editor недоступен"

        from core.blender_vse.styles import get_style

        print(f"\n[BLENDER VSE] Тема: '{topic}' | Стиль: {style} | {duration}s")

        # Ищем клипы через AssetFinder если не переданы
        if not video_clips:
            if self._asset_finder:
                print("  [ASSET] Поиск видео через AssetFinder...")
                video_clips = await self._asset_finder.find_videos_for_topic(
                    topic, style=style, count=4
                )
                print(f"  [ASSET] Найдено {len(video_clips)} клипов")
            else:
                video_clips = []

        # Нет клипов = стоп. Не рендерим градиенты и цветные картинки.
        if not video_clips:
            error_msg = (
                "[ERROR] Не найдены видео-клипы для монтажа. "
                "Установи API ключи (PEXELS_API_KEY, PIXABAY_API_KEY) "
                "или передай video_clips вручную."
            )
            print(f"[FAIL] {error_msg}")
            return error_msg

        # Ищем музыку под стиль
        music_path = None
        if self._asset_finder:
            music_path = await self._asset_finder.find_music_for_topic(topic, style=style)
            if music_path:
                print(f"  [ASSET] Музыка: {music_path}")

        # Базовые тексты если не переданы
        if not texts:
            texts = [
                {"text": topic[:30].upper(), "start_frame": 1, "duration": int(duration * 30 * 0.5)},
                {"text": "СМОТРИ ДО КОНЦА", "start_frame": int(duration * 30 * 0.5) + 1, "duration": int(duration * 30 * 0.5)},
            ]

        output_path = str(self.output_dir / f"short_{self._slug(topic)}_{style}_{int(duration)}s.mp4")

        try:
            editor = self._blender_vse
            editor.create_project(width=1080, height=1920, fps=30, duration_frames=int(duration * 30))

            # Добавляем музыку если нашли
            if music_path and Path(music_path).exists():
                try:
                    editor.add_sound(music_path, channel=2, frame_start=1)
                except Exception as e:
                    print(f"  [WARN] Не удалось добавить музыку: {e}")

            style_obj = get_style(style, editor=editor)
            result = style_obj.create_short(
                video_clips=video_clips,
                texts=texts,
                output_path=output_path,
                width=1080,
                height=1920,
                fps=30,
            )

            print(f"\n[DONE] Blender VSE short: {result}")
            return result
        except Exception as exc:
            print(f"[FAIL] Blender VSE error: {exc}")
            return f"[ERROR] {exc}"

    async def _generate_placeholder_clips(self, duration: float) -> List[str]:
        """Сгенерировать placeholder MP4 через ffmpeg."""
        clips = []
        if not self.has_ffmpeg:
            return clips
        try:
            import subprocess
            from pathlib import Path
            out_dir = self.temp_dir / "placeholders"
            out_dir.mkdir(parents=True, exist_ok=True)
            colors = ["black", "darkblue", "red"]
            seg_dur = max(2.0, duration / len(colors))
            for color in colors:
                path = out_dir / f"placeholder_{color}.mp4"
                if not path.exists():
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i",
                        f"color=c={color}:s=1080x1920:d={seg_dur}",
                        "-pix_fmt", "yuv420p", "-an", str(path)
                    ], check=True, capture_output=True)
                clips.append(str(path))
        except Exception as e:
            print(f"[WARN] Не удалось создать placeholder: {e}")
        return clips

    # ═══════════════════════════════════════════════
    # ShAG 1: Planirovanije segmentov
    # ═══════════════════════════════════════════════

    async def _plan_segments(self, topic: str, duration: float, 
                              style: str) -> List[SceneSegment]:
        """LLM разбивает ролик на сегменты."""
        
        # Fallback если LLM не доступен
        if self.llm is None:
            return self._default_plan(topic, duration)
        
        prompt = f"""Разбей YouTube Shorts (15 сек) на сегменты.
        
Тема: "{topic}"
Длительность: {duration} секунд
Формат: 1080x1920 (9:16 вертикальный)

Формат ответа — JSON:
[
  {{"type": "motion_canvas", "duration": 3.0, "description": "Хук: крупный текст с анимацией"}},
  {{"type": "blender_3d", "duration": 8.0, "description": "3D сцена: персонажи, действие"}},
  {{"type": "motion_canvas", "duration": 4.0, "description": "CTA: подписка, ссылка"}}
]

Правила:
- motion_canvas: текст, числа, графики, хуки, CTA — ВСЕГДА первый и последний сегменты
- blender_3d: 3D сцены, персонажи, атмосфера — серединные сегменты
- transition: плавные переходы между сегментами
- Хук ПЕРВЫЙ (2-3 сек) — цепляющая цифра или фраза
- CTA ПОСЛЕДНИЙ (3-4 сек) — призыв к действию
- Сумма duration = {duration} секунд"""

        try:
            response = await self.llm.complete(prompt, max_tokens=500, temperature=0.7)
            # Парсим JSON
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                segments = []
                for item in data:
                    segments.append(SceneSegment(
                        type=item.get("type", "motion_canvas"),
                        duration=float(item.get("duration", 3.0)),
                        description=item.get("description", ""),
                    ))
                return segments
        except Exception as e:
            print(f"  LLM planning failed: {e}")
        
        return self._default_plan(topic, duration)

    def _default_plan(self, topic: str, duration: float) -> List[SceneSegment]:
        """План по умолчанию если LLM не работает."""
        return [
            SceneSegment(type="motion_canvas", duration=3.0, 
                        description=f"Хук: крупный текст '{topic[:20]}...' с анимацией"),
            SceneSegment(type="blender_3d", duration=8.0,
                        description=f"3D сцена про {topic[:30]}"),
            SceneSegment(type="motion_canvas", duration=4.0,
                        description="CTA: Подпишись, ссылка в описании"),
        ]

    # ═══════════════════════════════════════════════
    # ШАГ 2: Генерация кода
    # ═══════════════════════════════════════════════

    async def _generate_motion_canvas_code(self, seg: SceneSegment) -> str:
        """Генерирует TypeScript для Motion Canvas."""
        
        # Это template — LLM может переписать
        if "хук" in seg.description.lower() or "hook" in seg.description.lower():
            return self._motion_canvas_hook_template(seg)
        elif "cta" in seg.description.lower():
            return self._motion_canvas_cta_template(seg)
        else:
            return self._motion_canvas_data_template(seg)

    async def _generate_blender_code(self, seg: SceneSegment) -> str:
        """Генерирует Python скрипт для Blender."""
        desc = seg.description.lower()
        topic = self.current_topic.lower()
        if any(k in desc or k in topic for k in ["снеговик", "horror", "snowman", "ужас", "страх"]):
            return self._load_template("horror_snowman", seg)
        return self._blender_scene_template(seg)
    
    def _load_template(self, name: str, seg: SceneSegment) -> str:
        """Загружает Blender-шаблон из templates/."""
        template_path = Path(__file__).parent.parent / "templates" / f"{name}.py"
        if template_path.exists():
            code = template_path.read_text(encoding="utf-8")
            # Подставляем duration из сегмента
            code = code.replace("{duration}", str(seg.duration))
            return code
        return self._blender_scene_template(seg)

    # ═══════════════════════════════════════════════
    # MOTION CANVAS TEMPLATES
    # ═══════════════════════════════════════════════

    def _motion_canvas_hook_template(self, seg: SceneSegment) -> str:
        """Хук: крупный текст с анимацией."""
        return f'''import {{makeScene2D, Txt, Rect, Circle}} from '@motion-canvas/2d';
import {{all, createRef, waitFor, useRandom, sequence}} from '@motion-canvas/core';

export default makeScene2D(function* (view) {{
  const bg = createRef<Rect>();
  const title = createRef<Txt>();
  const subtitle = createRef<Txt>();
  
  // Тёмный фон
  view.add(<Rect ref={{bg}} width={{1920}} height={{1080}} fill="#0a0a0a" />);
  
  // Основной текст (хук)
  view.add(<Txt ref={{title}} text="{seg.description[:30]}" 
    fill="#ffffff" fontSize={{120}} fontWeight={{700}}
    y={{0}} opacity={{0}} textAlign="center" />);
  
  // Подзаголовок
  view.add(<Txt ref={{subtitle}} text="Смотри до конца →" 
    fill="#00d4ff" fontSize={{48}} y={{200}} opacity={{0}} />);
  
  // Анимация
  yield* all(
    title().opacity(1, 0.5),
    title().scale(1.2, 0.8).to(1, 0.5),
  );
  yield* waitFor(0.5);
  yield* subtitle().opacity(1, 0.5);
  yield* waitFor({seg.duration - 2.3});
}});
'''

    def _motion_canvas_cta_template(self, seg: SceneSegment) -> str:
        """CTA: призыв к действию."""
        return f'''import {{makeScene2D, Txt, Rect, Circle}} from '@motion-canvas/2d';
import {{all, createRef, waitFor, loop}} from '@motion-canvas/core';

export default makeScene2D(function* (view) {{
  const bg = createRef<Rect>();
  const cta = createRef<Txt>();
  const arrow = createRef<Txt>();
  
  view.add(<Rect ref={{bg}} width={{1920}} height={{1080}} fill="#0a0a0a" />);
  
  view.add(<Txt ref={{cta}} text="ПОДПИШИСЬ" 
    fill="#ff3366" fontSize={{100}} fontWeight={{900}}
    y={{0}} opacity={{0}} textAlign="center" />);
  
  view.add(<Txt ref={{arrow}} text="👇" fontSize={{80}} y={{150}} opacity={{0}} />);
  
  yield* cta().opacity(1, 0.5);
  yield* arrow().opacity(1, 0.5);
  
  // Пульсация
  yield* loop(3, () => all(
    cta().scale(1.1, 0.4).to(1, 0.4),
    arrow().y(170, 0.4).to(150, 0.4),
  ));
  
  yield* waitFor({seg.duration - 3});
}});
'''

    def _motion_canvas_data_template(self, seg: SceneSegment) -> str:
        """Данные: графики, цифры."""
        return f'''import {{makeScene2D, Txt, Rect, Line}} from '@motion-canvas/2d';
import {{all, createRef, waitFor, sequence}} from '@motion-canvas/core';

export default makeScene2D(function* (view) {{
  const bg = createRef<Rect>();
  view.add(<Rect ref={{bg}} width={{1920}} height={{1080}} fill="#0a0a0a" />);
  
  const number = createRef<Txt>();
  view.add(<Txt ref={{number}} text="0%" fill="#00ff88" 
    fontSize={{200}} fontWeight={{700}} opacity={{0}} />);
  
  yield* number().opacity(1, 0.3);
  yield* number().text("95%", 1.5);
  yield* waitFor({seg.duration - 2});
}});
'''

    # ═══════════════════════════════════════════════
    # BLENDER TEMPLATES
    # ═══════════════════════════════════════════════

    def _blender_scene_template(self, seg: SceneSegment) -> str:
        """Python скрипт для Blender — динамичная neon/tech сцена."""
        return f'''import bpy
import math
import random

random.seed(42)

# Очистить сцену
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ─── НАСТРОЙКИ ───
DURATION = {seg.duration}
FPS = 30
TOTAL_FRAMES = int(DURATION * FPS)
scene = bpy.context.scene
scene.frame_end = TOTAL_FRAMES
scene.render.fps = FPS
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920

# ─── МИР / ТУМАН ───
scene.world.use_nodes = True
wd = scene.world.node_tree
wd.nodes.clear()
wn_bg = wd.nodes.new('ShaderNodeBackground')
wn_out = wd.nodes.new('ShaderNodeOutputWorld')
wn_bg.inputs[0].default_value = (0.03, 0.05, 0.1, 1)  # Тёмно-синий фон
wn_bg.inputs[1].default_value = 1.0
wd.links.new(wn_bg.outputs[0], wn_out.inputs[0])

# ─── ОСВЕЩЕНИЕ (яркое 3-Point + Neon) ───
# Key light (тёплый)
bpy.ops.object.light_add(type='AREA', location=(4, -3, 6))
key = bpy.context.active_object
key.data.energy = 200
key.data.color = (1.0, 0.9, 0.8)
key.data.size = 5

# Fill (холодный)
bpy.ops.object.light_add(type='AREA', location=(-5, 2, 4))
fill = bpy.context.active_object
fill.data.energy = 150
fill.data.color = (0.4, 0.7, 1.0)
fill.data.size = 4

# Rim / Back (неоновый)
bpy.ops.object.light_add(type='AREA', location=(0, 5, 2))
rim = bpy.context.active_object
rim.data.energy = 120
rim.data.color = (0.2, 1.0, 1.0)
rim.data.size = 3

# Bottom fill (подсветка снизу)
bpy.ops.object.light_add(type='AREA', location=(0, 0, -0.5))
bottom = bpy.context.active_object
bottom.data.energy = 80
bottom.data.color = (0.3, 0.2, 0.5)
bottom.data.size = 8

# ─── КАМЕРА (плавная орбита вокруг центра) ───
bpy.ops.object.camera_add(location=(0, -9, 3.5))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(65), 0, 0)
scene.camera = cam

# Target empty для отслеживания
target = bpy.data.objects.new("CameraTarget", None)
scene.collection.objects.link(target)
target.location = (0, 0, 1.8)

# Constraint: camera смотрит на target
constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = target
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# Анимация камеры: широкая орбита на постоянном расстоянии
for i in range(TOTAL_FRAMES + 1):
    scene.frame_set(i)
    t = i / TOTAL_FRAMES
    angle = t * math.radians(180) - math.radians(90)
    radius = 9.0
    height = 3.5 + math.sin(t * math.pi * 2) * 1.0
    cam.location = (math.sin(angle) * radius, -math.cos(angle) * radius, height)
    cam.keyframe_insert(data_path="location")

# ─── ПОЛ — отражающий grid ───
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -1.5))
floor = bpy.context.active_object
floor_mat = bpy.data.materials.new(name="FloorGrid")
floor_mat.use_nodes = True
fn = floor_mat.node_tree
fn_bsdf = fn.nodes['Principled BSDF']
fn_bsdf.inputs['Base Color'].default_value = (0.02, 0.03, 0.06, 1)
fn_bsdf.inputs['Metallic'].default_value = 0.4
fn_bsdf.inputs['Roughness'].default_value = 0.15
floor.data.materials.append(floor_mat)

# Grid lines на полу (тонкие кубы)
for g in range(-10, 11, 2):
    # X lines
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*2, 0, -1.48))
    gx = bpy.context.active_object
    gx.scale = (0.02, 20, 0.01)
    gm = bpy.data.materials.new(name=f"GridX_{{g}}")
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.0
    gm.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (0.0, 0.5, 0.7, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.0, 0.5, 0.7, 1)
    gx.data.materials.append(gm)
    # Y lines
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, g*2, -1.48))
    gy = bpy.context.active_object
    gy.scale = (20, 0.02, 0.01)
    gy.data.materials.append(gm)

# ─── ПЛАВАЮЩИЕ ОБЪЕКТЫ (геометрия + glow) ───
shapes = []

# Центральный тор (ядро) — компактный
bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.18, location=(0, 0, 2))
torus = bpy.context.active_object
torus.name = "Core"
shapes.append(torus)

tm = bpy.data.materials.new(name="CoreMat")
tm.use_nodes = True
tn = tm.node_tree
tn_bsdf = tn.nodes['Principled BSDF']
tn_bsdf.inputs['Base Color'].default_value = (0.0, 0.5, 0.9, 1)
tn_bsdf.inputs['Metallic'].default_value = 0.9
tn_bsdf.inputs['Roughness'].default_value = 0.15
tn_bsdf.inputs['Emission Strength'].default_value = 0.8
tn_bsdf.inputs['Emission Color'].default_value = (0.0, 0.4, 0.8, 1)
torus.data.materials.append(tm)

# Цветовая палитра для orb-ов
orb_colors = [
    (1.0, 0.3, 0.5),   # розовый
    (0.3, 0.8, 1.0),   # голубой
    (0.6, 0.3, 1.0),   # фиолетовый
    (0.2, 1.0, 0.6),   # мятный
    (1.0, 0.7, 0.2),   # оранжевый
    (0.8, 0.2, 0.6),   # маджента
]

# Окружающие икосферы — разноцветные, шире раскиданы
for j in range(6):
    angle = j * math.pi / 3 + 0.4
    r = 3.0 + random.uniform(-0.5, 0.5)
    z = 1.0 + random.uniform(0.5, 2.5)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.25, 0.45),
        location=(math.cos(angle)*r, math.sin(angle)*r, z))
    sph = bpy.context.active_object
    sph.name = f"Orb_{{j}}"
    shapes.append(sph)
    
    col = orb_colors[j]
    sm = bpy.data.materials.new(name=f"OrbMat_{{j}}")
    sm.use_nodes = True
    sn = sm.node_tree
    sn_bsdf = sn.nodes['Principled BSDF']
    sn_bsdf.inputs['Base Color'].default_value = (col[0]*0.7, col[1]*0.7, col[2]*0.7, 1)
    sn_bsdf.inputs['Metallic'].default_value = 0.6
    sn_bsdf.inputs['Roughness'].default_value = 0.25
    sn_bsdf.inputs['Emission Strength'].default_value = 0.5
    sn_bsdf.inputs['Emission Color'].default_value = (col[0]*0.4, col[1]*0.4, col[2]*0.4, 1)
    sph.data.materials.append(sm)

# Floating cubes — тоже цветные
for j in range(4):
    angle = j * math.pi / 2 + 0.8
    r = 4.0
    z = 2.5 + j * 0.8
    bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.4, 0.7),
        location=(math.cos(angle)*r, math.sin(angle)*r, z))
    cube = bpy.context.active_object
    cube.name = f"Cube_{{j}}"
    shapes.append(cube)
    
    col = orb_colors[(j + 2) % len(orb_colors)]
    cm = bpy.data.materials.new(name=f"CubeMat_{{j}}")
    cm.use_nodes = True
    cn = cm.node_tree
    cn_bsdf = cn.nodes['Principled BSDF']
    cn_bsdf.inputs['Base Color'].default_value = (col[0]*0.5, col[1]*0.5, col[2]*0.5, 1)
    cn_bsdf.inputs['Metallic'].default_value = 0.7
    cn_bsdf.inputs['Roughness'].default_value = 0.1
    cn_bsdf.inputs['Emission Strength'].default_value = 0.3
    cn_bsdf.inputs['Emission Color'].default_value = (col[0]*0.3, col[1]*0.3, col[2]*0.3, 1)
    cube.data.materials.append(cm)

# ─── АНИМАЦИЯ ОБЪЕКТОВ ───
for i in range(TOTAL_FRAMES + 1):
    scene.frame_set(i)
    t = i / TOTAL_FRAMES
    
    # Тор вращается
    torus.rotation_euler = (t * math.pi * 2, t * math.pi, 0)
    torus.keyframe_insert(data_path="rotation_euler")
    
    # Икосферы крутятся и плавают
    for idx, obj in enumerate(shapes[1:7]):
        phase = idx * 1.047
        obj.rotation_euler = (t * math.pi * 2 + phase, t * math.pi * 1.5, 0)
        obj.location.z += math.sin(t * math.pi * 2 + phase) * 0.003
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="location")
    
    # Кубы медленно вращаются
    for idx, obj in enumerate(shapes[7:]):
        obj.rotation_euler = (t * math.pi * 0.5, t * math.pi * 0.3 + idx, 0)
        obj.keyframe_insert(data_path="rotation_euler")

# ─── ЧАСТИЦЫ / Линии (кривые) ───
for k in range(8):
    bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
    curve = bpy.context.active_object
    curve.name = f"Line_{{k}}"
    spline = curve.data.splines[0]
    spline.type = 'POLY'
    spline.points[0].co = (math.cos(k*0.8)*3, math.sin(k*0.8)*3, 0.5, 1)
    spline.points[1].co = (math.cos(k*0.8)*1.5, math.sin(k*0.8)*1.5, 2.5, 1)
    
    crv_mat = bpy.data.materials.new(name=f"LineMat_{{k}}")
    crv_mat.use_nodes = True
    crv_n = crv_mat.node_tree
    crv_n.nodes.clear()
    crv_emit = crv_n.nodes.new('ShaderNodeEmission')
    crv_out = crv_n.nodes.new('ShaderNodeOutputMaterial')
    crv_emit.inputs[0].default_value = (0.0, 0.7 + k*0.03, 1.0, 1)
    crv_emit.inputs[1].default_value = 3.0
    crv_n.links.new(crv_emit.outputs[0], crv_out.inputs[0])
    curve.data.materials.append(crv_mat)
    
    # Анимация линий — пульсация
    for i in range(0, TOTAL_FRAMES + 1, 5):
        scene.frame_set(i)
        scale = 1.0 + 0.3 * math.sin(i / FPS * 2 + k)
        curve.scale = (scale, scale, scale)
        curve.keyframe_insert(data_path="scale")

# ─── РЕНДЕР ───
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.filepath = "//frames/frame_"
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100

# EEVEE настройки для glow
scene.eevee.bloom_intensity = 0.15
scene.eevee.bloom_radius = 6.0
scene.eevee.use_bloom = True
scene.eevee.taa_render_samples = 32

scene.frame_set(1)
bpy.ops.render.render(animation=True)
'''

    # ═══════════════════════════════════════════════
    # ШАГ 3: Рендеринг
    # ═══════════════════════════════════════════════

    async def _render_motion_canvas(self, seg: SceneSegment, 
                                     work_dir: Path, index: int) -> str:
        """Рендерит Motion Canvas сегмент."""
        if not self.has_node:
            return ""
        
        seg_dir = work_dir / f"mc_{index}"
        seg_dir.mkdir(exist_ok=True)
        
        # Создаём проект Motion Canvas
        scene_file = seg_dir / "scene.tsx"
        scene_file.write_text(seg.script_code, encoding="utf-8")
        
        project_ts = seg_dir / "project.ts"
        project_ts.write_text(f'''import {{makeProject}} from '@motion-canvas/core';
import scene from './scene?scene';
export default makeProject({{ scenes: [scene] }});
''', encoding="utf-8")
        
        vite_config = seg_dir / "vite.config.ts"
        vite_config.write_text(f'''import {{defineConfig}} from 'vite';
import motionCanvas from '@motion-canvas/vite-plugin';
export default defineConfig({{ plugins: [motionCanvas()] }});
''', encoding="utf-8")
        
        package_json = seg_dir / "package.json"
        package_json.write_text('''{{"type": "module", "dependencies": {{
  "@motion-canvas/core": "^3.17.0",
  "@motion-canvas/2d": "^3.17.0",
  "@motion-canvas/vite-plugin": "^3.17.0"
}}}}''', encoding="utf-8")
        
        # Use full paths for npm/npx on Windows to avoid resolution issues
        npm_exe = shutil.which("npm") or "npm"
        npx_exe = shutil.which("npx") or "npx"
        
        # npm install + рендер
        try:
            proc = await asyncio.create_subprocess_exec(
                npm_exe, "install", cwd=str(seg_dir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            
            # Рендер через npx
            proc = await asyncio.create_subprocess_exec(
                npx_exe, "motion-canvas", "render", "./project.ts",
                "--output", f"./output_{index}.mp4",
                cwd=str(seg_dir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=2048"}
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            
            output_file = seg_dir / f"output_{index}.mp4"
            if output_file.exists():
                return str(output_file)
        except Exception as e:
            print(f"  Motion Canvas render failed: {e}")
        
        return ""

    async def _render_blender(self, seg: SceneSegment, 
                               work_dir: Path, index: int) -> str:
        """Рендерит Blender сегмент."""
        if not self.has_blender:
            return ""
        
        seg_dir = work_dir / f"blender_{index}"
        seg_dir.mkdir(exist_ok=True)
        frames_dir = seg_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        script_file = seg_dir / "scene.py"
        script_file.write_text(seg.script_code, encoding="utf-8")
        
        try:
            cmd = [self._blender_exe, "--background", "--python", str(script_file.absolute())]
            print(f"  Blender cmd: {cmd}")
            print(f"  Blender cwd: {seg_dir}")
            print(f"  Script exists: {script_file.exists()}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(seg_dir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "BLENDER_SYSTEM_SCRIPTS": ""}
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=int(seg.duration * 30) + 60  # ~30 сек на кадр + запас
            )
            
            # Debug output
            print(f"  Blender exit code: {proc.returncode}")
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ''
            if 'Error' in stderr_text or 'error' in stderr_text:
                print(f"  Blender stderr: {stderr_text[:800]}")
            
            # Собираем кадры в видео
            frame_files = sorted(frames_dir.glob("frame_*.png"))
            print(f"  Blender frames found: {len(frame_files)}")
            if frame_files:
                video_path = seg_dir / f"output_{index}.mp4"
                await self._frames_to_video(frames_dir, str(video_path), seg.duration)
                if video_path.exists():
                    return str(video_path)
        except Exception as e:
            print(f"  Blender render failed: {e}")
        
        return ""

    # ═══════════════════════════════════════════════
    # REMOTION
    # ═══════════════════════════════════════════════

    async def _generate_remotion_code(self, seg: SceneSegment) -> str:
        """Генерирует React-компонент для Remotion."""
        desc = seg.description.lower()
        if "hook" in desc or "hook" in desc or "title" in desc:
            return "AnimatedText"
        elif "counter" in desc or "number" in desc or "stat" in desc:
            return "DataCounter"
        elif "neon" in desc or "glow" in desc:
            return "NeonText"
        elif "particle" in desc or "background" in desc:
            return "ParticleBackground"
        return "MinimalVideo"

    async def _render_remotion(self, seg: SceneSegment,
                                work_dir: Path, index: int) -> str:
        """Рендерит Remotion-сегмент через CLI."""
        if not self.has_remotion:
            return ""
        
        composition = seg.script_code or "MinimalVideo"
        seg_dir = work_dir / f"remotion_{index}"
        seg_dir.mkdir(exist_ok=True)
        
        output_path = seg_dir / f"output_{index}.mp4"
        
        # Находим remotion CLI
        remotion_cmd = None
        for candidate in [
            self.project_root / "node_modules" / ".bin" / "remotion.cmd",
            self.project_root / "node_modules" / ".bin" / "remotion",
        ]:
            if candidate.exists():
                remotion_cmd = str(candidate)
                break
        
        if remotion_cmd is None:
            return ""
        
        try:
            cmd = [
                remotion_cmd, "render",
                str(self.project_root / "video" / "src" / "index.tsx"),
                composition,
                str(output_path),
                "--codec", "h264",
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=int(seg.duration * 5) + 120,  # запас на рендер
            )
            if output_path.exists():
                return str(output_path)
            else:
                err = stderr.decode('utf-8', errors='replace')[-400:] if stderr else ''
                print(f"  [WARN] Remotion render failed: {err}")
        except Exception as e:
            print(f"  Remotion render failed: {e}")
        
        return ""

    async def _frames_to_video(self, frames_dir: Path, output: str, 
                                duration: float):
        """Конвертирует PNG кадры в MP4 через ffmpeg."""
        if not self.has_ffmpeg:
            return
        
        fps = 30
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920",
            "-preset", "fast",
            output,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

    # ═══════════════════════════════════════════════
    # ШАГ 4: Аудио
    # ═══════════════════════════════════════════════

    async def _generate_audio(self, topic: str, work_dir: Path) -> str:
        """Генерирует TTS озвучку."""
        audio_path = work_dir / "audio.mp3"
        
        # Проверяем edge-tts
        if shutil.which("edge-tts") is not None:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "edge-tts", "--voice", "ru-RU-SvetlanaNeural",
                    "--text", topic[:100],
                    "--write-media", str(audio_path),
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(proc.communicate(), timeout=30)
                if audio_path.exists():
                    return str(audio_path)
            except Exception:
                pass
        
        # Fallback: пустой аудио файл
        if self.has_ffmpeg:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", "15", "-acodec", "libmp3lame", str(audio_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
        
        return str(audio_path) if audio_path.exists() else ""

    # ═══════════════════════════════════════════════
    # ШАГ 5: Сборка ffmpeg
    # ═══════════════════════════════════════════════

    async def _assemble_final(self, clips: List[str], audio: str, 
                               output: str, duration: float):
        """Склеивает сегменты + аудио в финальный ролик."""
        if not self.has_ffmpeg or not clips:
            return
        
        out_dir = Path(output).parent
        
        # Копируем сегменты в output-директорию с безопасными именами
        # (избегаем проблем с кодировкой cp1251 на путях с кириллицей)
        safe_clips = []
        for i, clip in enumerate(clips):
            safe_name = out_dir / f"_seg_{i:02d}.mp4"
            try:
                shutil.copy2(clip, safe_name)
                safe_clips.append(safe_name)
            except Exception as e:
                print(f"  [WARN] copy clip {i} failed: {e}")
                safe_clips.append(Path(clip))
        
        # Создаём concat list с относительными путями
        concat_file = out_dir / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in safe_clips:
                rel = Path(clip).relative_to(out_dir)
                f.write(f"file '{rel}'\n")
        
        # ffmpeg: ВСЕ входы сначала, ПОТОМ выходные опции
        # Иначе -c:v libx264 будет интерпретирован как декодер для аудио-входа
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
        ]
        
        if audio and Path(audio).exists():
            cmd.extend(["-i", audio])
        
        # Выходные опции (после ВСЕХ входов)
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "23",
        ])
        
        if audio and Path(audio).exists():
            cmd.extend([
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-map", "0:v:0", "-map", "1:a:0"
            ])
        
        cmd.append(output)
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        
        if proc.returncode != 0:
            err = stderr.decode('utf-8', errors='replace')[-400:] if stderr else ''
            print(f"  [WARN] ffmpeg exit={proc.returncode}, err={err}")
        
        # Cleanup temp segment copies
        for clip in safe_clips:
            try:
                if str(clip).startswith(str(out_dir / "_seg_")):
                    clip.unlink(missing_ok=True)
            except Exception:
                pass
        concat_file.unlink(missing_ok=True)

    # ═══════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════

    async def _fallback_video(self, topic: str, duration: float, work_dir: Path) -> str:
        """Fallback: Blender VSE если доступен, иначе стильное видео с анимированным градиентом."""
        # Fallback 1: Blender VSE Editor
        if self.has_blender_vse:
            try:
                result = await self.create_video_blender_vse(
                    topic=topic,
                    style="yoedit",
                    duration=duration,
                )
                if result and not result.startswith("[ERROR]"):
                    return result
            except Exception as exc:
                print(f"[WARN] Blender VSE fallback failed: {exc}")

        # Fallback 2: анимированный градиент через PIL
        import math
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
        except ImportError:
            return ""
        
        frames_dir = work_dir / "fallback_frames"
        frames_dir.mkdir(exist_ok=True)
        
        width, height = 1080, 1920
        num_frames = int(duration * 30)
        
        # Палитра: тёмно-синий фон с неоновыми акцентами
        BG_TOP = (5, 5, 25)
        BG_BOTTOM = (15, 10, 40)
        NEON_CYAN = (0, 212, 255)
        NEON_PURPLE = (180, 80, 255)
        
        # "Частицы" — заранее генерируем траектории
        import random
        random.seed(42)
        particles = []
        for _ in range(30):
            particles.append({
                'x': random.uniform(0, width),
                'y': random.uniform(0, height),
                'r': random.uniform(2, 6),
                'speed_y': random.uniform(-1.5, -0.3),
                'speed_x': random.uniform(-0.3, 0.3),
                'color': random.choice([NEON_CYAN, NEON_PURPLE, (255, 255, 255)]),
                'alpha_base': random.uniform(80, 200),
            })
        
        for i in range(num_frames):
            t = i / num_frames
            
            # Градиентный фон
            img = Image.new('RGB', (width, height), BG_TOP)
            pixels = img.load()
            for y in range(height):
                ratio = y / height
                r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
                g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
                b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
                for x in range(width):
                    pixels[x, y] = (r, g, b)
            
            draw = ImageDraw.Draw(img)
            
            # Анимированные световые круги (bokeh-эффект)
            for idx in range(5):
                phase = idx * 1.2
                cx = width // 2 + int(math.sin(t * math.pi * 2 + phase) * 300)
                cy = height // 2 + int(math.cos(t * math.pi * 2 + phase * 0.7) * 500)
                radius = 150 + idx * 80
                color = NEON_CYAN if idx % 2 == 0 else NEON_PURPLE
                # Рисуем размытый круг через концентрические окружности
                for r in range(radius, 0, -10):
                    alpha = int(30 * (1 - r / radius))
                    if alpha > 0:
                        draw.ellipse([cx-r, cy-r, cx+r, cy+r], 
                                    fill=(color[0], color[1], color[2]))
            
            # Частицы
            for p in particles:
                px = (p['x'] + p['speed_x'] * i) % width
                py = (p['y'] + p['speed_y'] * i) % height
                pulse = int(p['alpha_base'] * (0.7 + 0.3 * math.sin(i * 0.1 + p['x'])))
                color = p['color']
                draw.ellipse([px-p['r'], py-p['r'], px+p['r'], py+p['r']],
                           fill=(color[0], color[1], color[2]))
            
            # Горизонтальная неоновая линия
            line_y = height // 2 + int(math.sin(t * math.pi * 2) * 100)
            for lw in range(8, 0, -2):
                alpha = 80 - lw * 8
                draw.line([(50, line_y-lw//2), (width-50, line_y-lw//2)],
                         fill=(NEON_CYAN[0], NEON_CYAN[1], NEON_CYAN[2]), width=lw)
            
            # Текст с " glow" эффектом (несколько слоёв)
            text = topic[:40]
            try:
                font = ImageFont.truetype("arial.ttf", 90)
                font_sub = ImageFont.truetype("arial.ttf", 50)
            except Exception:
                font = ImageFont.load_default()
                font_sub = font
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            tx = (width - text_w) // 2
            ty = height // 2 - text_h // 2 - 100
            
            # Glow layers
            for glow in range(15, 0, -3):
                draw.text((tx, ty), text, fill=(0, 150, 200), font=font)
            # Main text
            draw.text((tx, ty), text, fill=(255, 255, 255), font=font)
            
            # Подзаголовок
            sub_text = "AI automation"
            bbox_s = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = bbox_s[2] - bbox_s[0]
            draw.text(((width - sw) // 2, ty + text_h + 40), sub_text,
                     fill=(180, 180, 200), font=font_sub)
            
            # CTA с пульсацией
            cta = "Podpishis!"
            try:
                font_cta = ImageFont.truetype("arial.ttf", 65)
            except Exception:
                font_cta = ImageFont.load_default()
            bbox_c = draw.textbbox((0, 0), cta, font=font_cta)
            cta_w = bbox_c[2] - bbox_c[0]
            cta_x = (width - cta_w) // 2
            cta_y = height - 280
            
            pulse_scale = 1.0 + 0.05 * math.sin(i * 0.2)
            # Glow
            draw.text((cta_x, cta_y), cta, fill=(255, 50, 100), font=font_cta)
            draw.text((cta_x, cta_y), cta, fill=(255, 100, 150), font=font_cta)
            # Main
            draw.text((cta_x, cta_y), cta, fill=(255, 255, 255), font=font_cta)
            
            img.save(frames_dir / f"frame_{i:04d}.png")
        
        output_path = self.output_dir / f"short_{self._slug(topic)}_{int(duration)}s.mp4"
        await self._frames_to_video(frames_dir, str(output_path), duration)
        
        # Add audio
        audio_path = await self._generate_audio(topic, work_dir)
        if audio_path and Path(audio_path).exists():
            final_with_audio = work_dir / "final_with_audio.mp4"
            cmd = [
                "ffmpeg", "-y", "-i", str(output_path),
                "-i", audio_path, "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", str(final_with_audio)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=60)
            if final_with_audio.exists():
                return str(final_with_audio)
        
        return str(output_path) if output_path.exists() else ""

    @staticmethod
    def _slug(text: str) -> str:
        """Конвертирует текст в безопасное имя файла."""
        return re.sub(r'[^a-z0-9]+', '_', text.lower())[:30]


# ═══════════════════════════════════════════════
# MCP TOOL WRAPPER
# ═══════════════════════════════════════════════

class VideoCreatorTool:
    """MCP Tool обёртка для VideoCreator."""
    
    def __init__(self, video_creator: VideoCreator):
        self.vc = video_creator
    
    async def execute(self, params: dict) -> dict:
        """MCP Tool entry point."""
        topic = params.get("topic", "AI automation")
        style = params.get("style", "hybrid")
        duration = float(params.get("duration", 15.0))
        
        result_path = await self.vc.create_video(topic, style, duration)
        
        return {
            "success": result_path.startswith("/"),
            "output_path": result_path,
            "topic": topic,
            "duration": duration,
        }
