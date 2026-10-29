import numpy as np
import pytest

from ai_gym_td.live import PlaySession


@pytest.fixture
def session():
    s = PlaySession(seed=42)
    yield s
    s.close()


def test_manual_build_pause_and_same_state_mode_switch(session):
    y, x = np.argwhere(session.obs["action_mask"][1])[0]
    session.queue_build(int(x), int(y))
    session.step_once()
    assert session.game.tower_count() == 1 and session.game.gold == 95
    session.command("pause")
    tick, steps = session.game.tick, session.steps
    session.queue_build(int(x)+1, int(y))
    session.advance(10)
    session.step_once()
    assert (session.game.tick, session.steps) == (tick, steps)
    assert session.pending is None
    game = session.game
    session.set_mode("rule")
    assert session.game is game and session.game.tower_count() == 1
    session.command("pause")
    session.step_once()
    assert session.game.tick == tick+4


def test_invalid_ai_action_becomes_pass(session):
    class InvalidAgent:
        def act(self, obs, info):
            x,y=session.game.spawn
            return np.array([1,y,x])
    session.agents["rule"]=InvalidAgent()
    session.set_mode("rule")
    session.step_once()
    assert session.filtered == 1
    assert session.builds == 0 and not session.info["invalid_action"]
    assert session.game.tick == 4


def test_missing_checkpoint_falls_back_to_manual(session, tmp_path):
    session.checkpoint = tmp_path/"missing.pt"
    assert not session.set_mode("ppo")
    assert session.mode == "manual" and "unavailable" in session.message
    assert session.game.lives == 20


def test_time_limit_stops_and_restart_resets_everything():
    s=PlaySession("random",seed=42,max_steps=2)
    try:
        s.step_once();s.step_once()
        assert s.status == "TIME LIMIT" and s.ended
        tick=s.game.tick
        s.advance(100)
        assert s.game.tick == tick
        s.command("pause")
        s.command("restart")
        assert s.steps == s.filtered == s.builds == 0
        assert not s.ended and not s.paused and not s.truncated
        assert s.reward == 0 and s.game.gold == 120 and s.game.tower_count() == 0
        assert s.mode == "random"
    finally:
        s.close()


def test_one_and_four_times_preserve_decision_interval(session):
    session.speed=1
    for _ in range(30):session.advance(1/30)
    assert session.steps == 7 and session.game.tick == 28
    session.reset();session.speed=4
    for _ in range(30):session.advance(1/30)
    assert session.steps == 30 and session.game.tick == 120
    session.command("pause");session.advance(10);session.command("pause")
    session.advance(0)
    assert session.steps == 30


def test_switch_discards_pending_manual_click(session):
    y,x=np.argwhere(session.obs["action_mask"][1])[0]
    session.queue_build(int(x),int(y))
    session.set_mode("rule")
    session.step_once()
    assert session.pending is None and session.game.tower_count() == 0


def test_restart_repeats_ppo_actions_without_reloading():
    s=PlaySession("ppo",seed=42)
    try:
        agent=s.agents["ppo"]
        def trace():
            result=[]
            for _ in range(100):
                s.step_once()
                result.append((s.last_action,s.game.gold,s.game.tick,s.filtered))
            return result
        first=trace()
        s.reset()
        assert s.agents["ppo"] is agent
        assert trace()==first
    finally:
        s.close()


def test_manual_wave_control_has_no_extra_simulation_tick(session):
    session.command("wave")
    assert session.game.tick == 0
    session.step_once()
    assert session.game.wave_number == 1 and session.game.tick == 4
    assert session.obs["global"][4] == 1
