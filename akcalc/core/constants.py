"""明日方舟 伤害 / 寻路 计算核心常量。

数值来源：PRTS Wiki「游戏数据基础」「作战机制」逆向数据。
详见项目根目录 arknights_mechanics.md 与 README.md。
"""
from __future__ import annotations

# ---------------------------------------------------------------- 伤害公式

#: 任何伤害类型的保底系数（5%）
MIN_DAMAGE_RATIO = 0.05

#: 法术/元素伤害的百分比系数，官方标称 0.01
#: 注意：PRTS「定点数与浮点数」指出实际存储值略小于 0.01（约 -0.3e-7），
#: 这里保留标称值；如需完全复现游戏可用 0.00999999997
ELEMENT_RATIO = 0.01
ELEMENT_RATIO_EXACT = 0.00999999997

#: 法抗 / 元素抗性以「点数」计（100 = 完全免疫），换算基数
RESIST_BASE = 100

# ---------------------------------------------------------------- 攻速

ATTACK_SPEED_DEFAULT = 100
ATTACK_SPEED_MIN = 10
ATTACK_SPEED_MAX = 600
#: 攻速属性的实际下限（区别于 clamp 的 10）
ATTACK_SPEED_HARD_MIN = 20

# ---------------------------------------------------------------- 寻路

#: 类障碍物地块的地面寻路代价
PATH_COST_OBSTACLE = 1_000
#: 地穴的地面寻路代价（2023-02-14 闪断修复后）
PATH_COST_HOLE = 1_000_000

#: 移动倍率默认值（实际速度 = 标称移速 * move_multiplier * 0.5）
MOVE_MULTIPLIER_DEFAULT = 0.5
#: 移速上限不存在，下限为 0.1
MOVE_SPEED_MIN = 0.1

#: 游戏逻辑帧率
FPS = 30.0

# ---------------------------------------------------------------- 阻挡

#: 地面阻挡半径及其平方（判定实际使用平方值比较）
BLOCK_RADIUS_GROUND = 0.70709997
BLOCK_RADIUS_GROUND_SQ = 0.49999037
#: 飞行阻挡半径系数及其平方
BLOCK_RADIUS_FLY_COEF = 0.8944
BLOCK_RADIUS_FLY_SQ_COEF = 0.79995137

#: 我方干员碰撞体积半径
OPERATOR_COLLISION_RADIUS = 0.25

#: 阻挡偏移：敌人被推到干员的这个半径圆边界上
BLOCK_OFFSET_RADIUS = 0.5
#: 正中心判定阈值（敌我距离小于此值不产生偏移）
CENTER_EPSILON = 0.00001
#: 多敌人二次偏移：检测半径与最大偏移距离
SECONDARY_OFFSET_CHECK_RADIUS = 0.1
SECONDARY_OFFSET_MAX = 0.2

#: 行动受阻时的避障力与寻路加速度系数
AVOID_FORCE_MIN = 0.5
AVOID_ACCEL_COEF = 8.0

# ---------------------------------------------------------------- 位移

#: 力度对应表（描述 -> 力度值）
FORCE_TABLE = {
    "微小力": -1,
    "小力": 0,
    "中力": 1,
    "较大力": 2,
    "大力": 3,
    "大力+1": 4,
    "特大力": 5,
}

#: 推力-位移近似表：(力度-重量) -> (位移格数, 耗时秒)
PUSH_TABLE = {
    -3: (0.0, 0.0),
    -2: (0.12, 0.2),
    -1: (0.44, 0.4),
    0: (1.7, 0.8),
    1: (2.14, 0.9),
    2: (2.96, 1.0667),
    3: (3.53, 1.1667),
}

#: 拉力-位移近似表：(力度-重量) -> 拉力值
PULL_FORCE_TABLE = {
    -3: 0.0,
    -2: 2.0,
    -1: 10.0,
    0: 40.0,
    1: 42.0,
    2: 44.0,
    3: 46.0,
}

# ---------------------------------------------------------------- 伤害类型

DMG_PHYSICAL = "PHYSICAL"
DMG_MAGICAL = "MAGICAL"
DMG_ELEMENTAL = "ELEMENTAL"
DMG_TRUE = "TRUE"
DMG_HEAL = "HEAL"

DMG_TYPE_LABELS = {
    DMG_PHYSICAL: "物理伤害",
    DMG_MAGICAL: "法术伤害",
    DMG_ELEMENTAL: "元素伤害",
    DMG_TRUE: "真实伤害",
    DMG_HEAL: "治疗",
}

# ---------------------------------------------------------------- 地块类型

#: 可通行掩码
PASS_GROUND = "WALK_ONLY"
PASS_FLY = "FLY_ONLY"
PASS_ALL = "ALL"
PASS_NONE = "NONE"

HEIGHT_HIGH = "HIGHLAND"
HEIGHT_LOW = "LOWLAND"
HEIGHT_DEEP = "DEEPWATER"

#: PRTS/游戏中需要高寻路代价的「类障碍物」地块关键字
OBSTACLE_TILE_HINTS = (
    "forbidden",
    "wall",
    "fence",
    "barrier",
    "roadblock",
    "gazebo",
)
#: 地穴关键字
HOLE_TILE_HINTS = ("hole", "pit", "void")

# ---------------------------------------------------------------- 取整

def banker_round(x: float) -> int:
    """四舍六入五成双（银行家舍入），与游戏内 round 行为一致。"""
    import decimal
    return int(decimal.Decimal(str(x)).quantize(
        decimal.Decimal("1"), rounding=decimal.ROUND_HALF_EVEN))