"""1280x720 Pygame presentation composed around the existing viewer."""
import pygame
from ai_gym_td.ui_text import status_text
from ai_gym_td.ui_assets import AssetBank
from ai_gym_td.ui_layout import GameLayout
from ai_gym_td.ui_world import WorldRenderer
from ai_gym_td.ui_shop import draw_shop, draw_build_feedback
from ai_gym_td.ui_panels import BG, PANEL, TEXT, MUTED, ACCENT, text, draw_hud
from ai_gym_td.ui_levels import draw_level_picker


class GamePresentation:
    def __init__(self, screen, config):
        self.screen=screen
        self.layout=GameLayout(config.width,config.height)
        self.assets=AssetBank()
        self.canvas=pygame.Surface(self.layout.size)
        self.world=WorldRenderer(self.layout,self.assets)
        self.buttons=[]

    def draw(self,game,session):
        self.canvas.fill(BG)
        self.world.draw(self.canvas,game)
        self.buttons=draw_hud(self.canvas,self.assets,self.layout,game,session)
        pointer = self.layout.to_logical(pygame.mouse.get_pos(), self.screen.get_size())
        draw_build_feedback(self.canvas, self.layout, self.assets, game, session, pointer)
        self.buttons.extend(draw_shop(self.canvas, self.assets, self.layout, game, session))
        if session and (session.ended or session.paused):
            box=pygame.Rect(306,296,380,130)
            pygame.draw.rect(self.canvas,PANEL,box,border_radius=12)
            pygame.draw.rect(self.canvas,ACCENT,box,2,border_radius=12)
            label=self.assets.font(38).render(status_text(session.status),True,TEXT)
            self.canvas.blit(label,label.get_rect(center=(box.centerx,box.y+40)))
            hint="R 重开   L 选择关卡   Esc 退出" if session.ended else "P 继续   L 选择关卡   Esc 退出"
            label=self.assets.font(23).render(hint,True,MUTED)
            self.canvas.blit(label,label.get_rect(center=(box.centerx,box.y+86)))
        if session and session.level_menu_open:
            self.buttons = draw_level_picker(self.canvas, self.assets, session)
        viewport=self.layout.viewport(self.screen.get_size())
        self.screen.fill((8,15,22))
        frame=pygame.transform.smoothscale(self.canvas,viewport.size) if viewport.size!=self.layout.size else self.canvas
        self.screen.blit(frame,viewport)
        pygame.display.flip()
