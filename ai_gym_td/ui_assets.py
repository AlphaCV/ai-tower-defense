"""CC0 sprite loading, bounded rotation cache, and visible asset fallbacks."""
import json
import logging
import os
from pathlib import Path

import pygame

ASSET_ROOT = Path(__file__).resolve().parent / "assets"


class AssetBank:
    def __init__(self, root=ASSET_ROOT):
        self.root = Path(root)
        try:
            self.manifest = json.loads((self.root/"manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.manifest = {}
        self.originals, self.cache, self.fonts = {}, {}, {}
        self.missing = set()
        # Use installed fonts directly, avoiding the Windows SysFont registry bug.
        # System fonts are not copied or redistributed with the game.
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        candidates = [
            windows_fonts / "msyh.ttc", windows_fonts / "simhei.ttf",
            windows_fonts / "simsun.ttc",
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        ]
        self.font_path = None
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                probe = pygame.font.Font(str(candidate), 16)
                if all(metric is not None for metric in probe.metrics("金币生命箭塔")):
                    self.font_path = str(candidate)
                    break
            except (OSError, pygame.error):
                continue
        if self.font_path is None:
            logging.warning("Chinese font unavailable; install Microsoft YaHei or Noto Sans CJK.")

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(self.font_path, max(10, round(size * 0.78)) if self.font_path else size)
        return self.fonts[size]

    def image(self, key, size, angle=0):
        size = (size, size) if isinstance(size, int) else tuple(size)
        # At most 32 directions per key/size, independent of game duration.
        angle = round(angle/11.25)*11.25 % 360
        cache_key = (key, size, angle)
        if cache_key not in self.cache:
            if key not in self.originals:
                try:
                    file = self.root/self.manifest[key]["file"]
                    original = pygame.image.load(str(file)).convert_alpha()
                    if key in ("scout", "grunt", "brute", "swarm"):
                        bounds = original.get_bounding_rect()
                        side = max(bounds.width, bounds.height, 1)
                        normalized = pygame.Surface((side, side), pygame.SRCALPHA)
                        normalized.blit(original.subsurface(bounds),
                                        ((side-bounds.width)//2, (side-bounds.height)//2))
                        original = normalized
                    self.originals[key] = original
                except (KeyError, OSError, pygame.error):
                    self.missing.add(key)
                    logging.warning("UI asset missing: %s; using geometric fallback", key)
                    fallback = pygame.Surface((64,64),pygame.SRCALPHA)
                    pygame.draw.rect(fallback,(114,156,158),(5,5,54,54),border_radius=10)
                    pygame.draw.line(fallback,(255,218,136),(18,46),(46,18),4)
                    self.originals[key] = fallback
            sprite = pygame.transform.smoothscale(self.originals[key],size)
            self.cache[cache_key] = pygame.transform.rotate(sprite,angle) if angle else sprite
        return self.cache[cache_key]
