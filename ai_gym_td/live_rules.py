"""Optional live-game rules; the original training/evaluation environment is unchanged."""
import numpy as np

from ai_gym_td.config import TILE_GRASS
from ai_gym_td.upgrades import UpgradeableDefenseGame
from ai_gym_td.env import TowerDefenseEnv

# Authored positions on the existing 20x12 S-curve. Coordinates are (x, y).
DEFAULT_BUILD_SITES = (
    (2, 1), (5, 1), (8, 1), (11, 1), (14, 1), (17, 1),
    (3, 4), (7, 4), (11, 4), (15, 4),
    (5, 5), (9, 5), (13, 5), (18, 5),
    (2, 8), (5, 8), (9, 8), (13, 8), (18, 8),
    (5, 10), (9, 10), (13, 10), (17, 10), (19, 10),
)
SELL_REFUND_FRACTION = 0.6


class SiteDefenseGame(UpgradeableDefenseGame):
    def __init__(self, config, build_sites):
        super().__init__(config)
        self.build_sites = frozenset(build_sites)
        if len(self.build_sites) != len(build_sites):
            raise ValueError("Build sites must be unique")
        for x, y in self.build_sites:
            if not (0 <= x < config.width and 0 <= y < config.height):
                raise ValueError(f"Build site outside map: {(x, y)}")
            if self.grid[y][x] != TILE_GRASS:
                raise ValueError(f"Build site must be grass: {(x, y)}")

    def build_tower(self, x, y, tower_name):
        if (x, y) not in self.build_sites:
            return None
        return super().build_tower(x, y, tower_name)


class LiveDefenseEnv(TowerDefenseEnv):
    """Keep observation/action shapes and rewards; constrain both mask and engine."""
    def __init__(self, *, build_sites=None, **kwargs):
        self.build_sites = None if build_sites is None else tuple(build_sites)
        super().__init__(**kwargs)
        self.game = UpgradeableDefenseGame(self.cfg)
        if self.build_sites is not None:
            self.game = SiteDefenseGame(self.cfg, self.build_sites)
            self._site_mask = np.zeros((self.cfg.height, self.cfg.width), dtype=np.int8)
            for x, y in self.build_sites:
                self._site_mask[y, x] = 1

    def action_masks(self):
        mask = super().action_masks()
        if self.build_sites is not None:
            mask[1:] *= self._site_mask
        return mask

    def upgrade_tower(self, tid):
        result = self.game.upgrade_tower(tid)
        if result is None:
            return None
        level, price = result
        return self._observe(), self._base_info(), level, price

    def sell_tower(self, tid):
        """Human management operation, outside the pretrained model's action space.

        No simulation tick/reward is added. Refresh observations before the next
        decision so the model never sees stale gold or an occupied sold site.
        """
        tower = self.game.towers.get(tid)
        if tower is None or self.game.is_terminal:
            return None
        refund = int(tower.spec.cost * SELL_REFUND_FRACTION)
        if not self.game.sell_tower(tid, SELL_REFUND_FRACTION):
            return None
        return self._observe(), self._base_info(), refund
