"""Curated live levels; original benchmark map factories remain untouched."""
from dataclasses import dataclass
from typing import Callable

from ai_gym_td.config import GameConfig


@dataclass(frozen=True)
class Level:
    key: str
    name: str
    description: str
    factory: Callable[[], GameConfig]
    build_sites: tuple


def double_garden():
    """Two open garden loops on one continuous road, with no adjacent shortcuts."""
    corners = ((0, 2), (8, 2), (8, 6), (2, 6), (2, 9), (11, 9),
               (11, 2), (17, 2), (17, 6), (14, 6), (14, 9), (19, 9))
    path = [corners[0]]
    for x2, y2 in corners[1:]:
        x, y = path[-1]
        assert (x == x2) != (y == y2), "Road segments must be axis-aligned"
        dx, dy = (x2 > x) - (x2 < x), (y2 > y) - (y2 < y)
        while (x, y) != (x2, y2):
            x, y = x + dx, y + dy
            path.append((x, y))
    return GameConfig(path=path, blocked_cells=[(3, 4), (15, 4), (6, 11), (18, 1)],
                      map_name="double_garden")


def canyon_relay():
    """Three separated road legs reward defense across successive zones."""
    corners = ((0, 1), (5, 1), (5, 9), (10, 9), (10, 2),
               (16, 2), (16, 9), (19, 9))
    path = [corners[0]]
    for x2, y2 in corners[1:]:
        x, y = path[-1]
        dx, dy = (x2 > x) - (x2 < x), (y2 > y) - (y2 < y)
        while (x, y) != (x2, y2):
            x, y = x + dx, y + dy
            path.append((x, y))
    return GameConfig(path=path, blocked_cells=[(2, 6), (8, 2), (13, 6), (13, 10)],
                      map_name="canyon_relay")


LEVELS = (
    Level("s_curve", "绿野回廊", "长路线、多次交火，适合熟悉操作。",
          GameConfig.default_20x12, (
              (2, 1), (5, 1), (8, 1), (11, 1), (14, 1), (17, 1),
              (3, 4), (7, 4), (11, 4), (15, 4),
              (5, 8), (9, 8), (13, 8), (18, 8), (9, 10), (17, 10),
          )),
    Level("chokepoint", "双折山口", "守住两个转角，兼顾入口与基地。",
          GameConfig.chokepoint_path, (
              (1, 1), (4, 3), (7, 3), (8, 4), (10, 4), (12, 4),
              (8, 6), (10, 6), (13, 6), (13, 8), (16, 8), (18, 10),
          )),
    Level("straight", "疾风防线", "路线最短，集中火力阻止敌人突围。",
          GameConfig.straight_path,
          tuple((x, y) for y in (5, 7) for x in (2, 5, 8, 11, 14, 17))),
    Level("double_garden", "双环庭院", "双环交叉覆盖，集中升级或分区守卫。",
          double_garden, ((3, 1), (6, 4), (1, 7), (5, 10), (9, 7),
                          (10, 1), (14, 4), (18, 4), (13, 10), (18, 10))),
    Level("canyon_relay", "峡谷接力", "三段纵向防线，前段削血、末段补漏。",
          canyon_relay, ((3, 3), (6, 6), (4, 10), (8, 8), (9, 4),
                         (12, 3), (15, 5), (17, 8), (18, 10))),
)


def get_level(key):
    for level in LEVELS:
        if level.key == key:
            return level
    raise ValueError(f"Unknown level: {key}")
