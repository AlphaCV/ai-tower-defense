"""Presentation guidance only: no automatic placement or combat changes."""

RECOMMENDED_ORDER = ("s_curve", "double_garden", "canyon_relay", "chokepoint", "straight")
DIFFICULTY = {
    "s_curve": "入门", "double_garden": "普通", "canyon_relay": "中等",
    "chokepoint": "中等偏难", "straight": "挑战",
}
OPENINGS = {
    "chokepoint": (((1, 1), "archer"), ((4, 3), "cannon"), ((7, 3), "ice")),
    "straight": (((2, 5), "archer"), ((5, 7), "cannon"), ((5, 5), "ice")),
}
TIPS = {
    "s_curve": "先在前半程建立火力，再向中后段补防；留意转角的重复覆盖。",
    "double_garden": "两处庭院内部适合集中火力；中央连接段和出口仍需补防。",
    "canyon_relay": "前段削血、中段控制、末段补漏；不要只在入口堆单体输出塔。",
    "chokepoint": "参考开局：标记 1 箭塔 → 2 加农炮 → 3 冰塔，共 115 金币；有收入后继续补防。",
    "straight": "参考开局：标记 1 箭塔 → 2 加农炮 → 3 冰塔，共 115 金币；有收入后继续补防。",
}


def recommendation_text(levels):
    numbers = {level.key: index + 1 for index, level in enumerate(levels)}
    return "手动推荐顺序：" + " → ".join(str(numbers[key]) for key in RECOMMENDED_ORDER)
