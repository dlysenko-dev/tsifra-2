"""
Kinetic Text Generator — letter-by-letter animation with motion blur.
Replicates Merzliakov & YoEdit0r title styles.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import random


class KineticText:
    def __init__(self, font_path: str, output_dir: str, fps: int = 30):
        self.font_path = font_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps

    def _get_font(self, size: int, path: str = None):
        p = path or self.font_path
        try:
            return ImageFont.truetype(p, size)
        except:
            try:
                return ImageFont.truetype(self.font_path, size)
            except:
                return ImageFont.load_default()

    def _glow_text(self, draw, pos, text, font, color, glow_radius=12):
        """Draw text with strong glow effect."""
        x, y = pos
        for r in range(glow_radius, 0, -1):
            alpha = int(255 * (1 - r / glow_radius) * 0.5)
            glow_color = (*color[:3], alpha)
            draw.text((x, y), text, font=font, fill=glow_color)
        draw.text((x, y), text, font=font, fill=(*color[:3], 255))

    def _chromatic_split(self, img: Image.Image, shift: int = 3) -> Image.Image:
        """Apply RGB split (chromatic aberration) via PIL."""
        r, g, b, a = img.split()
        # Shift red left, blue right
        r = r.transform(img.size, Image.AFFINE, (1, 0, -shift, 0, 1, 0))
        b = b.transform(img.size, Image.AFFINE, (1, 0, shift, 0, 1, 0))
        return Image.merge("RGBA", (r, g, b, a))

    def generate_merzliakov_intro(
        self,
        text_lines: list,
        duration: float = 2.5,
        w: int = 1080,
        h: int = 1920,
    ) -> str:
        """
        Merzliakov style: black bg, strong yellow glow text, letter-by-letter,
        motion blur, chromatic aberration, heavy grain, scanlines.
        """
        total_frames = int(duration * self.fps)
        chars_per_sec = 8
        
        frames_dir = self.output_dir / "kinetic_m"
        frames_dir.mkdir(exist_ok=True)
        
        font_size = 130
        font = self._get_font(font_size)
        
        line_heights = []
        total_height = 0
        for line in text_lines:
            bbox = font.getbbox(line)
            lh = bbox[3] - bbox[1] if bbox else font_size
            line_heights.append(lh)
            total_height += lh + 20
        total_height -= 20
        
        start_y = (h - total_height) // 2
        
        for frame_idx in range(total_frames):
            t = frame_idx / self.fps
            img = Image.new('RGBA', (w, h), (0, 0, 0, 255))
            draw = ImageDraw.Draw(img)
            
            # Heavy film grain
            for _ in range(2000):
                gx, gy = int(random.random() * w), int(random.random() * h)
                if gx < w and gy < h:
                    img.putpixel((gx, gy), (
                        int(random.random() * 60 + 120),
                        int(random.random() * 60 + 120),
                        int(random.random() * 60 + 120),
                        50
                    ))
            
            # Draw letters one by one with glow
            char_idx = 0
            y_offset = start_y
            for line_idx, line in enumerate(text_lines):
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0] if bbox else len(line) * font_size * 0.6
                x_offset = (w - line_w) // 2
                
                for char_pos, char in enumerate(line):
                    appear_time = char_idx / chars_per_sec
                    if t >= appear_time:
                        letter_t = min(1.0, (t - appear_time) * 4)
                        
                        # Random fly-in per letter
                        random.seed(char_idx * 100)
                        dir_x = random.choice([-1, 1]) * (80 + random.random() * 150)
                        dir_y = random.choice([-1, 1]) * (40 + random.random() * 100)
                        
                        lx = x_offset + font.getlength(line[:char_pos])
                        ly = y_offset
                        cur_x = lx + dir_x * (1 - letter_t)
                        cur_y = ly + dir_y * (1 - letter_t)
                        
                        # Motion blur trail
                        for step in range(8):
                            trail_t = step / 8
                            tx = lx + dir_x * (1 - trail_t) * (1 - letter_t)
                            ty = ly + dir_y * (1 - trail_t) * (1 - letter_t)
                            alpha = int(200 * letter_t * trail_t * 0.25)
                            draw.text((int(tx), int(ty)), char, font=font, fill=(255, 200, 0, alpha))
                        
                        # Glow layers
                        for r in range(14, 0, -4):
                            alpha = int(255 * letter_t * 0.35 * (1 - r/14))
                            draw.text((int(cur_x + r), int(cur_y + r)), char, font=font, fill=(255, 220, 0, alpha))
                        
                        draw.text((int(cur_x), int(cur_y)), char, font=font, fill=(255, 240, 60, int(255 * letter_t)))
                    
                    char_idx += 1
                
                y_offset += line_heights[line_idx] + 20
            
            # Strong scanlines
            for y in range(0, h, 3):
                draw.line([(0, y), (w, y)], fill=(0, 0, 0, 60))
            
            # Chromatic aberration (RGB split)
            img = self._chromatic_split(img, shift=3)
            
            img.save(frames_dir / f"{frame_idx:04d}.png")
        
        out_path = self.output_dir / "kinetic_merzliakov_intro.mp4"
        cmd = [
            "ffmpeg", "-y", "-framerate", str(self.fps),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", str(out_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return str(out_path)

    def generate_feast_intro(
        self,
        text_lines: list,
        duration: float = 2.5,
        w: int = 1080,
        h: int = 1920,
    ) -> str:
        """
        FEAST style: very dark navy bg, blue glow text, letter-by-letter,
        minimal grain, subtle scanlines.
        """
        total_frames = int(duration * self.fps)
        chars_per_sec = 8
        frames_dir = self.output_dir / "kinetic_f"
        frames_dir.mkdir(exist_ok=True)
        font_size = 130
        font = self._get_font(font_size)
        line_heights = []
        total_height = 0
        for line in text_lines:
            bbox = font.getbbox(line)
            lh = bbox[3] - bbox[1] if bbox else font_size
            line_heights.append(lh)
            total_height += lh + 20
        total_height -= 20
        start_y = (h - total_height) // 2
        for frame_idx in range(total_frames):
            t = frame_idx / self.fps
            img = Image.new('RGBA', (w, h), (5, 5, 16, 255))
            draw = ImageDraw.Draw(img)
            # Light grain
            for _ in range(600):
                gx, gy = int(random.random() * w), int(random.random() * h)
                if gx < w and gy < h:
                    img.putpixel((gx, gy), (100, 120, 160, 25))
            char_idx = 0
            y_offset = start_y
            for line_idx, line in enumerate(text_lines):
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0] if bbox else len(line) * font_size * 0.6
                x_offset = (w - line_w) // 2
                for char_pos, char in enumerate(line):
                    appear_time = char_idx / chars_per_sec
                    if t >= appear_time:
                        letter_t = min(1.0, (t - appear_time) * 4)
                        lx = x_offset + font.getlength(line[:char_pos])
                        ly = y_offset
                        # Blue glow
                        self._glow_text(draw, (int(lx), int(ly)), char, font, (60, 150, 255), glow_radius=12)
                        color = (200, 230, 255, int(255 * letter_t))
                        draw.text((int(lx), int(ly)), char, font=font, fill=color)
                    char_idx += 1
                y_offset += line_heights[line_idx] + 20
            # Subtle scanlines
            for y in range(0, h, 4):
                draw.line([(0, y), (w, y)], fill=(0, 0, 0, 30))
            img.save(frames_dir / f"{frame_idx:04d}.png")
        out_path = self.output_dir / "kinetic_feast_intro.mp4"
        cmd = [
            "ffmpeg", "-y", "-framerate", str(self.fps),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", str(out_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return str(out_path)

    def generate_yoedit0r_intro(
        self,
        title: str,
        subtitle: str = "",
        duration: float = 3.0,
        w: int = 1080,
        h: int = 1920,
    ) -> str:
        """
        YoEdit0r style: light bg, elegant serif (Times New Roman), light rays, minimal.
        """
        total_frames = int(duration * self.fps)
        frames_dir = self.output_dir / "kinetic_y"
        frames_dir.mkdir(exist_ok=True)
        
        # Try elegant serif fonts
        serif_candidates = [
            "C:/Windows/Fonts/timesbd.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
            self.font_path,
        ]
        serif_font = None
        for sc in serif_candidates:
            if os.path.exists(sc):
                serif_font = sc
                break
        
        font_title = self._get_font(110, path=serif_font)
        font_sub = self._get_font(42, path=serif_font)
        
        for frame_idx in range(total_frames):
            t = frame_idx / self.fps
            progress = min(1.0, t / 1.5)
            
            # Soft gradient background
            img = Image.new('RGBA', (w, h), (250, 250, 252, 255))
            draw = ImageDraw.Draw(img)
            
            # Light rays from center
            cx, cy = w // 2, h // 2
            for angle in range(0, 360, 10):
                rad = math.radians(angle + frame_idx * 0.3)
                for r in range(0, max(w, h), 6):
                    px = int(cx + r * math.cos(rad))
                    py = int(cy + r * math.sin(rad))
                    if 0 <= px < w and 0 <= py < h:
                        alpha = int(45 * progress * (1 - r / max(w, h)))
                        img.putpixel((px, py), (255, 255, 255, 255))
            
            # Soft vignette
            for y in range(0, h, 4):
                for x in range(0, w, 4):
                    dist = math.sqrt((x - cx)**2 + (y - cy)**2) / max(cx, cy)
                    if dist > 0.6:
                        alpha = int((dist - 0.6) * 200)
                        draw.point((x, y), fill=(0, 0, 0, min(alpha, 80)))
            
            # Title with elegant fade and slight scale
            scale = 0.85 + 0.15 * progress
            title_size = int(110 * scale)
            font_t = self._get_font(title_size, path=serif_font)
            
            bbox = font_t.getbbox(title)
            tw = bbox[2] - bbox[0] if bbox else len(title) * title_size * 0.5
            th = bbox[3] - bbox[1] if bbox else title_size
            tx = (w - tw) // 2
            ty = (h - th) // 2 - 60
            
            # Soft shadow
            shadow_alpha = int(60 * progress)
            draw.text((tx + 4, ty + 4), title, font=font_t, fill=(0, 0, 0, shadow_alpha))
            # Main text
            alpha = int(255 * progress)
            draw.text((tx, ty), title, font=font_t, fill=(20, 20, 40, alpha))
            
            # Subtitle
            if subtitle:
                bbox_s = font_sub.getbbox(subtitle)
                sw = bbox_s[2] - bbox_s[0] if bbox_s else len(subtitle) * 20
                sx = (w - sw) // 2
                sy = ty + th + 50
                sub_alpha = int(255 * max(0, (progress - 0.3) / 0.7))
                draw.text((sx, sy), subtitle, font=font_sub, fill=(60, 60, 80, sub_alpha))
            
            img.save(frames_dir / f"{frame_idx:04d}.png")
        
        out_path = self.output_dir / "kinetic_yoedit0r_intro.mp4"
        cmd = [
            "ffmpeg", "-y", "-framerate", str(self.fps),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", str(out_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return str(out_path)


if __name__ == "__main__":
    import math
    import random
    
    font_path = "C:/Windows/Temp/font.ttf"
    out = "C:/Windows/Temp/pro_v9_safe"
    
    kt = KineticText(font_path, out)
    
    # Test Merzliakov
    m_path = kt.generate_merzliakov_intro(
        text_lines=["TRENDY", "EDIT"],
        duration=2.0
    )
    print(f"Merzliakov intro: {m_path}")
    
    # Test YoEdit0r
    y_path = kt.generate_yoedit0r_intro(
        title="Минимализм",
        subtitle="Aftereffect туториал",
        duration=2.5
    )
    print(f"YoEdit0r intro: {y_path}")
