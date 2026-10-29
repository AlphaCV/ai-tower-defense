import numpy as np
import pytest

from ai_gym_td.config import GameConfig
from ai_gym_td.env import TowerDefenseEnv
from ai_gym_td.live import PlaySession
from ai_gym_td.live_rules import DEFAULT_BUILD_SITES, LiveDefenseEnv


def test_site_mask_and_engine_reject_ordinary_grass():
    env = LiveDefenseEnv(build_sites=DEFAULT_BUILD_SITES, render_mode=None)
    try:
        obs, _ = env.reset(seed=42)
        assert len(DEFAULT_BUILD_SITES) == 24
        assert obs["action_mask"][1].sum() == 24
        assert obs["action_mask"][0].all()
        assert env.game.grid[0][0] == 0
        assert not obs["action_mask"][1, 0, 0]
        assert env.game.build_tower(0, 0, "archer") is None
        _, _, _, _, info = env.step([1, 0, 0])
        assert info["invalid_action"] and env.game.gold == 120
        for x, y in DEFAULT_BUILD_SITES:
            assert obs["action_mask"][1, y, x]
    finally:
        env.close()


def test_all_sites_fill_then_selling_reopens_exactly_one():
    cfg = GameConfig.default_20x12()
    cfg.starting_gold = 10000
    env = LiveDefenseEnv(config=cfg, build_sites=DEFAULT_BUILD_SITES, render_mode=None)
    try:
        env.reset(seed=42)
        for x, y in DEFAULT_BUILD_SITES:
            env.step([1, y, x])
        assert env.game.tower_count() == 24
        assert not env.action_masks()[1:].any()
        tower = next(iter(env.game.towers.values()))
        gold, tick = env.game.gold, env.game.tick
        obs, info, refund = env.sell_tower(tower.tid)
        assert refund == 15 and info["gold"] == gold + 15
        assert env.game.tick == tick
        assert obs["action_mask"][1].sum() == 1
        assert obs["action_mask"][1, tower.y, tower.x]
        assert not obs["grid"][tower.y, tower.x, 1]
        assert env.sell_tower(tower.tid) is None
        assert env.game.gold == gold + 15
    finally:
        env.close()


def test_legacy_env_and_adapter_have_identical_observations_and_rewards():
    old, new = TowerDefenseEnv(render_mode=None), LiveDefenseEnv(render_mode=None)
    try:
        a, ia = old.reset(seed=42)
        b, ib = new.reset(seed=42)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])
        for action in ([1, 0, 0], [0, 0, 0], [2, 1, 3], [1, 2, 0]):
            a, ra, ta, ca, ia = old.step(action)
            b, rb, tb, cb, ib = new.step(action)
            for key in a:
                np.testing.assert_array_equal(a[key], b[key])
            assert (ra, ta, ca) == (rb, tb, cb)
            assert old.game.snapshot() == new.game.snapshot()
    finally:
        old.close()
        new.close()


@pytest.mark.parametrize("tower_index,cost,refund", [(0,25,15),(1,55,33),(2,35,21),(3,80,48)])
def test_manual_sale_refund_and_rebuild(tower_index, cost, refund):
    s = PlaySession(fixed_sites=True, speed=1)
    try:
        x, y = DEFAULT_BUILD_SITES[0]
        s.command(f"tower:{tower_index}")
        s.click_cell(x, y)
        s.step_once()
        assert s.game.gold == 120-cost
        s.click_cell(x, y)
        assert s.selected_tower and s.sale_refund == refund
        tick, steps = s.game.tick, s.steps
        s.command("sell")
        s.command("sell")
        assert s.game.tower_count() == 1  # queued, never mutate midway through an event batch
        s.step_once()
        assert s.game.tower_count() == 0 and s.game.gold == 120-cost+refund
        assert s.sales == 1 and s.last_build is None and s.selected_tid is None
        assert s.game.tick == tick+4 and s.steps == steps+1
        assert s.obs["action_mask"][1, y, x]
        s.command("sell")
        s.step_once()
        assert s.game.gold == 120-cost+refund
        s.command("tower:0")
        s.click_cell(x, y)
        s.step_once()
        assert s.game.tower_count() == 1
        assert next(iter(s.game.towers.values())).spec.name == "archer"
        s.reset()
        assert s.game.gold == 120 and s.sales == 0 and s.game.tower_count() == 0
        assert s.obs["action_mask"][1].sum() == len(s.level.build_sites)
    finally:
        s.close()


def test_paused_ai_and_ended_sessions_cannot_sell_or_replay_pending_sale():
    s = PlaySession(fixed_sites=True)
    try:
        x, y = DEFAULT_BUILD_SITES[0]
        s.click_cell(x, y)
        s.step_once()
        s.click_cell(x, y)
        s.command("pause")
        s.command("sell")
        assert s.pending_sale is None
        s.command("pause")
        s.command("sell")
        s.set_mode("rule")
        assert s.pending_sale is None
        s.command("sell")
        assert s.pending_sale is None
        s.set_mode("manual")
        s.command("sell")
        s.command("pause")
        assert s.pending_sale is None
        s.command("pause")
        s.ended = True
        s.command("sell")
        s.step_once()
        assert s.game.tower_count() == 1 and s.game.gold == 95
    finally:
        s.close()


@pytest.mark.parametrize("mode", ["ppo", "rule", "random"])
def test_agents_use_only_sites_and_keep_model_observation_shape(mode):
    s = PlaySession(mode, fixed_sites=True, seed=42)
    try:
        for _ in range(200):
            s.step_once()
            assert all((t.x, t.y) in s.level.build_sites for t in s.game.towers.values())
            assert not s.info["invalid_action"]
        assert s.obs["grid"].shape == (12, 20, 8)
        assert s.obs["global"].shape == (6,)
        assert s.obs["action_mask"].shape == (5, 12, 20)
        assert s.game.tower_count() <= len(s.level.build_sites)
    finally:
        s.close()
