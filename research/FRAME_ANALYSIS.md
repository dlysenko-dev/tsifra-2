# Покадровый разбор референсных видео
## YoEdit0r + Arsenii Merzliakov

---

## 1. YoEdit0r — "Как Монтировать Reels, TikTok, Shorts в Минималистичном Стиле"

### Общая характеристика
- **Длительность**: ~29 мин (туториал)
- **Формат**: 16:9 horizontal (YouTube), но обсуждает 9:16 reels
- **Палитра**: Desaturated, low contrast, earthy tones, много натурального света
- **Темп**: Медленный, размеренный. Cuts редкие (1 раз в 4-5 сек в интро)
- **Аудио**: Mean -17.8 dB, Max 0.0 dB — очень динамичное, громкое, с impacts

### Покадровый разбор интро (0-30 сек)

| Время | Кадр | Техника | Описание |
|-------|------|---------|----------|
| 0.0s | 0001 | Title card | "Минимализм" — чистый белый фон, тонкий sans-serif, centered |
| 2.0s | 0020 | Establishing shot | Широкий план, человек за компьютером у окна. Moody, natural light, low saturation. Длинный take (~3 сек) |
| 5.0s | 0050 | Talking head + text | Говорящий с текстом "ЭТОТ СТИЛЬ МОНТАЖА". Белый lowercase текст, тонкая обводка, centered на chest. Monitor с timeline на заднем плане |
| 10.0s | 0100 | Motion graphic | Retro TV с test pattern, rotating green/black spiral background, pixel/8-bit text "ПЕРЕХОДЯТ ОТ САВГЕРОВ". VHS feel |
| 15.0s | 0150 | Phone mockup | iPhone на белом фоне, clean design. Bullet points: "Чистый дизайн", "Плавные анимации". Rounded corners, minimal |
| 25.0s | 0250 | Title card | "Минималистичный стиль монтажа" — elegant serif font (курсив), light rays/gradient background, AE tutorial label |

### Ключевые техники YoEdit0r
1. **Long establishing shots** (3+ сек) — даёт зрителю время "вдохнуть"
2. **Clean sans-serif text** — thin stroke, white, centered, lowercase
3. **Retro/VHS motion graphics** — TV test patterns, spirals, pixel fonts
4. **Phone mockups** на clean white background — минимализм
5. **Elegant serif titles** — курсив, light effects, gradient backgrounds
6. **Low saturation color grade** — earthy, desaturated, natural
7. **Slow pacing** — не спешит, каждый shot держится достаточно долго
8. **Background B-roll** — monitor с editing timeline за спиной говорящего

### Чего НЕТ у YoEdit0r (в отличие от viral editors)
- Нет ultra-fast cuts (1-2 сек)
- Нет glitch transitions
- Нет bold/zoom текстовых анимаций
- Нет phonk/_trap музыки
- Эстетика: calm, minimal, thoughtful

---

## 2. Arsenii Merzliakov — "Как делать ТРЕНДОВЫЙ монтаж в CapCut [Гайд 2026]"

### Общая характеристика
- **Длительность**: ~11.8 мин (туториал)
- **Формат**: 16:9, screen recording + phone mockups
- **Палитра**: Dark theme (CapCut UI), B&W + sepia для mockups, neon accents
- **Темп**: Быстрее YoEdit0r, cuts каждые 3 сек в среднем
- **Аудио**: Mean -27.6 dB, Max -2.6 dB — менее динамичное, но есть пики

### Покадровый разбор интро (0-30 сек)

| Время | Кадр | Техника | Описание |
|-------|------|---------|----------|
| 0.0s | 0001 | Kinetic text | Буквы "В ЭТОМ" на чёрном фоне, yellow/glow, fast motion |
| 2.0s | 0020 | Kinetic text + blur | "пок" / "лом" — буквы разлетаются с motion blur, RGB split, film grain |
| 5.0s | 0050 | Glitch text | "CAPCUT" — magenta/pink glow, chromatic aberration, scanlines, noise |
| 10.0s | 0100 | Phone mockup | B&W image (человек с газетой) + text "But here is the Truth", rounded corners, sepia tone, film grain overlay |
| 15.0s | 0150 | Phone mockup + particles | Мешок денег, рука, text "SUBWAY" — floating objects, B&W, vintage |
| 20.0s | 0200 | Black frame | Чёрный экран — hard cut transition |
| 25.0s | 0250 | UI showcase | CapCut media library, dark theme, thumbnail grid, 3D perspective tilt |

### Ключевые техники Merzliakov
1. **Kinetic typography** — буквы разлетаются/собираются с motion blur
2. **Chromatic aberration / RGB split** — цветные края на text и objects
3. **Glitch effects** — scanlines, noise, digital distortion
4. **Phone mockups** с rounded corners на чёрном фоне
5. **B&W + sepia vintage grade** — film grain overlay, old photo look
6. **Floating particles/objects** — деньги, руки, мешки — parallax effect
7. **Hard cuts + black frames** — резкие transitions без fades
8. **Dark UI showcase** — screen recording с 3D perspective
9. **Neon glow** — magenta/cyan accents на чёрном

### Что объединяет обоих авторов
- Оба используют **phone mockups** для демонстрации reels
- Оба используют **text overlays** как ключевой элемент
- Оба делают **tutorials**, а не просто viral edits
- Оба используют **clean compositions**

### Чем они отличаются
| YoEdit0r | Merzliakov |
|----------|------------|
| Minimal, calm | Trendy, energetic |
| Natural light | Dark/neon |
| Long takes | Fast cuts |
| Serif titles | Kinetic typography |
| Low saturation | B&W + sepia |
| VHS/retro | Glitch/digital |
| White backgrounds | Black backgrounds |

---

## 3. Выводы для нашего pipeline

### Что нужно добавить в v8:
1. **Phone mockup overlay** — rounded rectangle frame для 9:16 content
2. **Film grain overlay** — vintage texture
3. **Kinetic text** — letter-by-letter animation (PIL sequence или ASS)
4. **Chromatic aberration / RGB split** — через ffmpeg `geq`
5. **Scanlines overlay** — horizontal lines для glitch effect
6. **Sepia / B&W grade** — через `colorchannelmixer` или `hue`
7. **Black frame hard cuts** — 2-3 frame black flashes
8. **Elegant title cards** — serif font + gradient background + light rays
9. **Phone perspective tilt** — 3D rotation через `perspective` или `v360`
10. **Particle floating objects** — PNG overlays с keyframe drift

### Технические приоритеты:
1. Film grain + scanlines (легко, максимальный визуальный impact)
2. Sepia/B&W grade (легко через ffmpeg)
3. Phone mockup frame (PNG overlay)
4. Kinetic text (PIL seq, но можно и через ffmpeg drawtext с per-frame enable)
5. RGB split / chromatic aberration (ffmpeg geq)
6. Black hard cuts (уже есть, усилить)
