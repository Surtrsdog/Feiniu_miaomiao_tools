# 赫德雷 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4088_hodrer` |
| 职业 | 近卫 / `crusher` |
| 星级 | 6 星 |
| 生命（精二满级） | 5988 |
| 攻击（精二满级） | 1576 |
| 防御（精二满级） | 0 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.5 ÷ 1.00 = 2.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4088_hodrer_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.7 秒** | 21 帧 |

> 占攻击间隔 28.0%（0.7 秒 / 2.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.7 秒 | 21 帧 |
| 技能动画 | `Skill_2_Loop_A` | 0.766667 秒 | 23 帧 |
| 技能动画 | `Skill_2_Loop_B` | 0.766667 秒 | 23 帧 |
| 技能动画 | `Skill_3_Loop` | 0.7 秒 | 21 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.7 秒 | 21 帧 |


## 三、技能逐层拆解

---

### 重锋不熄　`skchr_hodrer_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力260%的物理伤害，并回复自身25%的生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.6 |
| `hp_ratio` | 0.25 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 余烬重荷　`skchr_hodrer_2`

**技能描述（最高级）：**

> 被动效果：攻击力+40%
> 主动触发可以在下列状态和初始状态间切换：
> 攻击间隔略微增大，阻挡数+1，攻击使目标晕眩1秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.4 |
| `base_attack_time` | 0.5 |
| `block_cnt` | 1 |
| `attack@stun` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 死境硝烟　`skchr_hodrer_3`

**技能描述（最高级）：**

> 每秒流失100点生命，并使自身攻击过和攻击过自身的敌人每秒受到200点真实伤害；攻击距离+1，生命上限+60%，攻击力+120%，每次攻击回复自身5%的生命且有25%概率使目标晕眩5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 70 秒 |
| duration / durationType | 70 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 0.6 |
| `atk` | 1.2 |
| `attack@hp_ratio` | 0.05 |
| `attack@buff_prob` | 0.25 |
| `attack@stun` | 5 |
| `ability_range_forward_extend` | 1 |
| `attack@value` | 100 |
| `attack@damage` | 200 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hodrer_s_3[damage]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfTargetSide** `_targetType`="MODIFIER_SOURCE"
- **CheckAbnormalFlag** `_targetType`="MODIFIER_SOURCE"
- **CheckContainsBuff** `_buffKeys`=["hodrer_s_3[burn]"] `_targetType`="MODIFIER_SOURCE"
- **IfNot** 
- **CreateBuff** buffKey=`hodrer_s_3[burn]` templateKey=`hodrer_s_3[periodic]` `lifeTimeType`=INFINITY

**`hodrer_s_3[damage]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **IfTargetSide** `_targetType`="MODIFIER_TARGET"
- **CheckAbnormalFlag** `_targetType`="MODIFIER_TARGET"
- **CheckContainsBuff** `_buffKeys`=["hodrer_s_3[burn]"] `_targetType`="MODIFIER_TARGET"
- **IfNot** 
- **CreateBuff** buffKey=`hodrer_s_3[burn]` templateKey=`hodrer_s_3[periodic]` `lifeTimeType`=INFINITY

**`hodrer_s_3[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **FixedValueDamage** `_targetType`="BUFF_OWNER"

**`hodrer_s_3[periodic]`** ← 事件 `ON_BUFF_TRIGGER`

- **NoSourceDamage** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
