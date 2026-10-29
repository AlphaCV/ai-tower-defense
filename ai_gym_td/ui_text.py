"""Chinese presentation labels; internal game and policy identifiers stay unchanged."""
import re

TOWER_NAMES = {"archer": "箭塔", "cannon": "加农炮", "ice": "冰塔", "tesla": "电塔"}
MODE_NAMES = {"manual": "手动操作", "ppo": "PPO 自动布塔", "rule": "规则策略", "random": "随机策略"}
STATUS_NAMES = {"RUNNING": "进行中", "PAUSED": "已暂停", "VICTORY": "防守胜利",
                "DEFEAT": "防守失败", "TIME LIMIT": "已达步数上限"}


def status_text(status):
    return STATUS_NAMES.get(status, status)


def message_text(message):
    fixed = {
        "": "",
        "Ready": "准备就绪",
        "Pass": "当前动作：等待，不建造",
        "Build queued": "建造指令已提交",
        "Cannot build: occupied, path, or insufficient gold.": "无法建造：位置被占用、不是草地或金币不足。",
        "AI inference failed; manual mode. See console.": "AI 决策失败，已切回手动。详情见控制台。",
    }
    if message in fixed:
        return fixed[message]
    if message.startswith("PPO unavailable"):
        return "PPO 加载失败，已切回手动。详情见控制台。"
    if message.startswith("Filtered "):
        return "动作不合法，已过滤为等待"
    match = re.fullmatch(r"Build (\w+) at \((\d+), (\d+)\)", message)
    if match:
        name, x, y = match.groups()
        return f"建造{TOWER_NAMES.get(name, name)}，位置（{x}, {y}）"
    return message


def wrap_lines(value, font, width):
    """Chinese has no word spaces, so wrap on glyph boundaries."""
    lines, line = [], ""
    for char in str(value):
        if char == "\n":
            lines.append(line)
            line = ""
            continue
        if line and font.size(line + char)[0] > width:
            lines.append(line.rstrip())
            line = ""
        line += char
    if line:
        lines.append(line.rstrip())
    return lines
