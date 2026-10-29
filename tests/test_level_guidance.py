import pytest

from ai_gym_td.levels import LEVELS, get_level
from ai_gym_td.live import PlaySession
from ai_gym_td.ui_level_guidance import DIFFICULTY, OPENINGS, RECOMMENDED_ORDER, TIPS
from ai_gym_td.viewer import PygameViewer


def test_opening_references_are_legal_and_affordable():
    assert set(RECOMMENDED_ORDER) == {level.key for level in LEVELS}
    assert len(RECOMMENDED_ORDER) == len(LEVELS)
    for key, opening in OPENINGS.items():
        level = get_level(key)
        assert len({cell for cell, _ in opening}) == 3
        assert all(cell in level.build_sites for cell, _ in opening)
        assert sum(level.factory().towers[name].cost for _, name in opening) == 115


@pytest.mark.parametrize("key", tuple(OPENINGS))
def test_opening_can_be_built_using_normal_manual_commands(key):
    s = PlaySession("manual", fixed_sites=True, level=key)
    try:
        for cell, name in OPENINGS[key]:
            s.command(f"tower:{s.env._tower_names.index(name)}")
            s.click_cell(*cell)
            s.step_once()
            assert not s.info["invalid_action"]
        assert s.game.gold == 5 and s.builds == 3
    finally:
        s.close()


@pytest.mark.parametrize("size", [(1280,720),(1024,576),(1100,800)])
def test_guidance_fits_without_building_or_switching_map(size, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    s = PlaySession("manual", fixed_sites=True)
    v = PygameViewer(s.env.cfg, presentation=True, window_size=size)
    try:
        s.command("levels")
        for level in LEVELS:
            s.command(f"levels:pick:{level.key}")
            v.draw(s.game, fps=0, process_events=False, session=s)
            assert v.ui.assets.font(20).size(TIPS[level.key])[0] <= 984
            assert v.ui.assets.font(18).size("手动难度：" + DIFFICULTY[level.key])[0] <= 187
            assert s.game.gold == 120 and s.builds == 0 and s.level.key == "s_curve"
        s.command("levels:cancel")
        assert not s.game.towers
    finally:
        s.close()
        v.close()
