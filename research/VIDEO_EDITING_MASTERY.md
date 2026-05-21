# Video Editing Mastery Database
## Target Authors: YoEdit0r, Arsenii Merzliakov, Iman Gadzhi
## Mission: Replicate professional editing quality programmatically

---

## 1. Iman Gadzhi Style Analysis

### Signature Elements (from research)
- **Font**: Montserrat Bold (sometimes Arial/Helvetica for captions)
- **Pacing**: Fast cuts every 1-2 seconds. Jump cuts to remove dead air.
- **Dynamic zooms**: Punch-in zooms on key moments. Ken Burns slow zoom on B-roll.
- **Text overlays**: Bold, high-contrast, white with dark stroke. Large size.
- **Color grading**: High contrast, slightly desaturated, teal/orange hints. Lumetri-style.
- **Sound design**: Whooshes on cuts, bass hits on transitions, audio ducking under voice.
- **B-roll insertion**: Quick cutaways to luxury lifestyle footage (cars, offices, travel).
- **Speed ramping**: Slow-mo on impactful moments, fast-forward on transitions.
- **CTA cards**: Bold end-screen with subscribe/follow callouts.

### Technical Implementation Plan
1. **Fast cuts**: ffmpeg `select` filter or scene detection → auto-cut every 1-2s
2. **Dynamic zoom**: `zoompan` with sinusoidal curves, or `scale`+`crop` keyframes
3. **Text**: drawtext with Montserrat Bold, white fill, black border (outline), shadow
4. **Color grade**: `eq` contrast/sat + `curves` RGB + `lutyuv` for teal/orange
5. **Transitions**: `xfade` with fast duration (0.1-0.3s), or custom `fade` + `zoom`
6. **Sound**: layer whoosh SFX on every cut, sidechain compression ducking

---

## 2. YoEdit0r Style Analysis

### What we know (viral shorts editor)
- Platform: YouTube Shorts, TikTok, Reels
- Style: Trending sounds, fast-paced, meme inserts, text pop-ins
- **Jump cuts every 1-2 seconds** — prevents drop-off
- **Punch-in zooms** — keeps attention high
- **Beat syncing** — cuts on every beat
- **Speed ramping** — adds energy
- **Dynamic text pop-ins** — highlights keywords
- **Overlay graphics** — arrows, circles, icons
- **Flash cuts** — rapid flashes for intensity
- **Glitch transitions** — glow, shake, distortion, color flicker
- **Meme inserts** — instant engagement

### Technical Implementation Plan
1. **Beat detection**: `aubio` or ffmpeg `showfreqs` → detect transients → cut on beats
2. **Glitch effects**: `geq` (general equation) for RGB splitting, `noise` for grain, `negate` flash frames
3. **Text pop-in**: `drawtext` with `enable='between(t,start,end)'` + scale animation via `zoompan` overlay
4. **Overlay graphics**: PNG sequences (arrows, circles) composited with `overlay`
5. **Flash cuts**: insert 2-3 frame white/black clips between segments
6. **Meme inserts**: quick 0.5s meme PNGs with `zoompan` bounce effect

---

## 3. Arsenii Merzliakov Style Analysis

### What we know (cinematic storyteller)
- Style: Cinematic, slow transitions, color grading, emotional narrative
- **Seamless transitions**: Speed ramps, luma fades, whip pans
- **Cinematic color grading**: Teal & orange, film-style LUTs
- **Speed ramping**: Dramatic slow-mo on key moments
- **Motion graphics**: Clean lower-thirds, animated titles
- **Sound design**: Ambient soundscapes, emotional swells
- **B-roll storytelling**: Visuals guide narrative, not just decoration

### Technical Implementation Plan
1. **Seamless transitions**: `xfade` with luma matte or custom mask video
2. **Color grading**: Apply .cube LUTs via `lut3d` filter in ffmpeg
3. **Whip pan**: `zoompan` with fast horizontal movement + motion blur via `tmix`
4. **Speed ramp**: `atempo` + `setpts` curves (bezier interpolation)
5. **Titles**: `drawtext` with fade-in + tracking (letter-spacing animation)
6. **Ambient audio**: layer room tone + reverb via `aecho`

---

## 4. Universal Viral Editing Techniques (2025)

### From research — 15 techniques:
1. Jump cuts every 1-2 seconds
2. Punch-in zooms
3. Speed ramping (curve-based)
4. Beat syncing (audio-driven cuts)
5. Split-screen reactions
6. Quick B-roll cutaways
7. Looping end for replay
8. Luma & motion transitions
9. AI auto-captions (animated)
10. Green screen commentary
11. Keyframe animations (position, scale, opacity)
12. Dynamic text pop-ins (scale + fade)
13. Overlay graphics (arrows, circles)
14. Meme inserts
15. Flash cuts (1-3 frame flashes)

### Sound Design Rules
- Sound is 50% of success
- High-energy music (trap, phonk, epic)
- Whooshes, hits, swooshes on every cut
- Pop sound effects on text appearance
- Sync actions to beats
- Audio ducking when voiceover plays

### Text & Caption Rules (2025)
- Bold fonts (Montserrat, Impact, Arial Bold)
- Stroke/outlines for readability
- 5-8 words per line max
- Animate dynamically (scale in, slide in, typewriter)
- Use emojis for emotional boost
- Captions for silent viewers

---

## 5. ffmpeg Implementation Guide

### 5.1 Fast Cuts + Beat Sync
```bash
# Detect beats with aubio
aubio beat input.mp3 > beats.txt

# Or ffmpeg loudness detection for transient peaks
ffmpeg -i input.mp3 -af "ebur128=peak=true" -f null -
```

