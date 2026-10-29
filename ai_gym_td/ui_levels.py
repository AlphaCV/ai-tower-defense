"""Level picker with previews from the same configuration used by the game."""
import pygame

from ai_gym_td.levels import LEVELS
from ai_gym_td.ui_level_guidance import DIFFICULTY, OPENINGS, TIPS, recommendation_text
from ai_gym_td.ui_panels import PANEL, TEXT, MUTED, ACCENT, text, button


def description_lines(bank, description, width):
    """Wrap Chinese card descriptions by measured glyph width."""
    lines, line = [], ""
    for character in description:
        if line and bank.font(17).size(line + character)[0] > width:
            if character in "，。；：！？、":
                lines.append(line[:-1])
                line = line[-1]
            else:
                lines.append(line)
                line = ""
        line += character
    if line:
        lines.append(line)
    return lines


def draw_level_picker(surface, bank, session):
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((5, 12, 19, 225))
    surface.blit(shade, (0, 0))
    text(surface, bank, "选择关卡", (148, 50), 40)
    text(surface, bank, "选择地图后点击开始。本局进度将重置，控制模式和倍速保留。", (148, 101), 20, MUTED)
    text(surface, bank, recommendation_text(LEVELS) + "（原编号不变）", (148, 132), 21, ACCENT)
    buttons = []
    card_width = min(314, (1200 - 16 * (len(LEVELS) - 1)) // len(LEVELS))
    left = (surface.get_width() - (card_width + 16) * len(LEVELS) + 16) // 2
    for i, level in enumerate(LEVELS):
        rect = pygame.Rect(left + i * (card_width + 16), 174, card_width, 344)
        chosen = session.level_choice == level.key
        pygame.draw.rect(surface, PANEL, rect, border_radius=12)
        pygame.draw.rect(surface, ACCENT if chosen else (61, 82, 90), rect, 3 if chosen else 1, border_radius=12)
        text(surface, bank, f"{i + 1:02}  {level.name}", (rect.x + 20, 192), 24 if card_width < 260 else 29, ACCENT if chosen else TEXT)
        cfg = level.factory()
        grid = cfg.make_grid()
        cell = min(13, (card_width - 40) // cfg.width)
        map_x = rect.x + (card_width - cfg.width * cell) // 2
        colors = [(56, 95, 66), (191, 174, 125), (231, 145, 91), (116, 195, 223), (90, 103, 99)]
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                pygame.draw.rect(surface, colors[tile], (map_x + x * cell, 241 + y * cell, cell, cell))
        if session.fixed_sites:
            for x, y in level.build_sites:
                pygame.draw.circle(surface, (232, 229, 177),
                                   (map_x + x * cell + cell // 2, 241 + y * cell + cell // 2), 3)
        if session.fixed_sites and chosen and session.mode == "manual":
            for number, ((x, y), _) in enumerate(OPENINGS.get(level.key, ()), 1):
                center = (map_x + x * cell + cell // 2, 241 + y * cell + cell // 2)
                pygame.draw.circle(surface, (244, 205, 119), center, 8)
                glyph = bank.font(15).render(str(number), True, (17, 28, 38))
                surface.blit(glyph, glyph.get_rect(center=center))
        if session.fixed_sites:
            text(surface, bank, "手动难度：" + DIFFICULTY[level.key], (rect.x + 20, 374), 18, ACCENT)
        else:
            text(surface, bank, "自由建造对照", (rect.x + 20, 374), 18, MUTED)
        sites = f"{len(level.build_sites)} 个建造点" if session.fixed_sites else "自由建造"
        text(surface, bank, f"{sites}  ·  {cfg.max_waves} 波敌人", (rect.x + 20, 414), 19 if card_width < 260 else 22)
        for row, line in enumerate(description_lines(bank, level.description, card_width - 40)):
            text(surface, bank, line, (rect.x + 20, 442 + row * 21), 17, MUTED)
        text(surface, bank, "当前关卡" if session.level.key == level.key else f"按 {i + 1} 或点击选择", (rect.x + 20, 495), 18, ACCENT)
        buttons.append((rect, f"levels:pick:{level.key}"))
    if session.mode == "manual" and session.fixed_sites:
        tip = TIPS[session.level_choice]
        note = "预览数字仅为参考，需要手动建塔；开局后仍需补防和升级，不能保证通关。"
    elif session.mode == "manual":
        tip = "自由建造为对照模式；上述推荐顺序基于固定建造点玩法。"
        note = "所有地图均可直接选择；开始后请根据实际战况调整布防。"
    else:
        tip = "AI 演示建议从第 1 关开始；当前智能体不主动升级或出售。"
        note = "卡片难度按手动玩法评估；原 PPO 在其他四关的既有三种子测试中均未通关。"
    text(surface, bank, tip, (148, 531), 20, TEXT)
    text(surface, bank, note, (148, 561), 18, MUTED)
    for label, command, rect, active in [
        ("返回当前游戏 [Esc]", "levels:cancel", pygame.Rect(148, 590, 230, 46), False),
        ("开始所选关卡 [Enter]", "levels:start", pygame.Rect(888, 590, 234, 46), True),
    ]:
        button(surface, bank, label, rect, active)
        buttons.append((rect, command))
    return buttons
