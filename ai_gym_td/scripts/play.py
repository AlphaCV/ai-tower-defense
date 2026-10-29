"""Interactive manual and live AI presentation, without training."""
from __future__ import annotations

import argparse
import sys

from ai_gym_td.live import PlaySession
from ai_gym_td.levels import LEVELS


def handle_event(event, session, viewer):
    pygame = viewer.pygame
    if event.type == pygame.VIDEORESIZE:
        viewer.resize(event.size)
        return True
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if session.level_menu_open:
            if event.key in (pygame.K_ESCAPE, pygame.K_l):
                session.command("levels:cancel")
            elif event.key == pygame.K_RETURN:
                session.command("levels:start")
            elif pygame.K_1 <= event.key < pygame.K_1 + len(LEVELS):
                session.command(f"levels:pick:{LEVELS[event.key - pygame.K_1].key}")
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        controls = {
            pygame.K_p: "pause", pygame.K_r: "restart", pygame.K_l: "levels",
            pygame.K_SPACE: "wave", pygame.K_s: "speed",
            pygame.K_F1: "manual", pygame.K_F2: "ppo",
            pygame.K_F3: "rule", pygame.K_F4: "random",
        }
        if event.key in controls:
            session.command(controls[event.key])
        elif event.key == pygame.K_TAB:
            session.set_mode("ppo" if session.mode == "manual" else "manual")
        elif pygame.K_1 <= event.key <= pygame.K_4:
            session.command(f"tower:{event.key - pygame.K_1}")
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        position = viewer.logical_position(event.pos)
        if position is None:
            return True
        for rect, command in viewer.buttons:
            if rect.collidepoint(position):
                if session.level_menu_open and not command.startswith("levels:"):
                    return True
                if command == "exit":
                    return False
                session.command(command)
                return True
        cell = viewer.grid_position(event.pos)
        if cell is not None:
            session.click_cell(*cell)
    return True


def play(cell_px=40, target_fps=30, seed=42, agent="manual", ckpt=None, max_steps=12000, speed=4, fixed_sites=True, level="s_curve"):
    try:
        from ai_gym_td.viewer import PygameViewer
        session = PlaySession(agent, ckpt, seed, max_steps, speed, fixed_sites=fixed_sites, level=level)
        viewer = PygameViewer(session.env.cfg, cell_px=cell_px, hud_height=216,
                              caption="AI 智能塔防 | 自动布塔 / 手动操作", presentation=True)
    except ImportError as exc:
        print(f"Missing game dependency: {exc}")
        return 1
    pygame = viewer.pygame
    clock = pygame.time.Clock()
    print("F1 手动 | F2 PPO 自动布塔 | F3 规则 | F4 随机 | Tab 手动/PPO")
    print("L 选择关卡 | P 暂停 | R 重开 | S 1/4 倍速 | 1–4 选塔 | 点已有炮塔可出售 | 空格 下一波 | Esc 退出")
    viewer.draw(session.game, fps=0, process_events=False, session=session)
    try:
        running = True
        while running:
            elapsed = clock.tick(target_fps) / 1000.0
            for event in pygame.event.get():
                if not handle_event(event, session, viewer):
                    running = False
                    break
            if not running:
                break
            session.advance(elapsed)
            viewer.draw(session.game, fps=0, process_events=False, session=session)
    finally:
        session.close()
        viewer.close()
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cell-px", type=int, default=40)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--agent", choices=PlaySession.MODES, default="manual")
    p.add_argument("--ckpt", type=str)
    p.add_argument("--max-steps", type=int, default=12000)
    p.add_argument("--speed", type=int, choices=[1, 4], default=4)
    p.add_argument("--free-build", action="store_true", help="使用原版自由建造规则（用于对照）")
    p.add_argument("--level", choices=[level.key for level in LEVELS], default="s_curve", help="启动关卡；游戏中按 L 切换")
    args = p.parse_args()
    if args.cell_px < 36 or args.fps <= 0 or args.max_steps <= 0:
        p.error("cell-px must be >=36; fps and max-steps must be positive")
    sys.exit(play(args.cell_px, args.fps, args.seed, args.agent, args.ckpt, args.max_steps, args.speed, fixed_sites=not args.free_build, level=args.level))


if __name__ == "__main__":
    main()
