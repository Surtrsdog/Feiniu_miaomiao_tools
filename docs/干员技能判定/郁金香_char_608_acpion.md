# 郁金香 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_608_acpion` |
| 职业 | 先锋 / `pioneer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2095 |
| 攻击（精二满级） | 500 |
| 防御（精二满级） | 370 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_608_acpion_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.3 秒** | 9 帧 |

> 占攻击间隔 28.6%（0.3 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 钻心　`skchr_acpion_1`

**技能描述（最高级）：**

> 立即获得6点部署费用，并对攻击范围至多2名敌人造成攻击力230%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 6 |
| `atk_scale` | 2.3 |
| `max_target` | 2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`acpion_s_1[cost]`** ← 事件 `ON_SKILL_CAST_SUCCEED`

- **IfElse** 
  - **IsBlackboardZero** 
  - **ModifyCost** 
- **AlwaysNext** 
- **AssignValueToBB** 

**`acpion_s_1[cost]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IsBlackboardZero** 
  - **CheckCharSkillAvailable** `_targetType`="BUFF_OWNER"
  - **ModifyCost** 
  - **BlackboardAdd** 

---

### 迅瞬　`skchr_acpion_2`

**技能描述（最高级）：**

> 技能持续时间内逐渐获得8点部署费用，攻击速度+125，并无视目标35%的防御力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 22 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 1 |
| `interval` | 1.2 |
| `trig_cnt` | 8 |
| `attack_speed` | 125 |
| `def_penetrate` | 0.35 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`acpion_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **ModifyCost** 

---

### 只余芬芳　`skchr_acpion_3`

**技能描述（最高级）：**

> 立即获得8点费用，对周围的敌人发动8次连续斩击，每次造成相当于攻击力200%的物理伤害，并无视目标50%防御力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 8 |
| `atk_scale` | 2 |
| `def_penetrate` | 0.5 |
| `times` | 8 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
