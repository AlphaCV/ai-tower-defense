import pygame
import pytest
from ai_gym_td.live import PlaySession
from ai_gym_td.viewer import PygameViewer
from ai_gym_td.scripts.play import handle_event


@pytest.mark.parametrize('size',[(1280,720),(1024,576),(1100,800)])
def test_real_buttons_preview_upgrade_full_level_refund_and_guards(size,monkeypatch):
    monkeypatch.setenv('SDL_VIDEODRIVER','dummy')
    s=PlaySession(fixed_sites=True,speed=1)
    v=PygameViewer(s.env.cfg,presentation=True,window_size=size)
    def draw():
        before=s.game.snapshot();spec=s.selected_tower.spec if s.selected_tower else None
        v.draw(s.game,fps=0,process_events=False,session=s)
        assert s.game.snapshot()==before
        if spec:assert s.selected_tower.spec is spec
    def click(command=None,cell=None):
        if cell is not None:pos=v.grid_center(*cell)
        else:
            rect=next(r for r,c in v.buttons if c==command)
            vp=v.ui.layout.viewport(v.screen.get_size())
            pos=(round(vp.x+rect.centerx*vp.width/1280),round(vp.y+rect.centery*vp.height/720))
        handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos),s,v)
    def commands():return [c for _,c in v.buttons]
    try:
        draw();cell=s.level.build_sites[0]
        click(cell=cell);s.step_once();click(cell=cell);draw()
        tid=s.selected_tid
        assert 'upgrade' in commands() and s.upgrade_quote[2].damage==12
        click('pause');draw();assert 'upgrade' not in commands() and 'sell' not in commands()
        click('pause');click('rule');draw();assert 'upgrade' not in commands()
        click('manual');draw();click('upgrade');click('upgrade');s.step_once();draw()
        assert s.game.tower_level(tid)==2 and s.game.gold==50 and s.sale_refund==42
        assert s.upgrade_quote[2].damage==16.8
        assert 'upgrade' not in commands()
        s.command('upgrade')
        s.step_once()
        assert s.game.gold==50 and s.game.tower_level(tid)==2
        # Controlled unit-test balance to exercise the level-3 button and refund.
        # Native-window verification uses only normal starting resources.
        s.game._gold = 120
        draw()
        click('upgrade');s.step_once();draw()
        assert s.game.tower_level(tid)==3 and s.game.gold==0 and s.sale_refund==114
        assert 'upgrade' not in commands()
        assert all(not r.colliderect(v.ui.layout.grid_rect) for r,_ in v.buttons)
        click('sell');s.step_once();draw()
        assert s.game.gold==114 and not s.game.towers and 'tower:1' in commands()
        click('tower:1');click(cell=cell);s.step_once();click(cell=cell);draw()
        assert s.game.gold==59 and s.upgrade_quote[1]==180 and 'upgrade' not in commands()
        click('deselect');draw();assert 'tower:0' in commands()
        click('restart');draw()
        assert s.upgrades==0 and not s.game._tower_levels and s.game.gold==120
    finally:s.close();v.close()
