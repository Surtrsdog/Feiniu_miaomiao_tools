# 伺夜 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_427_vigil` |
| 职业 | 先锋 / `tactician` |
| 星级 | 6 星 |
| 生命（精二满级） | 1755 |
| 攻击（精二满级） | 462 |
| 防御（精二满级） | 154 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_427_vigil_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.266667 秒** | 8 帧 |

> 占攻击间隔 26.7%（0.266667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill3_Attack_A` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill3_Attack_B` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill3_Attack_C` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 领袖的呼唤　`skchr_vigil_1`

**技能描述（最高级）：**

> 立即获得7点部署费用，并增加一只“狼影”


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 21 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 7 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vigil_s_1[enhance]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckFirstRallyPointMode** 
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

### 领袖的馈赠　`skchr_vigil_2`

**技能描述（最高级）：**

> 立即获得2点部署费用，并使狼群下次攻击的攻击力提升至200%且狼群恢复20%生命值；若狼群击倒敌人则额外获得1点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 4 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 2 |
| `vigil_wolf_s_2.atk_scale` | 2 |
| `vigil_wolf_s_2.hp_ratio` | 0.2 |
| `vigil_wolf_s_2.cost` | 1 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vigil_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

### 领袖的尊严　`skchr_vigil_3`

**技能描述（最高级）：**

> 技能持续时间内逐渐获得12点部署费用，攻击变为三连击；狼群与伺夜攻击被狼群阻挡的单位造成伤害时，额外造成相当于伺夜攻击力50%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@vigil_s_3.atk_scale` | 0.5 |
| `value` | 12 |
| `interval` | 1.25 |
| `cost` | 1 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vigil_s_3[buff]`** ← 事件 `ON_BUFF_START`

- **CheckBlocked** `_targetType`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="TARGET"

**`vigil_s_3[buff_token]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`vigil_s_3[buff_token]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
