# 折光 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_499_kaitou` |
| 职业 | 术师 / `primcaster` |
| 星级 | 5 星 |
| 生命（精二满级） | 1309 |
| 攻击（精二满级） | 578 |
| 防御（精二满级） | 111 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_499_kaitou_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 37.5%（0.6 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 镭射穿凿　`skchr_kaitou_1`

**技能描述（最高级）：**

> 攻击力+110%，攻击附带造成法术伤害15%的凋亡损伤，若目标处于凋亡损伤爆发期间则对其额外造成相当于攻击力50%的元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.1 |
| `attack@ep_damage_ratio` | 0.15 |
| `attack@extra_ep_damage_scale` | 0.5 |

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

**`kaitou_s_1[ep_damage]`** ← 事件 `ON_BUFF_START`

- **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 热处理变色　`skchr_kaitou_2`

**技能描述（最高级）：**

> 攻击速度+90，额外攻击1个目标，攻击对处于凋亡损伤爆发期间的目标额外造成相当于攻击力75%的元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 90 |
| `attack@extra_ep_damage_scale` | 0.75 |

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

**`kaitou_s_2[ep_damage]`** ← 事件 `ON_BUFF_START`

- **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
