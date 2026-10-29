"""Run unchanged combat and verify each tower deals damage while being rendered."""
import pygame
import pytest

from ai_gym_td.config import GameConfig
from ai_gym_td.engine import TowerDefenseGame
from ai_gym_td.ui_assets import AssetBank
from ai_gym_td.ui_layout import GameLayout
from ai_gym_td.ui_world import WorldRenderer


@pytest.mark.parametrize("name", ["archer", "cannon", "ice", "tesla"])
def test_each_tower_attacks_and_render_preserves_combat(name, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1280, 720))
    cfg = GameConfig.straight_path()
    a, b = TowerDefenseGame(cfg, seed=42), TowerDefenseGame(cfg, seed=42)
    for game in (a, b):
        assert game.build_tower(4, 5, name) is not None
        assert game.gold == cfg.starting_gold - cfg.towers[name].cost
        game.start_next_wave()
    renderer = WorldRenderer(GameLayout(), AssetBank())
    surface = pygame.Surface((1280, 720))
    damaged = False
    slow = False
    for _ in range(300):
        a.step(1/cfg.tick_rate)
        b.step(1/cfg.tick_rate)
        damaged |= any(enemy.hp < enemy.max_hp for enemy in a.enemies.values())
        slow |= any(enemy.slow_mult < 1 for enemy in a.enemies.values())
        renderer.draw(surface, a)
    assert damaged and next(iter(a.towers.values())).shots_fired > 0
    assert a.snapshot() == b.snapshot()
    if name == "ice":
        assert slow
    pygame.quit()
