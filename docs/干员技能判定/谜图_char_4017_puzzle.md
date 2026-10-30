# 谜图 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4017_puzzle` |
| 职业 | 先锋 / `agent` |
| 星级 | 5 星 |
| 生命（精二满级） | 1860 |
| 攻击（精二满级） | 566 |
| 防御（精二满级） | 244 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4017_puzzle_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 40.0%（0.4 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_2_Combat` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 关键线索　`skchr_puzzle_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力300%的物理伤害，并获得3点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 2 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `cost` | 3 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`puzzle_s_1[add_cost]`** ← 事件 `ON_BUFF_START`

- **ModifyCost** 

**`puzzle_s_1[mul_atk]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **AtkScaleUp** 

---

### 疑点追踪　`skchr_puzzle_2`

**技能描述（最高级）：**

> 攻击速度+70，攻击使目标在16秒内每秒受到相当于谜图攻击力15%的法术伤害，效果最多可叠加10次，每次攻击时获得1点部署费用。


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 14 / 26 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 8 秒 |
| duration / durationType | 8 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 70 |
| `attack@atk_scale_2` | 0.15 |
| `attack@addtion_cnt` | 1 |
| `attack@max_cnt` | 10 |
| `cost` | 1 |
| `attack@duration_2` | 16 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`puzzle_s_2[add_cost]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **FilterDamageModifer** `_source`="BUFF_OWNER"
- **ModifyCost** 

**`puzzle_s_2[cnt]`** ← 事件 `ON_BUFF_START`

- **AddBuffBlackboard** `_targetType`="TARGET"

**`puzzle_s_2[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **ApplyCacheAtkDamageByBuffBlackBoardCnt** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
