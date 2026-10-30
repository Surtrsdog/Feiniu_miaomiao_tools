# 水月 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_437_mizuki` |
| 职业 | 特种 / `stalker` |
| 星级 | 6 星 |
| 生命（精二满级） | 1758 |
| 攻击（精二满级） | 865 |
| 防御（精二满级） | 356 |
| 法抗 | 3000% |
| **攻击间隔 baseAttackTime** | **3.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 0 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 3.5 ÷ 1.00 = 3.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_437_mizuki_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 15.2%（0.533333 秒 / 3.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 唤醒　`skchr_mizuki_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力300%的物理伤害，且第一天赋伤害倍率提升至3倍
> 可充能3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `talent_scale` | 3 |
| `cnt` | 3 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

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

### 囚徒困境　`skchr_mizuki_2`

**技能描述（最高级）：**

> 攻击间隔较大幅度缩短，攻击力+30%，第一天赋额外攻击1个目标并附加1.3秒束缚


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 21 秒 |
| duration / durationType | 21 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -1.5 |
| `atk` | 0.3 |
| `attack@unmovable` | 1.3 |
| `attack@max_target` | 1 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

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

### 镜花水月　`skchr_mizuki_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+150%，第一天赋额外攻击2个目标并附加1秒晕眩；每次攻击命中目标少于3名敌人时，自身流失最大生命值的12%。


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `attack@stun` | 1 |
| `attack@hp_ratio` | 0.12 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = y-4`，19 格（direction=1）

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mizuki_s_3[damage]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"
- **DamageViaMaxHpRatio** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
