"""Presentation-only HUD. All button commands are handled by PlaySession."""
import pygame
from ai_gym_td.ui_text import MODE_NAMES, status_text

BG=(17,28,38)
PANEL=(25,40,51)
TEXT=(232,239,232)
MUTED=(154,178,182)
ACCENT=(111,217,186)


def text(surface,bank,value,pos,size=22,color=TEXT):
    image=bank.font(size).render(str(value),True,color)
    surface.blit(image,pos)


def button(surface,bank,label,rect,active=False,disabled=False):
    color=(45,99,87) if active else (39,60,72)
    if disabled:color=(29,44,52)
    pygame.draw.rect(surface,color,rect,border_radius=7)
    pygame.draw.rect(surface,ACCENT if active else (61,82,90),rect,1,border_radius=7)
    image=bank.font(21).render(label,True,MUTED if disabled else TEXT)
    surface.blit(image,image.get_rect(center=rect.center))


def draw_hud(surface,bank,layout,game,session):
    buttons=[]
    pygame.draw.rect(surface,PANEL,(0,0,1280,72))
    pygame.draw.line(surface,(63,87,88),(0,71),(1280,71))
    sprite=bank.image("archer",50)
    surface.blit(sprite,(17,9))
    text(surface,bank,"AI 智能塔防",(78,15),27)
    subtitle = f"固定建造点：{game.tower_count()} / {len(game.build_sites)}" if hasattr(game, "build_sites") else "自由建造 · 对照模式"
    text(surface,bank,subtitle,(79,43),16,MUTED)
    for x,title,value,color in [
        (270,"金币",game.gold,(242,209,128)),
        (377,"生命",int(game.lives),(246,156,143)),
        (482,"波次",f"{game.wave_number:02}/{game.cfg.max_waves}",TEXT)]:
        text(surface,bank,title,(x,12),16,MUTED)
        text(surface,bank,value,(x,32),30,color)
    mode=MODE_NAMES[session.mode] if session else "观察模式"
    text(surface,bank,"控制模式",(600,12),16,MUTED)
    text(surface,bank,mode,(600,34),24,ACCENT)
    if session:
        controls=[("继续" if session.paused else "暂停","pause",800,94),
                  ("重新开始","restart",904,104),(f"{session.speed} 倍速","speed",1018,112),
                  ("退出","exit",1140,124)]
        for title,command,x,width in controls:
            rect=pygame.Rect(x,18,width,38)
            button(surface,bank,title,rect,active=command=="pause" and session.paused)
            buttons.append((rect,command))
        for i,(label,mode) in enumerate([("F1 手动","manual"),("F2 PPO","ppo"),("F3 规则","rule"),("F4 随机","random")]):
            rect=pygame.Rect(16+i*114,679,106,29)
            button(surface,bank,label,rect,session.mode==mode)
            buttons.append((rect,mode))
        rect = pygame.Rect(480, 679, 246, 29)
        button(surface, bank, f"{session.level.name} · 选关 [L]", rect)
        buttons.append((rect, "levels"))
        text(surface,bank,"P 暂停   R 重开   S 倍速",(752,684),17,MUTED)
        text(surface,bank,f"步数 {session.steps}  |  {status_text(session.status)}",(998,684),17,ACCENT)
    return buttons
