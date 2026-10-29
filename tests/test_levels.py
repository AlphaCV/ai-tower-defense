import numpy as np
import pygame
import pytest

from ai_gym_td.config import TILE_GRASS, GameConfig
from ai_gym_td.engine import TowerDefenseGame
from ai_gym_td.levels import LEVELS
from ai_gym_td.live import PlaySession
from ai_gym_td.live_rules import LiveDefenseEnv
from ai_gym_td.scripts.play import handle_event
from ai_gym_td.viewer import PygameViewer
from ai_gym_td.ui_levels import description_lines


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.key)
def test_paths_sites_and_manual_sale(level):
    cfg = level.factory()
    assert (cfg.width, cfg.height) == (20, 12)
    assert len(cfg.path) == len(set(cfg.path))
    assert all(abs(x-a)+abs(y-b) == 1 for (x,y),(a,b) in zip(cfg.path,cfg.path[1:]))
    assert TowerDefenseGame(cfg).path == cfg.path  # No shortcuts through adjacent roads.
    assert len(set(level.build_sites)) == len(level.build_sites)
    s = PlaySession(fixed_sites=True, level=level.key)
    try:
        for x,y in level.build_sites:
            assert s.game.grid[y][x] == TILE_GRASS and s.obs["action_mask"][1,y,x]
        assert s.obs["action_mask"][1].sum() == len(level.build_sites)
        x,y = level.build_sites[0]
        s.click_cell(x,y);s.step_once()
        assert s.game.gold == 95 and s.game.tower_count() == 1
        s.click_cell(x,y);s.command("sell");s.step_once()
        assert s.game.gold == 110 and not s.game.towers
        assert s.obs["action_mask"][1,y,x]
        s.command("restart")
        assert s.level == level and s.game.gold == 120 and s.game.path == cfg.path
    finally:
        s.close()


def test_switch_resets_pending_state_and_recomputes_observation():
    s = PlaySession("ppo", fixed_sites=True)
    model = s.agents["ppo"]
    try:
        s.set_mode("manual")
        s.click_cell(*s.level.build_sites[0]);s.step_once()
        s.click_cell(*s.level.build_sites[0]);s.command("sell")
        s.set_mode("ppo")
        for level in LEVELS[1:]:
            s.switch_level(level.key)
            assert s.mode == "ppo" and s.agents["ppo"] is model
            assert s.seed == 42 and s.speed == 4
            assert s.steps == s.builds == s.sales == 0
            assert s.pending is s.pending_sale is s.selected_tid is None
            assert s.game.gold == 120 and not s.game.towers
            reference = LiveDefenseEnv(config=level.factory(),build_sites=level.build_sites)
            try:
                obs,_ = reference.reset(seed=42)
                for key in obs:
                    np.testing.assert_array_equal(s.obs[key],obs[key])
            finally:
                reference.close()
            for _ in range(100):
                s.step_once()
            assert s.mode == "ppo" and s.builds > 0
            assert all((t.x,t.y) in level.build_sites for t in s.game.towers.values())
        env = s.env
        with pytest.raises(ValueError):
            s.switch_level("bad")
        assert s.env is env
    finally:
        s.close()


