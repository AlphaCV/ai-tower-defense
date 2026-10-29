"""Manual live-game upgrades; no changes to the original engine or model space."""
from dataclasses import dataclass, replace
from ai_gym_td.engine import TowerDefenseGame


@dataclass(frozen=True)
class UpgradeStep:
    price: int
    damage_mult: float
    range_bonus: float
    fire_rate_mult: float = 1.0
    splash_bonus: float = 0.0
    slow_mult: float = 1.0
    slow_duration_bonus: float = 0.0
    chain_bonus: int = 0


# Each row is relative to the original level-1 spec, never compounded.
# Incremental upgrade fees; base tower costs and combat stats stay unchanged.
# See ECONOMY.md for the legal-play comparisons behind these prices.
UPGRADE_STEPS = {
    "archer": (UpgradeStep(45, 1.5, .2, 1.15), UpgradeStep(120, 2.1, .4, 1.3)),
    "cannon": (UpgradeStep(180, 1.25, .1, splash_bonus=.12),
               UpgradeStep(500, 1.6, .2, splash_bonus=.25)),
    "ice": (UpgradeStep(60, 1.25, .15, 1.05, slow_mult=.84, slow_duration_bonus=.3),
            UpgradeStep(180, 1.6, .3, 1.1, slow_mult=.7, slow_duration_bonus=.6)),
    "tesla": (UpgradeStep(140, 1.35, .15, chain_bonus=1),
              UpgradeStep(360, 1.7, .3, chain_bonus=2)),
}


class UpgradeableDefenseGame(TowerDefenseGame):
    def reset(self, seed=None):
        super().reset(seed)
        self._tower_levels = {}

    def tower_level(self, tid):
        return self._tower_levels.get(tid, 1) if tid in self.towers else 0

    def upgrade_quote(self, tid):
        tower = self.towers.get(tid)
        if tower is None:
            return None
        level = self.tower_level(tid)
        steps = UPGRADE_STEPS.get(tower.spec.name, ())
        if level > len(steps):
            return None
        step = steps[level - 1]
        base = self.cfg.towers[tower.spec.name]
        spec = replace(base,
            # Existing engine sale logic reads this per-instance cumulative cost.
            cost=tower.spec.cost + step.price,
            damage=round(base.damage * step.damage_mult, 3),
            range=round(base.range + step.range_bonus, 3),
            fire_rate=round(base.fire_rate * step.fire_rate_mult, 3),
            splash=round(base.splash + step.splash_bonus, 3),
            slow=round(base.slow * step.slow_mult, 3),
            slow_duration=round(base.slow_duration + step.slow_duration_bonus, 3),
            chain=base.chain + step.chain_bonus)
        return level + 1, step.price, spec

    def upgrade_tower(self, tid):
        quote = self.upgrade_quote(tid)
        if self.is_terminal or quote is None:
            return None
        level, price, spec = quote
        if self.gold < price:
            return None
        self._gold -= price
        self.towers[tid].spec = spec
        self._tower_levels[tid] = level
        # Keep cooldown and in-flight projectiles: upgrades do not grant free shots.
        return level, price

    def sell_tower(self, tid, refund_frac=.6):
        sold = super().sell_tower(tid, refund_frac)
        if sold:
            self._tower_levels.pop(tid, None)
        return sold
