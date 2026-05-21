"""
Bounce Animator — replicates After Effects bounce expression via PIL.
AE Expression:
    amp = 0.04; freq = 1.8; decay = 3;
    v * amp * sin(freq * t * 2 * PI) / exp(decay * t) * easeFactor
"""

import math
from PIL import Image, ImageDraw, ImageFont


def bounce_value(t, start_val, end_val, amp=0.04, freq=1.8, decay=3.0, time_max=3.0):
    """
    Calculate bounced value at time t after keyframe.
    t: time since keyframe (seconds)
    start_val: value before keyframe
    end_val: target value at keyframe
    """
    if t >= time_max:
        return end_val
    
    # Velocity (difference between target and start)
    v = end_val - start_val
    
    # Ease out factor (1 → 0)
    ease_factor = max(0, 1 - t / time_max)
    
    # Bounce component
    bounce = v * amp * math.sin(freq * t * 2 * math.pi) / math.exp(decay * t) * ease_factor
    
    return end_val + bounce


def generate_bounce_text(
    text,
    font_path,
    output_path,
    w=1080,
    h=1920,
    duration=2.5,
    fps=30,
    start_scale=0.3,
    end_scale=1.0,
    start_y_offset=200,
    text_color=(255, 255, 255, 255),
    bg_color=(0, 0, 0, 255),
    glow_color=(255, 220, 0, 180),
):
    """Generate MP4 with bounced text animation."""
    import subprocess, os
    
    total_frames = int(duration * fps)
    frames_dir = output_path.replace('.mp4', '_frames')
    os.makedirs(frames_dir, exist_ok=True)
    
    try:
        font = ImageFont.truetype(font_path, 120)
    except:
        font = ImageFont.load_default()
    
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        
        img = Image.new('RGBA', (w, h), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Calculate bounced scale and position
        cur_scale = bounce_value(t, start_scale, end_scale)
        cur_y_offset = bounce_value(t, start_y_offset, 0, amp=0.03, freq=2.0)
        
        # Measure text at full scale
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0] if bbox else len(text) * 60
        text_h = bbox[3] - bbox[1] if bbox else 120
        
        # Scale dimensions
        scaled_w = int(text_w * cur_scale)
        scaled_h = int(text_h * cur_scale)
        
        # Create text image at full size
        txt_img = Image.new('RGBA', (int(text_w) + 40, int(text_h) + 40), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        
        # Glow
        for r in range(20, 0, -5):
            alpha = int(glow_color[3] * cur_scale * (1 - r/20))
            txt_draw.text((20 + r, 20 + r), text, font=font, fill=(*glow_color[:3], alpha))
        
        # Main text
        txt_draw.text((20, 20), text, font=font, fill=text_color)
        
        # Scale
        txt_img = txt_img.resize((scaled_w + 40, scaled_h + 40), Image.LANCZOS)
        
        # Position (centered with Y bounce)
        px = (w - txt_img.width) // 2
        py = (h - txt_img.height) // 2 + int(cur_y_offset)
        
        img.paste(txt_img, (px, py), txt_img)
        
        img.save(f"{frames_dir}/{frame_idx:04d}.png")
    
    # Compile to MP4
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", f"{frames_dir}/%04d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


if __name__ == "__main__":
    out = generate_bounce_text(
        "ЭНЕРГИЯ",
        "C:/Windows/Temp/font.ttf",
        "C:/Windows/Temp/pro_v9_safe/bounce_test.mp4",
        duration=2.0
    )
    print(f"Done: {out}")
