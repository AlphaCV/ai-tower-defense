"""Small presentation controller; the environment remains the only simulation owner."""
from pathlib import Path
from time import perf_counter

import numpy as np

from ai_gym_td.agents import RandomAgent, RuleBasedAgent
from ai_gym_td.live_rules import LiveDefenseEnv, SELL_REFUND_FRACTION
from ai_gym_td.levels import get_level


class PlaySession:
    MODES = ("manual", "ppo", "rule", "random")

    def __init__(self, mode="manual", checkpoint=None, seed=42, max_steps=12000, speed=4, fixed_sites=False, level="s_curve"):
        self.fixed_sites, self.max_steps = fixed_sites, max_steps
        self.level = get_level(level)
        self.env = self._make_env(self.level)
        self.checkpoint = Path(checkpoint) if checkpoint else Path(__file__).resolve().parent.parent / "agent.pt"
        self.seed, self.speed = seed, speed
        self.mode, self.selected = "manual", 0
        self.agents = {}
        self.reset()
        self.set_mode(mode)

    def _make_env(self, level):
        # A new environment also recomputes the path-distance observation channel.
        return LiveDefenseEnv(config=level.factory(), render_mode=None,
                              max_env_steps=self.max_steps,
                              build_sites=level.build_sites if self.fixed_sites else None)

    def switch_level(self, key):
        level = get_level(key)
        env = self._make_env(level)
        self.env.close()
        self.level, self.env = level, env
        self.reset()

    @property
    def game(self):
        return self.env.game

    @property
    def status(self):
        if self.ended:
            return "TIME LIMIT" if self.truncated else ("VICTORY" if self.game.phase == "won" else "DEFEAT")
        return "PAUSED" if self.paused else "RUNNING"

    def reset(self):
        self.obs, self.info = self.env.reset(seed=self.seed)
        self.agents.update(random=RandomAgent(seed=self.seed), rule=RuleBasedAgent(seed=self.seed))
        if "ppo" in self.agents:
            import torch
            torch.manual_seed(self.seed)
        self.paused = self.ended = self.truncated = False
        self.steps = self.filtered = self.builds = 0
        self.reward = self.inference_ms = self.accumulator = 0.0
        self.pending = None
        self.selected = 0
        self.last_action, self.message = "Ready", ""
        self.last_build = None
        self.selected_tid = self.pending_sale = None
        self.sales = 0
        self.upgrades = 0
        self.pending_upgrade = None
        self.level_menu_open = False
        self.level_choice = self.level.key

    def set_mode(self, mode):
        self.pending_upgrade = None
        if mode not in self.MODES:
            raise ValueError(f"Unknown mode: {mode}")
        if mode == "ppo" and mode not in self.agents:
            try:
                import torch
                from ai_gym_td.scripts.evaluate import _build_agent
                torch.set_num_threads(1)
                self.agents["ppo"] = _build_agent("ppo", str(self.checkpoint))
                torch.manual_seed(self.seed)
            except Exception as exc:
                # Optional model failures must leave manual play available.
                self.mode, self.pending = "manual", None
                self.pending_sale = None
                self.accumulator = 0.0
                self.message = f"PPO unavailable ({type(exc).__name__}); manual mode. See console."
                print(f"PPO load failed: {exc}")
                return False
        self.mode, self.pending = mode, None
        self.pending_sale = None
        self.accumulator = 0.0
        self.inference_ms = 0.0
        self.message = ""
        return True

    def command(self, command):
        if command == "levels":
            self.level_menu_open = True
            self.level_choice = self.level.key
            self.pending = self.pending_sale = None
            self.pending_upgrade = None
            self.accumulator = 0.0
            return
        if command.startswith("levels:"):
            if self.level_menu_open:
                if command == "levels:cancel":
                    self.level_menu_open = False
                elif command == "levels:start":
                    self.switch_level(self.level_choice)
                elif command.startswith("levels:pick:"):
                    self.level_choice = get_level(command.split(":", 2)[2]).key
            return
        if self.level_menu_open:
            return
        if command in self.MODES:
            self.set_mode(command)
        elif command == "pause" and not self.ended:
            self.paused = not self.paused
            self.pending, self.accumulator = None, 0.0
            self.pending_sale = None
            self.pending_upgrade = None
        elif command == "restart":
            self.reset()
        elif command == "speed":
            self.speed = 1 if self.speed == 4 else 4
            self.accumulator = 0.0
        elif command == "wave" and self.mode == "manual" and not self.paused and not self.ended:
            # Applied inside the next env.step: no stale observation or extra tick.
            self.env.skip_build_phase()
        elif command == "sell":
            if self.mode == "manual" and not self.paused and not self.ended and self.selected_tower:
                self.pending_sale = self.selected_tid
                self.pending = None
                self.pending_upgrade = None
        elif command == "upgrade":
            if self.mode == "manual" and not self.paused and not self.ended and self.selected_tower:
                quote = self.upgrade_quote
                if quote is None:
                    self.message = "该炮塔已达到最高等级。"
                elif self.game.gold < quote[1]:
                    self.message = f"升级还需要 {quote[1] - self.game.gold} 金币。"
                else:
                    self.pending_upgrade = self.selected_tid
                    self.pending = self.pending_sale = None
                    self.message = "升级指令已提交。"
        elif command == "deselect":
            self.selected_tid = None
            self.pending_upgrade = self.pending_sale = None
        elif command.startswith("tower:"):
            self.selected_tid = None
            self.pending_upgrade = self.pending_sale = None
            self.message = ""
            self.selected = int(command.split(":")[1])

    @property
    def selected_tower(self):
        return self.game.towers.get(self.selected_tid)

    @property
    def sale_refund(self):
        tower = self.selected_tower
        return int(tower.spec.cost * SELL_REFUND_FRACTION) if tower else 0

    @property
    def upgrade_quote(self):
        return self.game.upgrade_quote(self.selected_tid)

    def click_cell(self, x, y):
        if self.level_menu_open:
            return
        tower = next((t for t in self.game.towers.values() if (t.x, t.y) == (x, y)), None)
        self.selected_tid = tower.tid if tower else None
        self.pending = self.pending_sale = None
        self.pending_upgrade = None
        if tower is None:
            self.queue_build(x, y)

    def queue_build(self, x, y):
        if self.mode != "manual" or self.paused or self.ended or self.level_menu_open:
            return
        self.pending_sale = None
        self.pending_upgrade = None
        action = np.array([self.selected + 1, y, x], dtype=np.int64)
        if self.env.build_sites is not None and (x, y) not in self.game.build_sites:
            self.message = "请在标有加号的圆形建造点上建塔。"
            return
        if self.env.action_space.contains(action) and self.obs["action_mask"][tuple(action)]:
            self.pending = action
            self.message = "Build queued"
        else:
            self.message = "Cannot build: occupied, path, or insufficient gold."

    def step_once(self):
        if self.paused or self.ended or self.level_menu_open:
            return
        if self.mode == "manual":
            if self.pending_upgrade is not None:
                tid, self.pending_upgrade = self.pending_upgrade, None
                upgraded = self.env.upgrade_tower(tid)
                if upgraded is not None:
                    self.obs, self.info, level, price = upgraded
                    self.upgrades += 1
                    self.message = f"已升至 {level} 级，消耗 {price} 金币。"
                else:
                    self.message = "升级未执行：金币不足、已满级或炮塔不存在。"
            if self.pending_sale is not None:
                tid, self.pending_sale = self.pending_sale, None
                tower = self.game.towers.get(tid)
                sold = self.env.sell_tower(tid)
                if sold is not None:
                    self.obs, self.info, refund = sold
                    self.sales += 1
                    self.message = f"炮塔已出售，返还 {refund} 金币。可在原建造点重新建塔。"
                    if self.last_build and tower and (tower.x, tower.y) == (self.last_build["x"], self.last_build["y"]):
                        self.last_build = None
                self.selected_tid = None
            if self.pending is not None:
                self.message = ""
            action = self.pending if self.pending is not None else np.array([0, 0, 0])
        else:
            start = perf_counter()
            try:
                action = self.agents[self.mode].act(self.obs, self.info)
            except Exception as exc:
                self.set_mode("manual")
                self.message = "AI inference failed; manual mode. See console."
                print(f"AI inference failed: {exc}")
                return
            self.inference_ms = (perf_counter() - start) * 1000
        self.pending = None
        legal = self.env.action_space.contains(action)
        legal = legal and bool(self.obs["action_mask"][tuple(action)])
        if not legal:
            self.filtered += 1
            self.last_action = f"Filtered {tuple(action)} -> pass"
            action = np.array([0, 0, 0])
        elif int(action[0]):
            name = self.env._tower_names[int(action[0]) - 1]
            self.last_action = f"Build {name} at ({action[2]}, {action[1]})"
        else:
            self.last_action = "Pass"
        self.obs, reward, terminated, self.truncated, self.info = self.env.step(action)
        self.steps += 1
        self.reward += reward
        self.builds += int(self.info["placed_tower"])
        if self.info["placed_tower"]:
            self.last_build = {
                "step": self.steps, "type": self.env._tower_names[int(action[0])-1],
                "x": int(action[2]), "y": int(action[1]), "mode": self.mode,
            }
        self.ended = terminated or self.truncated

    def advance(self, elapsed):
        if self.paused or self.ended or self.level_menu_open:
            self.accumulator = 0.0
            return
        interval = self.env.steps_per_action / self.env.cfg.tick_rate
        # Discard long stalls; never freeze the UI trying to catch up indefinitely.
        self.accumulator += min(max(elapsed, 0.0), 0.25) * self.speed
        for _ in range(8):
            if self.accumulator + 1e-9 < interval or self.ended:
                break
            self.accumulator -= interval
            self.step_once()
        self.accumulator = min(self.accumulator, interval * 8)

    def close(self):
        self.env.close()
        for agent in self.agents.values():
            if hasattr(agent, "env"):
                agent.env.close()
