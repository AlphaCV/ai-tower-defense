"""Shop and build feedback; values and legality come from the live environment."""
import pygame

from ai_gym_td.ui_panels import PANEL, TEXT, MUTED, ACCENT, text, button
from ai_gym_td.ui_world import TOWER_COLORS
from ai_gym_td.ui_text import TOWER_NAMES, status_text, message_text, wrap_lines


def wrapped_text(surface, bank, value, rect, size=18, color=MUTED):
    """Wrap Chinese messages within the available sidebar height."""
    font = bank.font(size)
    y = rect.y
    for line in wrap_lines(value, font, rect.width):
        if y + font.get_height() > rect.bottom:
            return
        text(surface, bank, line, (rect.x, y), size, color)
        y += font.get_linesize()


def draw_shop(surface, bank, layout, game, session):
    buttons = []
    pygame.draw.rect(surface, PANEL, layout.shop_rect, border_radius=10)
    if session and session.selected_tower:
        return draw_tower_details(surface, bank, game, session)
    text(surface, bank, "炮塔商店", (1008, 103), 25)
    manual = session is not None and session.mode == "manual"
    text(surface, bank, ("点圆台建塔；点炮塔升级/出售" if hasattr(game, "build_sites") else "点草地建塔；点炮塔升级/出售") if manual else
         "AI 自动建造，卡片仅供查看", (1008, 129), 17, MUTED)
    for index, (name, spec) in enumerate(game.cfg.towers.items()):
        rect = pygame.Rect(1008, 153 + 86 * index, 240, 78)
        selected = session is not None and session.selected == index
        affordable = game.gold >= spec.cost
        pygame.draw.rect(surface, (35, 58, 65) if selected else (30, 47, 57),
                         rect, border_radius=8)
        pygame.draw.rect(surface, TOWER_COLORS[name] if selected else (55, 73, 81),
                         rect, 2 if selected else 1, border_radius=8)
        sprite = bank.image(name, 42)
        surface.blit(sprite, (rect.x + 7, rect.y + 11))
        text(surface, bank, f"{index+1}  {TOWER_NAMES[name]}", (rect.x + 55, rect.y + 9), 23)
        price = bank.font(21).render(str(spec.cost) + " 金币", True,
                                     (242, 209, 128) if affordable else (241, 145, 132))
        surface.blit(price, (rect.right - price.get_width() - 10, rect.y + 11))
        text(surface, bank, f"伤害 {spec.damage:g}  射程 {spec.range:g}",
             (rect.x + 55, rect.y + 34), 17, MUTED)
        detail = {"archer": "单体", "cannon": f"范围 {spec.splash:g}",
                  "ice": f"减速 {int(spec.slow*100)}%", "tesla": f"连锁 +{spec.chain}"}[name]
        text(surface, bank, f"间隔 {1/spec.fire_rate:.2f}秒 · {detail}",
             (rect.x + 55, rect.y + 55), 17, MUTED)
        # All cards remain inspectable. queue_build is the sole legality gate.
        if session:
            buttons.append((rect, f"tower:{index}"))
    if not session:
        return buttons

    pygame.draw.line(surface, (61, 82, 90), (1008, 506), (1248, 506))
    text(surface, bank, "AI 实时动作" if not manual else "建造操作", (1008, 516), 19, ACCENT)
    text(surface, bank, f"炮塔 {game.tower_count()} 座  /  敌人 {game.active_enemy_count()} 个",
         (1008, 538), 18, MUTED)
    if session.last_build:
        build = session.last_build
        text(surface, bank, f"最近：{TOWER_NAMES[build['type']]} ({build['x']}, {build['y']})",
             (1008, 560), 20, TOWER_COLORS[build["type"]])
    else:
        text(surface, bank, "最近：尚未建造炮塔", (1008, 560), 19, MUTED)
    if manual:
        spec = list(game.cfg.towers.values())[session.selected]
        hint = message_text(session.message) or (
            f"还需要 {spec.cost-game.gold} 金币。" if game.gold < spec.cost else
            f"已选{TOWER_NAMES[spec.name]}，点击空闲" + ("圆台建造。" if hasattr(game, "build_sites") else "草地建造。"))
        wrapped_text(surface, bank, hint, pygame.Rect(1008, 585, 240, 39), 17)
        enabled = game.phase == "build" and not session.paused and not session.ended
        rect = pygame.Rect(1008, 629, 240, 25)
        button(surface, bank, "空格 / 开始下一波" if enabled else
               "敌人进攻中" if game.phase == "wave" else status_text(session.status), rect, disabled=not enabled)
        if enabled:
            buttons.append((rect, "wave"))
    else:
        wrapped_text(surface, bank, message_text(session.message or session.last_action),
                     pygame.Rect(1008, 585, 240, 39), 17)
        text(surface, bank, f"决策 {session.inference_ms:.1f} ms · 过滤 {session.filtered} 次",
             (1008, 635), 18, MUTED)
    return buttons


