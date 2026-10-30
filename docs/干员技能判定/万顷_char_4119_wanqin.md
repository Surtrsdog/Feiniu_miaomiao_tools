# 万顷 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4119_wanqin` |
| 职业 | 先锋 / `bearer` |
| 星级 | 5 星 |
| 生命（精二满级） | 1516 |
| 攻击（精二满级） | 514 |
| 防御（精二满级） | 380 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4119_wanqin_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.666667 秒** | 20 帧 |

> 占攻击间隔 51.3%（0.666667 秒 / 1.3 秒）。开技能不会让抬手变快。



## 三、技能逐层拆解

---

### 支援号令·γ型　`skcom_assist_cost[3]`

**技能描述（最高级）：**

> 停止攻击，持续时间内回复总共18点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 26 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 8 秒 |
| duration / durationType | 8 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `value` | 18 |
| `interval` | 0.44 |
| `cost` | 1 |

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

### 应东风　`skchr_wanqin_2`

**技能描述（最高级）：**

> 停止攻击，逐渐回复总共20点部署费用
> 技能期间，每秒治疗周围友方干员相当于万顷25%攻击力的生命值，周围部署方向与万顷相同的干员攻击速度+25


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 16 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@attack_speed` | 25 |
| `attack@heal_scale` | 0.25 |
| `value` | 20 |
| `wanqin_s_2[cost].interval` | 0.75 |
| `wanqin_s_2[cost].cost` | 1 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`wanqin_s_2[buff]`** ← 事件 `ON_BUFF_START`

- **CheckDirection** `_target`="SOURCE" `_source`="BUFF_OWNER"
- **CreateBuff** buffKey=`wanqin_s_2[atk_speed]` 属性修改=[ATTACK_SPEED ADDITION blackboard] `lifeTimeType`=INFINITY

**`wanqin_s_2[buff]`** ← 事件 `ON_DIRECTION_CHANGED`

- **IfElse** 
  - **CheckDirection** `_target`="SOURCE" `_source`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["wanqin_s_2[atk_speed]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`wanqin_s_2[atk_speed]` 属性修改=[ATTACK_SPEED ADDITION blackboard] `lifeTimeType`=INFINITY
  - **FinishDerivedBuff** 

**`wanqin_s_2[hp_recover]`** ← 事件 `ON_BUFF_TRIGGER`

- **AtkToHpRecovery** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
