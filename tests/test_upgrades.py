from dataclasses import replace
import numpy as np
import pytest

from ai_gym_td.config import GameConfig, ENEMIES
from ai_gym_td.engine import Enemy
from ai_gym_td.live import PlaySession
from ai_gym_td.live_rules import LiveDefenseEnv


@pytest.mark.parametrize("name,cost,p2,p3,damage", [
    ("archer",25,45,120,16.8),("cannon",55,180,500,44.8),
    ("ice",35,60,180,4.8),("tesla",80,140,360,23.8)])
def test_upgrade_economy_isolation_refund_and_reset(name,cost,p2,p3,damage):
    cfg = GameConfig.straight_path();cfg.starting_gold=1000
    env = LiveDefenseEnv(config=cfg,build_sites=((1,5),(3,5)),render_mode=None)
    try:
        env.reset(seed=42)
        tid = env.game.build_tower(1,5,name)
        other = env.game.build_tower(3,5,name)
        tower = env.game.towers[tid]
        tower.cooldown=.75
        before = cfg.to_json(); tick=env.game.tick
        for expected,price in ((2,p2),(3,p3)):
            obs,info,level,paid = env.upgrade_tower(tid)
            assert (level,paid)==(expected,price)
            assert env.game.tick==tick and tower.cooldown==.75
            assert env.game.tower_level(tid)==expected
            assert env.observation_space.contains(obs)
            assert info['gold']==env.game.gold
        assert env.game.gold==1000-cost*2-p2-p3
        assert tower.spec.cost==cost+p2+p3 and tower.spec.damage==damage
        assert env.game.towers[other].spec is cfg.towers[name]
        assert cfg.to_json()==before
        gold=env.game.gold
        assert env.upgrade_tower(tid) is None and env.game.gold==gold
        _,info,refund=env.sell_tower(tid)
        assert refund==(cost+p2+p3)*60//100 and info['gold']==gold+refund
        assert env.game.tower_level(tid)==0 and env.upgrade_tower(tid) is None
        assert env.sell_tower(tid) is None
        fresh=env.game.build_tower(1,5,name)
        assert env.game.tower_level(fresh)==1 and env.game.towers[fresh].spec is cfg.towers[name]
        env.reset(seed=42)
        assert not env.game.towers and not env.game._tower_levels
        assert env.game.gold==1000
    finally: env.close()


def test_money_terminal_and_unknown_tower_guards():
    env=LiveDefenseEnv()
    try:
        env.reset(seed=42)
        tid=env.game.build_tower(0,0,'tesla')
        assert env.game.gold==40
        assert env.upgrade_tower(tid) is None
        assert env.upgrade_tower(999) is None
        assert env.game.gold==40 and env.game.tower_level(tid)==1
        env.game._gold=1000
        env.game._phase=env.game.WON
        assert env.upgrade_tower(tid) is None and env.sell_tower(tid) is None
        assert env.game.gold==1000
    finally: env.close()


def test_queue_duplicate_cancel_mode_switch_and_fresh_ai_observation():
    s=PlaySession(fixed_sites=True,speed=1)
    try:
        cell=s.level.build_sites[0]
        s.click_cell(*cell);s.step_once();s.click_cell(*cell)
        tid=s.selected_tid;tick=s.game.tick
        s.command('upgrade');s.command('upgrade');s.step_once()
        assert s.upgrades==1 and s.game.tower_level(tid)==2 and s.game.gold==50
        assert s.game.tick==tick+4 and s.obs['global'][0]==pytest.approx(50/240)
        assert s.sale_refund==42 and s.upgrade_quote[1]==120
        # Every mode switch discards queued spending, including the PPO cache path.
        # Controlled balance: the new level-3 fee exceeds the opening funds.
        s.game._gold = 120
        s.obs = s.env._observe()
        s.info = s.env._base_info()
        s.command('upgrade')
        assert s.pending_upgrade == tid
        s.set_mode('ppo')
        assert s.pending_upgrade is None
        s.command('upgrade');s.step_once()
        assert s.game.tower_level(tid)==2 and s.upgrades==1
        s.set_mode('manual')
        # Reset to a deterministic gold balance; do not rely on AI's purchases.
        s.reset();s.click_cell(*cell);s.step_once();s.click_cell(*cell)
        tid=s.selected_tid
        for command in ('pause','levels','deselect','tower:1'):
            s.command('upgrade');s.command(command)
            assert s.pending_upgrade is None
            if command=='pause':s.command('pause')
            if command=='levels':s.command('levels:cancel')
            s.step_once()
            assert s.game.tower_level(tid)==1
            s.click_cell(*cell)
        s.command('upgrade');s.command('sell');s.step_once()
        assert s.game.gold==110 and not s.game.towers and s.upgrades==0
        s.command('tower:0');s.click_cell(*cell);s.step_once();s.click_cell(*cell)
        s.command('upgrade')
        assert s.pending_upgrade == s.selected_tid
        s.switch_level('straight')
        assert s.upgrades==0 and s.pending_upgrade is None and not s.game._tower_levels
        s.click_cell(*s.level.build_sites[0]);s.step_once();s.click_cell(*s.level.build_sites[0])
        s.ended=True;s.command('upgrade');s.step_once()
        assert s.selected_tower.spec.cost==25 and s.upgrades==0
    finally:s.close()


def combat(name, level):
    cfg=GameConfig.straight_path();cfg.starting_gold=1000
    env=LiveDefenseEnv(config=cfg,render_mode=None)
    g=env.game;tid=g.build_tower(1,5,name)
    for _ in range(level-1):assert env.upgrade_tower(tid)
    # Controlled stationary targets let us compare actual impacts and chain counts.
    spec=replace(ENEMIES['grunt'],hp=10000,speed=0,armor=0)
    for i in range(6):
        g._enemies[i+1]=Enemy(i+1,spec,0,0,0,6,10000,10000)
    g._phase=g.WAVE
    for _ in range(20):g.step(1/30)
    return env,g.towers[tid],list(g.enemies.values())


@pytest.mark.parametrize('name',['archer','cannon','ice','tesla'])
def test_upgraded_towers_really_attack_with_new_damage_and_effects(name):
    old,a,ea=combat(name,1);new,b,eb=combat(name,3)
    try:
        assert a.shots_fired>0 and b.shots_fired>0
        assert sum(e.max_hp-e.hp for e in eb)>sum(e.max_hp-e.hp for e in ea)
        if name=='ice':
            assert min(e.slow_mult for e in eb)==pytest.approx(.35)
            assert max(e.slow_until for e in eb)>max(e.slow_until for e in ea)
        if name=='tesla':
            assert sum(e.hp<e.max_hp for e in ea)==3
            assert sum(e.hp<e.max_hp for e in eb)==5
        if name=='cannon':assert b.spec.splash==1.35
        if name=='archer':assert b.spec.fire_rate>a.spec.fire_rate
    finally:old.close();new.close()


def test_inflight_projectile_and_cooldown_are_not_retroactively_upgraded():
    env=LiveDefenseEnv(render_mode=None)
    try:
        tid=env.game.build_tower(2,1,'archer');tower=env.game.towers[tid]
        e=Enemy(1,ENEMIES['grunt'],0,0,0,2,60,60)
        env.game._fire(tower,e)
        projectile=next(iter(env.game.projectiles.values()))
        tower.cooldown=.6
        assert env.upgrade_tower(tid)
        assert projectile.damage==8 and tower.spec.damage==12 and tower.cooldown==.6
    finally:env.close()
