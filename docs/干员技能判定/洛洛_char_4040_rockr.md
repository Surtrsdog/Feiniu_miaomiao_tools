# 洛洛 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4040_rockr` |
| 职业 | 术师 / `funnel` |
| 星级 | 5 星 |
| 生命（精二满级） | 1468 |
| 攻击（精二满级） | 320 |
| 防御（精二满级） | 123 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4040_rockr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 38.5%（0.5 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 战术咏唱·γ型　`skcom_magic_rage[3]`

**技能描述（最高级）：**

> 攻击速度+90


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 90 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 自负此轭　`skchr_rockr_2`

**技能描述（最高级）：**

> 攻击速度+80，释放浮游单元锁定敌人攻击
> 过载：特性浮游单元伤害上限提升至2倍，攻击力+50%，技能结束后晕眩过载持续时间的等长时间
> 浮游单元锁敌后直至敌人被击杀或技能结束后返回干员身边，可随时主动关闭技能


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack_speed` | 80 |
| `attack@cnt` | 0 |
| `scale` | 2 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`rockr_s_2[attack_hit_audio]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["rockr_s_2[overload]"] `_targetType`="BUFF_SOURCE"
  - **CreateBuff** buffKey=`rockr_s_2[attack_audio]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`rockr_s_2[attack_audio]` `lifeTimeType`=IMMEDIATELY

**`rockr_s_2[attack_start_audio]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["rockr_s_2[overload]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`rockr_s_2[attack_audio]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`rockr_s_2[attack_audio]` `lifeTimeType`=IMMEDIATELY

**`rockr_s_2[funnel_hit_audio]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["rockr_s_2[overload]"] `_targetType`="BUFF_SOURCE"
  - **CreateBuff** buffKey=`rockr_s_2[funnel_hit_audio]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`rockr_s_2[funnel_hit_audio]` `lifeTimeType`=IMMEDIATELY

**`rockr_s_2[overload]`** ← 事件 `ON_BUFF_FINISH`

- **IfTarget** `_targetType`="BUFF_OWNER"
- **AssignBuffExistingTimeIntoBlackboard** 
- **CreateBuffById** 
- **ModifyFunnelMaxAtkScaleMultiplier** 
- **CreateEffect** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="TARGET"
- **CreateBuff** buffKey=`rockr_s_2[overload_finish]` `lifeTimeType`=IMMEDIATELY

**`rockr_s_2[overload]`** ← 事件 `ON_BUFF_START`

- **ModifyFunnelMaxAtkScaleMultiplier** 

**`rockr_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`rockr_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