def draw_tower_details(surface, bank, game, session):
    tower = session.selected_tower
    spec = tower.spec
    level = game.tower_level(tower.tid)
    quote = session.upgrade_quote
    next_spec = quote[2] if quote else None
    enabled = session.mode == "manual" and not session.paused and not session.ended and not session.level_menu_open
    text(surface, bank, "炮塔详情", (1008, 103), 25)
    text(surface, bank, "升级预览 · 最多 3 级", (1008, 132), 18, MUTED)
    pygame.draw.rect(surface, (35,58,65), (1008,164,240,66), border_radius=8)
    surface.blit(bank.image(spec.name, 50), (1012,170))
    text(surface, bank, f"{TOWER_NAMES[spec.name]} · {level} 级", (1072,171), 24, ACCENT)
    text(surface, bank, f"累计投入 {spec.cost} 金币", (1072,201), 17, MUTED)
    for label,x in (("属性",1008),("当前",1106),("下一级",1174)):
        text(surface,bank,label,(x,247),18,MUTED)
    rows = [("伤害", "damage", "number"), ("射程", "range", "number"), ("攻击间隔（秒）", "fire_rate", "interval")]
    if spec.name == "cannon": rows.append(("溅射范围", "splash", "number"))
    elif spec.name == "ice": rows.extend((("减速幅度", "slow", "slow"),("持续秒数", "slow_duration", "number")))
    elif spec.name == "tesla": rows.append(("额外连锁", "chain", "number"))
    for i,(label,attr,fmt) in enumerate(rows):
        y = 277 + i*28
        def value(s):
            if s is None: return "—"
            n = getattr(s,attr)
            if fmt == "interval": return f"{1/n:.2f}"
            return f"{round((1-n)*100)}%" if fmt == "slow" else f"{n:g}"
        text(surface,bank,label,(1008,y),17,MUTED)
        text(surface,bank,value(spec),(1106,y),18)
        text(surface,bank,value(next_spec),(1174,y),18,ACCENT)
    text(surface,bank,"出售返还累计投入的 60%",(1008,433),17,MUTED)
    if not enabled:
        hint = "对局已结束" if session.ended else "请先继续游戏再升级或出售" if session.paused else "按 F1 切回手动后可升级或出售"
    elif quote is None:
        hint = "已达最高等级，可出售后换塔。"
    elif game.gold < quote[1]:
        hint = f"升级还需要 {quote[1]-game.gold} 金币。"
    else:
        hint = session.message or "升级提升当前炮塔的战斗属性。"
    wrapped_text(surface,bank,hint,pygame.Rect(1008,464,240,55),18)
    upgrade = pygame.Rect(1008,535,240,42)
    sell = pygame.Rect(1008,593,151,31)
    cancel = pygame.Rect(1167,593,81,31)
    affordable = quote is not None and game.gold >= quote[1]
    button(surface,bank,f"升级至 {quote[0]} 级 · {quote[1]} 金币" if quote else "已满级 · 3 级",upgrade,
           active=enabled and affordable,disabled=not (enabled and affordable))
    button(surface,bank,f"出售 +{session.sale_refund} 金币",sell,disabled=not enabled)
    button(surface,bank,"返回",cancel)
    buttons = [(cancel,"deselect")]
    if enabled:
        buttons.append((sell,"sell"))
        if affordable: buttons.append((upgrade,"upgrade"))
    text(surface,bank,"1–4 选购新塔 · AI 不自动升级",(1008,635),16,MUTED)
    return buttons


def draw_build_feedback(surface, layout, bank, game, session, pointer):
    if not session:
        return
    old_clip = surface.get_clip()
    surface.set_clip(layout.grid_rect)
    # Persistent latest build marker is updated only on successful env.step.
    # It is presentation data, never a fabricated action or a second game state.
    if session.last_build:
        build = session.last_build
        center = layout.center(build["x"], build["y"])
        rect = pygame.Rect(0, 0, round(layout.cell)-2, round(layout.cell)-2)
        rect.center = center
        pygame.draw.rect(surface, (251, 236, 176), rect, 3, border_radius=4)
    tower = session.selected_tower
    if tower:
        center = layout.center(tower.x, tower.y)
        pygame.draw.circle(surface, ACCENT, center, round(tower.spec.range*layout.cell), 1)
        rect = pygame.Rect(0, 0, round(layout.cell)-2, round(layout.cell)-2)
        rect.center = center
        pygame.draw.rect(surface, ACCENT, rect, 3, border_radius=4)
    cell = layout.grid_at(pointer)
    if cell is not None and any((t.x, t.y) == cell for t in game.towers.values()):
        cell = None
    if cell is not None and session.mode == "manual" and not session.paused and not session.ended:
        x, y = cell
        spec = list(game.cfg.towers.values())[session.selected]
        legal = bool(session.obs["action_mask"][session.selected + 1, y, x])
        color = (157, 240, 200) if legal else (250, 145, 128)
        center = layout.center(x, y)
        pygame.draw.circle(surface, color, center, round(spec.range*layout.cell), 1)
        rect = pygame.Rect(0, 0, round(layout.cell), round(layout.cell))
        rect.center = center
        pygame.draw.rect(surface, color, rect.inflate(-2, -2), 2, border_radius=5)
        if legal:
            ghost = bank.image(spec.name, round(layout.cell)-8).copy()
            ghost.set_alpha(130)
            surface.blit(ghost, ghost.get_rect(center=center))
    surface.set_clip(old_clip)
