# 诺威尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4173_nowell` |
| 职业 | 医疗 / `healer` |
| 星级 | 5 星 |
| 生命（精二满级） | 1367 |
| 攻击（精二满级） | 516 |
| 防御（精二满级） | 108 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4173_nowell_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.633333 秒** | 19 帧 |

> 占攻击间隔 22.2%（0.633333 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 步履不停　`skchr_nowell_1`

**技能描述（最高级）：**

> 攻击力+40%，攻击速度+40，优先治疗处于异常状态中的友方干员


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.4 |
| `attack_speed` | 40 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 生命不息　`skchr_nowell_2`

**技能描述（最高级）：**

> 立即为攻击范围内三名友方干员施加一个增益（优先选择处于异常状态中的干员），使其12秒内每秒受到一次相当于诺威尔攻击力45%的治疗并获得抵抗


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 12 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target` | 3 |
| `status_resistance[limit]` | 12 |
| `interval` | 1 |
| `heal_scale` | 0.45 |
| `nowell_s_2[immediately_heal].heal_scale` | 0 |
| `one_minus_status_resistance` | 0.5 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`nowell_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"

**`nowell_s_2`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nowell_s_2[immediately_heal]` templateKey=`nowell_s_2[immediately_heal]` `lifeTimeType`=IMMEDIATELY
- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_SOURCE"

**`nowell_s_2[immediately_heal]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
