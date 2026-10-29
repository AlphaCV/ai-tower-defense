import random
import numpy as np
import pygame
import pytest
import torch

from ai_gym_td.live import PlaySession
from ai_gym_td.viewer import PygameViewer
from ai_gym_td.scripts.play import handle_event


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    s = PlaySession(seed=42)
    v = PygameViewer(s.env.cfg, presentation=True)
    v.draw(s.game, fps=0, process_events=False, session=s)
    yield s, v
    s.close()
    v.close()


def click(s, v, logical=None, command=None, physical=None):
    if command:
        logical = next(rect.center for rect, cmd in v.buttons if cmd == command)
    if physical is None:
        viewport = v.ui.layout.viewport(v.screen.get_size())
        physical = (round(viewport.x + logical[0]*viewport.width/1280),
                    round(viewport.y + logical[1]*viewport.height/720))
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=physical)
    return handle_event(event, s, v)


@pytest.mark.parametrize("size", [(1280, 720), (1024, 576), (1100, 800)])
def test_shop_build_and_scaled_pointer(window, size):
    s, v = window
    v.resize(size)
    v.draw(s.game, fps=0, process_events=False, session=s)
    for index in range(4):
        assert click(s, v, command=f"tower:{index}")
        assert s.selected == index and s.pending is None
        assert s.game.gold == 120 and s.game.tower_count() == 0
    y, x = map(int, np.argwhere(s.obs["action_mask"][4])[0])
    click(s, v, physical=v.grid_center(x, y))
    s.step_once()
    assert s.game.gold == 40 and s.game.tower_count() == 1
    assert s.last_build == dict(step=1, type="tesla", x=x, y=y, mode="manual")
    previous = s.last_build.copy()
    s.step_once()
    assert s.last_action == "Pass" and s.last_build == previous
    click(s, v, physical=v.grid_center(x, y))
    assert s.pending is None and s.selected_tower.spec.name == "tesla"
    # Sidebar gaps, map border and letterbox must never queue a tower.
    click(s, v, logical=(1000, 508))
    click(s, v, logical=(10, 250))
    if size == (1100, 800):
        click(s, v, physical=(100, 10))
    assert s.pending is None
    click(s, v, command="restart")
    assert s.last_build is None and s.game.gold == 120


def test_buttons_pause_speed_wave_modes_and_exit(window):
    s, v = window
    click(s, v, command="pause")
    assert s.paused
    click(s, v, physical=v.grid_center(0, 0))
    assert s.pending is None
    click(s, v, command="pause")
    click(s, v, command="speed")
    assert s.speed == 1
    click(s, v, command="wave")
    s.step_once()
    assert s.game.phase == "wave" and s.game.wave_number == 1
    v.draw(s.game, fps=0, process_events=False, session=s)
    assert "wave" not in [cmd for _, cmd in v.buttons]
    for mode in ("ppo", "rule", "random", "manual"):
        game = s.game
        click(s, v, command=mode)
        assert s.mode == mode and s.game is game
        s.step_once()
        assert not s.info["invalid_action"]
    assert click(s, v, command="exit") is False


def test_full_presentation_does_not_change_policy_rng_or_state(window):
    s, v = window
    s.set_mode("ppo")
    for _ in range(200):
        s.step_once()
    before = s.game.snapshot()
    torch_state = torch.get_rng_state().clone()
    py_state = random.getstate()
    np_state = np.random.get_state()
    for _ in range(3):
        v.draw(s.game, fps=0, process_events=False, session=s)
    assert s.game.snapshot() == before
    assert torch.equal(torch.get_rng_state(), torch_state)
    assert random.getstate() == py_state
    assert np.array_equal(np.random.get_state()[1], np_state[1])
    assert not v.ui.assets.missing
    assert all(not rect.colliderect(v.ui.layout.grid_rect) for rect, _ in v.buttons)


def test_filtered_action_is_not_reported_as_a_build(window):
    s, v = window
    class InvalidAgent:
        def act(self, obs, info):
            x, y = s.game.spawn
            return np.array([1, y, x])
    s.agents["rule"] = InvalidAgent()
    s.set_mode("rule")
    s.step_once()
    v.draw(s.game, fps=0, process_events=False, session=s)
    assert s.last_build is None and s.filtered == 1 and s.builds == 0
