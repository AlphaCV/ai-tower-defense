import random
import numpy as np
import pygame

from ai_gym_td.env import TowerDefenseEnv
from ai_gym_td.ui_assets import AssetBank
from ai_gym_td.ui_layout import GameLayout
from ai_gym_td.ui_world import WorldRenderer
from ai_gym_td.ui_panels import draw_hud


def test_render_is_read_only_and_does_not_consume_randomness():
    pygame.init();pygame.display.set_mode((1280,720))
    env=TowerDefenseEnv(render_mode=None);env.reset(seed=42)
    env.game.build_tower(0,0,"archer");env.game.start_next_wave()
    for _ in range(20):env.step([0,0,0])
    bank=AssetBank();layout=GameLayout();renderer=WorldRenderer(layout,bank)
    canvas=pygame.Surface(layout.size)
    before=env.game.snapshot()
    random_state=random.getstate();np_state=np.random.get_state()
    renderer.draw(canvas,env.game)
    terrain=renderer.terrain
    draw_hud(canvas,bank,layout,env.game,None)
    renderer.draw(canvas,env.game)
    assert env.game.snapshot()==before
    assert random.getstate()==random_state
    assert np.array_equal(np.random.get_state()[1],np_state[1])
    assert renderer.terrain is terrain
    assert not bank.missing
    assert canvas.get_at(layout.center(0,0))!=canvas.get_at(layout.center(10,0))
    tower_pixel=canvas.get_at(layout.center(0,0))
    env.reset(seed=42);renderer.draw(canvas,env.game)
    assert renderer.terrain is terrain
    assert canvas.get_at(layout.center(0,0)) != tower_pixel
    env.close();pygame.quit()
