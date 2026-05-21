# ПРОМПТ ДЛЯ ВТОРОГО ОКНА KIMI CODE

## Контекст проекта
Ты работаешь в проекте `c:\Users\mafio\цифра 2\digital-clone-v3\`. Это motion design pipeline для создания видео в стиле Iman Gadzhi (beat-synced motion graphics, kinetic typography, SFX sync).

**Ключевая проблема:** Главный агент (первое окно) НЕ МОЖЕТ разобрать motion design референсов по скриншотам. Один скриншот = одна секунда видео, а в секунде происходит 30 кадров с анимацией. Агент не "вкуривает" как движутся элементы. Твоя задача — стать его "глазами" и документировать ДВИЖЕНИЕ.

## Твоя задача
Пользователь пришлёт видео-референсы. Ты должен:

### 1. Скачать видео
- Если пользователь дал ссылку — скачай видео через `yt-dlp` или аналог
- Если пользователь дал файл — скопируй его в `assets/gadzhi_sources/references/`
- **ВАЖНО:** Все пути с кириллицей ломают ffmpeg. Используй `C:/Windows/Temp/pro_v9_safe/refs/` для всех ffmpeg операций

### 2. Покадровый анализ (каждые 2-3 кадра)
Для КАЖДОГО сегмента видео извлекай кадры через ffmpeg:
```bash
ffmpeg -i video.mp4 -vf "select='not(mod(n,2))'" -vsync vfr frame_%04d.png
```

Смотри кадры и документируй **ДВИЖЕНИЕ** каждого элемента:

#### Что документировать для каждого элемента (текст, иконка, фото, фигура):
1. **Entry animation** (как появляется):
   - Scale: от 0% до 100%? С bounce? С overshoot?
   - Position: откуда прилетает? (left, right, top, bottom, center zoom)
   - Opacity: fade-in 0→1 или резко?
   - Rotation: есть ли spin/tilt?
   - Duration: сколько кадров длится появление?
   - Easing: linear / ease-out / ease-in-out / elastic / bounce?

2. **Hold phase** (статичное состояние):
   - Есть ли subtle motion? (пульсация, drift, float)
   - Position: где находится относительно центра?
   - Scale: 100% или больше/меньше?

3. **Exit animation** (как исчезает):
   - Scale: уменьшается? До 0% или улетает за экран?
   - Position: куда улетает?
   - Opacity: fade-out или резкий cut?
   - Duration: сколько кадров?
   - Easing?

4. **Взаимодействие с битом**:
   - На каком кадре/времени происходит cut/transition?
   - Что происходит на strong beat? (zoom snap, shake, flash, element swap)
   - Какой SFX играет на этом моменте? (whoosh, click, deep hit, pop)

### 3. Структура отчёта
Сохраняй отчёт в `learning/reference_analysis_NAME.md`:

```markdown
# Анализ референса: [название видео]
## Общая информация
- Duration: X секунд, Y кадров @ Z fps
- BPM: [если определён через librosa]
- Структура: [сколько сегментов, хронометраж каждого]

## Сегмент 1: [Название] (0:00-0:03, кадры 0-90)
### Фон / Видео
- Entry: [описание]
- Hold: [описание]
- Exit: [описание]

### Текст "ТЕКСТ"
- Entry: scale 0→120% за 8 кадров с bounce (amp=0.1, freq=2), затем settle до 100% за 4 кадра ease-out
- Position: center screen, Y offset -200px
- Hold: subtle float up/down 5px, pulse scale 100-103%
- Exit: scale 100→80%, opacity 1→0 за 6 кадров, slide left 200px
- Glow: yellow shadow offset (4,4), opacity 60%
- Motion blur: 3 trail layers offset by 3px each

### Иконка / Элемент
- Entry: slide from bottom, scale 0.5→1.0, rotate -15°→0°
- Hold: bounce on beat (scale 1.0→1.1→1.0 every 22 frames)
- Exit: explode scale 1.0→1.5, opacity fade

### Cut/Transition на beat
- Frame 45: hard cut + zoom snap + brightness flash + whoosh SFX
- Frame 46-48: camera shake 3px amplitude, decay over 3 frames

## Сегмент 2: ...
```

### 4. Технические требования
- **ffmpeg:** 8.0.1-full_build (MSYS2)
- **Python:** 3.14
- **Путь workaround:** ВСЕ ffmpeg команды используют `C:/Windows/Temp/pro_v9_safe/refs/` — кириллица в пути ломает filtergraph
- **librosa** установлен для BPM detection
- Используй `Agent(subagent_type="explore")` для поиска файлов в проекте
- НЕ запускай git commit/push без явного разрешения

### 5. Что НЕ делать
- НЕ генерируй видео сам — только анализируй и документируй
- НЕ делай скриншоты через ReadMediaFile и не оставляй их без описания движения
- НЕ пиши общие фразы типа "текст появляется с анимацией" — конкретизируй: scale, duration, easing, direction
- НЕ забудь описать SFX sync — какой звук на каком кадре

### 6. Когда закончишь
1. Сохрани полный отчёт в `learning/reference_analysis_NAME.md`
2. Сохрани key frames (каждые 5-10 кадров) в `assets/gadzhi_sources/references/frames_NAME/`
3. Напиши в первое окно: "Анализ готов, файл: learning/reference_analysis_NAME.md"
4. Кратко перечисли ТОП-5 самых важных motion design паттернов, которые ГЛАВНЫЙ агент должен реализовать
