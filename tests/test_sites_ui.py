import pygame
import pytest

from ai_gym_td.live import PlaySession
from ai_gym_td.live_rules import DEFAULT_BUILD_SITES
from ai_gym_td.scripts.play import handle_event
from ai_gym_td.viewer import PygameViewer


@pytest.mark.parametrize("size", [(1280,720), (1024,576), (1100,800)])
def test_click_build_select_sell_rebuild_and_ai_guard(size, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    s = PlaySession(fixed_sites=True)
    v = PygameViewer(s.env.cfg, presentation=True, window_size=size)
    def draw():
        v.draw(s.game, fps=0, session=s, process_events=False)
    def click(command=None, cell=None):
        if cell:
            pos = v.grid_center(*cell)
        else:
            rect = next(r for r,c in v.buttons if c == command)
            vp = v.ui.layout.viewport(size)
            pos = (round(vp.x+rect.centerx*vp.width/1280), round(vp.y+rect.centery*vp.height/720))
        handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos),s,v)
    try:
        draw()
        x,y = DEFAULT_BUILD_SITES[0]
        foundation = v.ui.canvas.get_at(v.ui.layout.center(x,y))
        click(cell=(0,0));s.step_once()
        assert not s.builds and "圆形建造点" in s.message
        click(command="tower:1")
        click(cell=(x,y));s.step_once();draw()
        assert s.game.gold == 65 and s.game.tower_count() == 1
        click(cell=(x,y));draw()
        assert s.selected_tower.spec.name == "cannon" and s.sale_refund == 33
        assert "sell" in [c for _,c in v.buttons]
        click(command="pause");draw()
        assert "sell" not in [c for _,c in v.buttons]
        click(command="pause");click(command="ppo");draw()
        assert "sell" not in [c for _,c in v.buttons]
        click(command="manual");draw()
        click(command="sell");s.step_once();draw()
        assert s.game.gold == 98 and s.game.tower_count() == 0
        assert v.ui.canvas.get_at(v.ui.layout.center(x,y)) == foundation
        assert s.obs["action_mask"][2,y,x]
        click(command="tower:3")
        click(cell=(x,y));s.step_once();draw()
        assert s.game.gold == 18 and s.game.tower_count() == 1
        assert next(iter(s.game.towers.values())).spec.name == "tesla"
        assert all(not rect.colliderect(v.ui.layout.grid_rect) for rect,_ in v.buttons)
    finally:
        s.close();v.close()
