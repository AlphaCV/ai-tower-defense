"""Optional Pygame viewer for interactive play and live training visualization.

Importing this module is safe even if pygame is not installed — it raises a
clear ImportError only when `PygameViewer` is instantiated.
"""

from __future__ import annotations

from typing import Optional, Tuple

from ai_gym_td.config import GameConfig, TILE_BASE, TILE_BLOCKED, TILE_GRASS, TILE_PATH, TILE_SPAWN
from ai_gym_td.engine import TowerDefenseGame


PALETTE = {
    TILE_GRASS: (52, 96, 58),
    TILE_PATH: (170, 150, 110),
    TILE_SPAWN: (200, 110, 80),
    TILE_BASE: (110, 150, 220),
    TILE_BLOCKED: (70, 70, 80),
}


class PygameViewer:
    """Interactive pygame window for `render_mode='human'` or manual play."""

    def __init__(self, config: GameConfig, cell_px: int = 36, hud_height: int = 56, caption: str = "AI Gym Tower Defense", *, presentation=False, window_size=(1280,720)):
        try:
            import pygame  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "PygameViewer requires pygame. Install with `pip install pygame`."
            ) from e
        import pygame

        self.presentation = presentation
        self.buttons = []
        self.closed = False
        self.pygame = pygame
        self.cfg = config
        self.cell = cell_px
        self.W = config.width * cell_px
        self.H = config.height * cell_px + hud_height
        self.hud_h = hud_height

        pygame.init()
        pygame.display.set_caption(caption)
        self.screen = pygame.display.set_mode(window_size, pygame.RESIZABLE) if presentation else pygame.display.set_mode((self.W, self.H))
        self.clock = pygame.time.Clock()
        self.ui_font = pygame.font.Font(None, 22)
        font_size = max(12, cell_px // 3)
        try:
            self.font = pygame.font.SysFont("consolas", font_size)
        except (TypeError, OSError, pygame.error):
            # Some Windows font registry entries are not path strings.
            self.font = pygame.font.Font(None, font_size)
        if presentation:
            from ai_gym_td.ui_view import GamePresentation
            self.ui = GamePresentation(self.screen, config)
            self.cell = self.ui.layout.cell
            self.W, self.H = self.ui.layout.size

    def draw(self, game: TowerDefenseGame, fps: int = 30, *, process_events: bool = True, session=None) -> None:
        if self.closed:
            return
        pygame = self.pygame
        if process_events:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return

        if self.presentation:
            self.ui.draw(game, session)
            self.buttons = self.ui.buttons
            self.clock.tick(fps)
            return

        self.screen.fill((20, 22, 28))

        # Grid
        for y in range(self.cfg.height):
            for x in range(self.cfg.width):
                code = game.grid[y][x]
                color = PALETTE.get(code, (0, 0, 0))
                if code == TILE_GRASS and (x + y) % 2 == 1:
                    color = tuple(max(0, c - 10) for c in color)
                rect = pygame.Rect(x * self.cell, y * self.cell, self.cell, self.cell)
                pygame.draw.rect(self.screen, color, rect)

        # Path arrows
        if len(game.path) >= 2:
            for i in range(0, len(game.path) - 1, 2):
                ax, ay = game.path[i]
                bx, by = game.path[i + 1]
                p1 = (ax * self.cell + self.cell // 2, ay * self.cell + self.cell // 2)
                p2 = (bx * self.cell + self.cell // 2, by * self.cell + self.cell // 2)
                pygame.draw.line(self.screen, (220, 210, 180), p1, p2, 2)

        # Towers
        for t in game.towers.values():
            cx = t.x * self.cell + self.cell // 2
            cy = t.y * self.cell + self.cell // 2
            r = self.cell // 2 - 2
            pygame.draw.circle(self.screen, t.spec.color, (cx, cy), r)
            pygame.draw.circle(self.screen, (10, 10, 12), (cx, cy), r, 2)
            if t.target_eid is not None and session is None:
                rr = int(t.spec.range * self.cell)
                pygame.draw.circle(self.screen, t.spec.color, (cx, cy), rr, 1)
            label = self.font.render(t.spec.symbol, True, (20, 20, 24))
            self.screen.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))

        # Enemies
        for e in game.enemies.values():
            cx = int((e.x + 0.5) * self.cell)
            cy = int((e.y + 0.5) * self.cell)
            r = int(e.spec.radius * self.cell)
            pygame.draw.circle(self.screen, e.spec.color, (cx, cy), r)
            # HP bar
            bar_w = self.cell - 4
            bar_h = max(2, self.cell // 10)
            bx = cx - bar_w // 2
            by = cy - r - bar_h - 2
            pygame.draw.rect(self.screen, (30, 30, 34), (bx, by, bar_w, bar_h))
            frac = max(0.0, min(1.0, e.hp / e.max_hp if e.max_hp else 0.0))
            color = (120, 220, 120) if frac > 0.5 else (230, 80, 80)
            pygame.draw.rect(self.screen, color, (bx, by, int(bar_w * frac), bar_h))

        # Projectiles
        for p in game.projectiles.values():
            cx = int(p.x * self.cell)
            cy = int(p.y * self.cell)
            pygame.draw.circle(self.screen, (255, 230, 120), (cx, cy), 3)

        if session is None:
            # HUD
            hud_y = self.cfg.height * self.cell
            pygame.draw.rect(self.screen, (14, 16, 20), (0, hud_y, self.W, self.hud_h))
            hud_text = (
                f"Wave {game.wave_number}/{self.cfg.max_waves}   "
                f"Gold {game.gold}   "
                f"Lives {int(game.lives)}   "
                f"Enemies {game.active_enemy_count()}   "
                f"Towers {game.tower_count()}   "
                f"Phase {game.phase}"
            )
            label = self.font.render(hud_text, True, (240, 240, 240))
            self.screen.blit(label, (8, hud_y + 8))
            if game.is_terminal:
                msg = "VICTORY" if game.phase == TowerDefenseGame.WON else "DEFEAT"
                big = self.font.render(msg, True, (255, 220, 80))
                self.screen.blit(big, ((self.W - big.get_width()) // 2, hud_y + 28))

        else:
            self._draw_dashboard(session)

        pygame.display.flip()
        self.clock.tick(fps)

    def _draw_dashboard(self, session):
        pygame = self.pygame
        game = session.game
        y = self.cfg.height * self.cell
        pygame.draw.rect(self.screen, (17, 24, 34), (0, y, self.W, self.hud_h))
        def label(text, row, color=(225, 234, 242), x=12):
            while self.ui_font.size(text)[0] > self.W - x - 12 and len(text) > 3:
                text = text[:-4] + "..."
            self.screen.blit(self.ui_font.render(text, True, color), (x, row))
        label(f"Wave {game.wave_number}/{self.cfg.max_waves}    Lives {int(game.lives)}"
              f"    Gold {game.gold}    Towers {game.tower_count()}    Enemies {game.active_enemy_count()}", y+10)
        mode = "PPO + legality filter" if session.mode == "ppo" else session.mode.upper()
        label(f"{mode}  |  {session.status}  |  {session.speed}x  |  Seed {session.seed}"
              f"  |  Step {session.steps}/{session.env.max_env_steps}", y+34, (109, 219, 198))
        self.buttons = []
        def button(text, command, index, count, row, active=False):
            width = (self.W - 24) // count
            rect = pygame.Rect(12 + index * width, row, width - 6, 30)
            pygame.draw.rect(self.screen, (34, 100, 93) if active else (43, 56, 72), rect, border_radius=5)
            img = self.ui_font.render(text, True, (245, 248, 250))
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons.append((rect, command))
        controls = [("Manual", "manual"), ("PPO", "ppo"), ("Rule", "rule"), ("Random", "random"),
                    ("Resume" if session.paused else "Pause", "pause"), ("Restart", "restart"),
                    (f"{session.speed}x speed", "speed")]
        for i, (title, command) in enumerate(controls):
            button(title, command, i, 7, y+60, command == session.mode or (command == "pause" and session.paused))
        for i, name in enumerate(session.env._tower_names):
            button(f"{i+1} {name.title()} {self.cfg.towers[name].cost}g", f"tower:{i}", i, 5, y+98,
                   session.mode == "manual" and i == session.selected)
        button("Next wave", "wave", 4, 5, y+98)
        label(f"{session.last_action}  |  AI {session.inference_ms:.2f} ms"
              f"  |  Filtered {session.filtered}  |  Reward {session.reward:.1f}", y+141)
        label("F1-F4 Mode   TAB Manual/PPO   P Pause   R Restart   S Speed   ESC Exit", y+165, (160, 180, 202))
        label(session.message or "Manual: 1-4 select tower, click grass to build; SPACE starts next wave.",
              y+189, (244, 197, 115) if session.message else (160, 180, 202))
        if session.ended or session.paused:
            box = pygame.Rect((self.W-380)//2, (y-86)//2, 380, 86)
            pygame.draw.rect(self.screen, (17, 24, 34), box, border_radius=10)
            hint = "R: restart   ESC: exit" if session.ended else "P: resume   R: restart   ESC: exit"
            for text, offset in [(session.status, 18), (hint, 49)]:
                img = self.ui_font.render(text, True, (245, 213, 132))
                self.screen.blit(img, img.get_rect(midtop=(box.centerx, box.y+offset)))

    def logical_position(self, position):
        if self.presentation:
            return self.ui.layout.to_logical(position, self.screen.get_size())
        return position

    def grid_position(self, position):
        if self.presentation:
            return self.ui.layout.grid_at(self.logical_position(position))
        x, y = position
        if 0 <= x < self.W and 0 <= y < self.cfg.height * self.cell:
            return int(x // self.cell), int(y // self.cell)
        return None

    def grid_center(self, x, y):
        if not self.presentation:
            return round((x + 0.5) * self.cell), round((y + 0.5) * self.cell)
        px, py = self.ui.layout.center(x, y)
        view = self.ui.layout.viewport(self.screen.get_size())
        return round(view.x + px * view.width / 1280), round(view.y + py * view.height / 720)

    def resize(self, size):
        if self.presentation:
            self.screen = self.pygame.display.set_mode((max(640, size[0]), max(360, size[1])), self.pygame.RESIZABLE)
            self.ui.screen = self.screen

    def close(self) -> None:
        self.closed = True
        try:
            self.pygame.quit()
        except Exception:
            pass


__all__ = ["PygameViewer"]