@pytest.mark.parametrize("size", [(1280,720),(1024,576),(1100,800)])
def test_level_picker_clicks_keyboard_pause_and_no_clickthrough(size, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER","dummy")
    s = PlaySession(fixed_sites=True)
    v = PygameViewer(s.env.cfg,presentation=True,window_size=size)
    def draw():
        v.draw(s.game,fps=0,process_events=False,session=s)
    def key(key):
        return handle_event(pygame.event.Event(pygame.KEYDOWN,key=key),s,v)
    def click(cmd):
        rect = next(r for r,c in v.buttons if c == cmd)
        vp = v.ui.layout.viewport(size)
        pos = (round(vp.x+rect.centerx*vp.width/1280),round(vp.y+rect.centery*vp.height/720))
        handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos),s,v)
    try:
        draw();click("levels");draw()
        assert s.level_menu_open
        cards = [r for r,c in v.buttons if c.startswith("levels:pick:")]
        assert len(cards) == len(LEVELS)
        assert all(pygame.Rect(0,0,1280,720).contains(r) for r in cards)
        assert all(not a.colliderect(b) for i,a in enumerate(cards) for b in cards[i+1:])
        for rect,level in zip(cards,LEVELS):
            lines = description_lines(v.ui.assets, level.description, rect.width-40)
            assert len(lines) <= 2 and "".join(lines) == level.description
            assert all(line[0] not in "，。；：！？、" for line in lines)
            assert all(v.ui.assets.font(17).size(line)[0] <= rect.width-40 for line in lines)
            assert v.ui.assets.font(24).size(f"05  {level.name}")[0] <= rect.width-40
        key(pygame.K_5)
        assert s.level_choice == "canyon_relay" and s.level.key == "s_curve"
        key(pygame.K_4)
        assert s.level_choice == "double_garden" and s.level.key == "s_curve"
        s.advance(1);s.step_once();s.click_cell(*s.level.build_sites[0]);key(pygame.K_SPACE)
        assert s.steps == 0 and s.pending is None and s.game.wave_number == 0
        click("levels:pick:straight");draw()
        assert s.level.key == "s_curve" and s.level_choice == "straight"
        assert key(pygame.K_ESCAPE) and not s.level_menu_open
        assert s.level.key == "s_curve" and not s.paused
        s.command("pause");key(pygame.K_l);draw();click("levels:cancel")
        assert s.paused
        for index,level in enumerate(LEVELS):
            draw();click("levels");draw()
            if index == 1:
                key(pygame.K_2);key(pygame.K_RETURN)
            else:
                click(f"levels:pick:{level.key}");draw();click("levels:start")
            draw()
            assert s.level == level and not s.level_menu_open and not s.paused
            assert v.ui.world._grid is s.game.grid
            assert not s.game.towers and s.steps == 0
            assert all(not r.colliderect(v.ui.layout.grid_rect) for r,_ in v.buttons)
        assert not key(pygame.K_ESCAPE)
    finally:
        s.close();v.close()


def test_free_build_level_switch_preserves_opt_out():
    s = PlaySession(fixed_sites=False)
    try:
        for level in LEVELS:
            s.switch_level(level.key)
            assert s.env.build_sites is None
            assert s.obs["action_mask"][1].sum() > len(level.build_sites)
    finally:
        s.close()


def test_double_garden_preserves_rules_and_requires_multiple_defense_zones():
    from ai_gym_td.levels import get_level
    level = get_level("double_garden")
    cfg = level.factory()
    baseline = GameConfig.default_20x12()
    for key in vars(baseline):
        if key not in ("path", "blocked_cells", "map_name"):
            assert getattr(cfg,key) == getattr(baseline,key)
    assert len(cfg.path) == 59 and len(level.build_sites) == 10
    assert cfg.path[0] == (0,2) and cfg.path[-1] == (19,9)
    # Even a maximum-range archer cannot cover the whole road from any build site.
    for x,y in level.build_sites:
        covered = sum((x-px)**2+(y-py)**2 <= 3.6**2 for px,py in cfg.path)
        assert 0 < covered < len(cfg.path) / 2
    cfg.path.clear()
    assert len(level.factory().path) == 59


def test_canyon_relay_preserves_rules_and_distributed_coverage():
    from ai_gym_td.levels import get_level
    level = get_level("canyon_relay")
    cfg = level.factory()
    baseline = GameConfig.default_20x12()
    for key in vars(baseline):
        if key not in ("path", "blocked_cells", "map_name"):
            assert getattr(cfg, key) == getattr(baseline, key)
    assert len(cfg.path) == 42 and len(level.build_sites) == 9
    assert cfg.path[0] == (0, 1) and cfg.path[-1] == (19, 9)
    for x, y in level.build_sites:
        covered = sum((x-px)**2+(y-py)**2 <= 3.6**2 for px, py in cfg.path)
        assert 0 < covered < len(cfg.path) / 2
    cfg.path.clear()
    assert len(level.factory().path) == 42
