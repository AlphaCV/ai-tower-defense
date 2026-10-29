import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from ai_gym_td.config import GameConfig
from ai_gym_td.engine import TowerDefenseGame
from ai_gym_td.viewer import PygameViewer

def test_font_registry_failure_uses_default(monkeypatch):
    def broken(*args,**kwargs): raise TypeError('non-string registry font')
    monkeypatch.setattr(pygame.font,'SysFont',broken)
    viewer=PygameViewer(GameConfig.default_20x12())
    try: assert viewer.font is not None
    finally: viewer.close()

def test_external_event_owner_keeps_input():
    cfg=GameConfig.default_20x12();viewer=PygameViewer(cfg)
    try:
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_1))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        viewer.draw(TowerDefenseGame(cfg),fps=0,process_events=False)
        events=pygame.event.get()
        assert [e.type for e in events]==[pygame.KEYDOWN,pygame.QUIT]
        assert not viewer.closed
    finally: viewer.close()

def test_quit_and_repeated_draw_are_safe():
    cfg=GameConfig.default_20x12();game=TowerDefenseGame(cfg);viewer=PygameViewer(cfg)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    viewer.draw(game,fps=0)
    assert viewer.closed
    viewer.draw(game,fps=0)
    viewer.close()
