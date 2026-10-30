# 年 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_2014_nian` |
| 职业 | 重装 / `protector` |
| 星级 | 6 星 |
| 生命（精二满级） | 3699 |
| 攻击（精二满级） | 619 |
| 防御（精二满级） | 726 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_2014_nian_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.1 秒** | 3 帧 |

> 占攻击间隔 6.7%（0.1 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Begin` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop` | 0.1 秒 | 3 帧 |


## 三、技能逐层拆解

---

### 锡灼　`skchr_nian_1`

**技能描述（最高级）：**

> 防御力+70%，攻击力+45%，普通攻击造成法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.45 |
| `def` | 0.7 |

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

### 铜印　`skchr_nian_2`

**技能描述（最高级）：**

> 停止攻击；防御力+130%，阻挡数+1，每次受到攻击时对目标造成相当于年攻击力90%的法术伤害并使其失去特殊能力5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 1.3 |
| `block_cnt` | 1 |
| `atk_scale` | 0.9 |
| `silence` | 5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nian_s_2`** ← 事件 `ON_TAKE_DAMAGE`

- **VertifyTarget** `_target`="MODIFIER_SOURCE" `_source`="MODIFIER_TARGET" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateBuffById** 

---

### 铁御　`skchr_nian_3`

**技能描述（最高级）：**

> 攻击力+120%；周围其他友方干员的防御力+80%，阻挡数+1，并获得抵抗


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 70 / 85 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 45 秒 |
| duration / durationType | 45 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `nian_s_3[self].block_cnt` | 0 |
| `nian_s_3[ally].block_cnt` | 1 |
| `nian_s_3[ally].def` | 0.8 |
| `one_minus_status_resistance` | -0.5 |
| `nian_s_3[self].atk` | 1.2 |

#### 攻击范围

`rangeId = x-2`，21 格（direction=1）

```
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
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