### 5.2 Dynamic Zoom (Ken Burns on steroids)
```bash
# Sinusoidal zoom in+out synced to clip duration
ffmpeg -i clip.mp4 -vf "zoompan=z='min(zoom+0.0015,1.5)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920" out.mp4
```

### 5.3 Glitch Effect
```bash
# RGB split + noise flash
ffmpeg -i clip.mp4 -vf "split[r][g][b];
[r]crop=iw:ih:2:0,pad=iw+4:ih:2:0:red[r1];
[g]crop=iw:ih:0:0[g1];
[b]crop=iw:ih:-2:0,pad=iw+4:ih:2:0:black[b1];
[r1][g1][b1]blend=all_mode=addition, noise=alls=20:allf=t+u" out.mp4
```

### 5.4 Text with Animation
```bash
# Scale-in text using drawtext + enable
ffmpeg -i clip.mp4 -vf "drawtext=fontfile=Montserrat-Bold.ttf:
text='KEY MESSAGE':
fontcolor=white:
fontsize=120:
borderw=6:bordercolor=black:
x=(w-text_w)/2:y=(h-text_h)/2:
enable='between(t,1,3)'" out.mp4
```

### 5.5 Flash Cut Transition
```bash
# Insert 2 white frames between clips
ffmpeg -f lavfi -i color=c=white:s=1080x1920:d=0.08 -i clip1.mp4 -i clip2.mp4 \
-filter_complex "[0][1][2]concat=n=3:v=1:a=0" out.mp4
```

### 5.6 Speed Ramping
```bash
# Bezier curve speed ramp: slow → fast → normal
ffmpeg -i clip.mp4 -filter_complex "
[0:v]setpts='PTS/((1+sin(PI*t/3))/2+0.5)'[v];
[0:a]atempo='((1+sin(PI*t/3))/2+0.5)'[a]"
-map "[v]" -map "[a]" out.mp4
```

### 5.7 Overlay Graphics (PNG)
```bash
# Arrow overlay bouncing in
ffmpeg -i clip.mp4 -i arrow.png -filter_complex "
[1:v]format=rgba,
zoompan=z='min(zoom+0.05,1.5)':d=30:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=200x200,
fade=t=in:st=0:d=0.3[arrow];
[0:v][arrow]overlay=x=W-w-50:y=H-h-50:enable='between(t,2,4)'" out.mp4
```

### 5.8 Cinematic Color Grade with LUT
```bash
ffmpeg -i clip.mp4 -vf "lut3d='cinematic.cube', eq=contrast=1.1:saturation=1.2" out.mp4
```

---

## 6. Blender VSE Advanced Techniques

### What works in headless mode:
- Text strips with `font_size` + `blend_alpha` keyframes
- Adjustment strips for color grading
- Sound strips
- Image strips (PNGs)
- Effect strips (cross, gamma cross)

### What DOES NOT work headless:
- MovieSequence video decoding (gray frames)
- TextSequence `animation_data` in 4.x

### Workaround for video in headless Blender:
1. Pre-extract frames from video to PNG sequence using ffmpeg
2. Add Image Sequence strip in Blender VSE
3. Apply effects, text, color grade in VSE
4. Render final output

### Advanced Blender VSE pipeline:
```python
# 1. Extract frames
ffmpeg -i video.mp4 -vf "fps=30,scale=1080:1920" frames/%04d.png

# 2. Add image sequence + text + effects in Blender VSE
# 3. Render
```

---

## 7. Assets Needed

### Fonts:
- Montserrat Bold (Gadzhi)
- Impact (bold headlines)
- Arial Bold (captions)
- Helvetica Neue (clean captions)

### LUTs:
- Teal & Orange cinematic
- High contrast desaturated
- Kodak film emulation
- Orange & Teal (Merzliakov style)

### SFX:
- Whoosh transitions (10 variants)
- Bass hits / impacts
- Pop sounds (text appearance)
- Glitch sounds
- Ambient room tones

### Overlays:
- Arrow PNGs (animated)
- Circle highlights
- Progress bars
- Subscribe buttons
- Flash frames (white/black)

### Transitions:
- Luma matte wipes
- Zoom transitions
- Glitch transitions
- Whip pan blur

---

## 8. Learning Checklist

- [x] Research editing styles of target authors
- [x] Document signature techniques
- [x] Find free asset sources
- [ ] Download reference videos for frame analysis
- [ ] Frame-by-frame breakdown of 3 reference videos
- [ ] Build ffmpeg filters for each technique
- [ ] Build Blender VSE pipeline for each technique
- [ ] Create automated beat-sync cut detection
- [ ] Implement speed ramping with curves
- [ ] Implement glitch effects
- [ ] Implement dynamic text animations
- [ ] Collect and organize asset library
- [ ] Test render and iterate quality
- [ ] Match reference quality

---

## 9. Quality Benchmarks

### Amateur (REJECTED):
- Crossfade between clips
- Static text overlays
- No sound design
- No color grading
- Single speed throughout

### Professional (TARGET):
- Cuts every 1-2 seconds or on beat
- Dynamic zooms and motion on every clip
- Animated text synced to audio
- Layered sound design (music + SFX + ambient)
- Cinematic color grading with LUTs
- Speed ramps for emphasis
- Seamless transitions (not just fades)
- Overlay graphics for emphasis
- Consistent visual style/branding

---

*Last updated: 2026-05-18*
*Next step: Download reference videos, frame analysis, asset collection*
