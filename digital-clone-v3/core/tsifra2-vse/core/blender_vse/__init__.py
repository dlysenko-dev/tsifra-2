#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blender VSE Video Editor Package
================================

Пакет для создания видео через Blender Video Sequence Editor (VSE).
Поддерживает загрузку клипов, текстовые анимации, цветокоррекцию,
переходы и рендер в MP4.

Blender 4.x compatible
"""

from .editor import BlenderVSEEditor

__version__ = "1.0.0"
__all__ = ["BlenderVSEEditor"]
