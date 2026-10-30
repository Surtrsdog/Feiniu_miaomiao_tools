# 佩德洛 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4234_pedro` |
| 职业 | 辅助 / `supportiveranger` |
| 星级 | 5 星 |
| 生命（精二满级） | 1580 |
| 攻击（精二满级） | 765 |
| 防御（精二满级） | 210 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.1 ÷ 1.00 = 2.100 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4234_pedro_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 28.6%（0.6 秒 / 2.1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2` | 0.733333 秒 | 22 帧 |
| 技能动画 | `Skill_Down_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Down_2` | 0.733333 秒 | 22 帧 |


## 三、技能逐层拆解

---

### 标记射击　`skchr_pedro_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至135%，同时攻击2个目标并对目标施加触发型效果（不叠加，优先选择未持有该效果的目标）：受到法术伤害时，额外受到相当于佩德洛220%攻击力的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target` | 2 |
| `atk_scale` | 1.35 |
| `debuff_atk_scale` | 2.2 |

#### 攻击范围

`rangeId = 3-18`，14 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 交替撤离　`skchr_pedro_2`

**技能描述（最高级）：**

> 对范围内的3名干员施加触发型效果（不叠加，优先选择未持有该效果的目标）：生命值低于50%时，立刻治疗相当于佩德洛210%攻击力的生命值且在8秒内不容易受到攻击
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 19 / 22 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.1 |
| `duration` | 8 |
| `taunt_level` | -1 |
| `max_target` | 3 |
| `hp_ratio` | 0.5 |

#### 攻击范围

`rangeId = 3-18`，14 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`pedro_s2`** ← 事件 `ON_BUFF_START`

- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["pedro_s2_buff"] `_targetType`="BUFF_OWNER"
  - **CheckUnitAlive** 
  - **AssignAttributeToBB** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **FilterByExecuteBlackboardValue** `_condType`="GE"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`pedro_s2_buff` templateKey=`pedro_s2_buff` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`pedro_s2_buff` templateKey=`pedro_s2_buff` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
