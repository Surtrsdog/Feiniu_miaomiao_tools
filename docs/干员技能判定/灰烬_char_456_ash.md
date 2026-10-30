# 灰烬 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_456_ash` |
| 职业 | 狙击 / `fastshot` |
| 星级 | 6 星 |
| 生命（精二满级） | 1689 |
| 攻击（精二满级） | 534 |
| 防御（精二满级） | 169 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_456_ash_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0 秒** | 0 帧 |

> 占攻击间隔 0.0%（0 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_1_Loop_Down` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop_Down` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_3` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_3_Down` | 0.566667 秒 | 17 帧 |


> ⚠️ **本条需实测复核**：`Attack_Loop` 动画的 `OnAttack` 事件落在第 0 帧（t = 0）。
>
> 含义：该循环动画的伤害帧就是循环起点帧。但**首次**攻击的抬手可能由另一段入场攻击动画决定，不能直接当成 0。
>
> 该干员其他含 `OnAttack` 的动画：`Start_Attack` 0.233 秒、`Skill_3` 0.567 秒、`Skill_3_Down` 0.567 秒

## 三、技能逐层拆解

---

### 支援射击　`skchr_ash_1`

**技能描述（最高级）：**

> 攻击力+15%，攻击变为2连击
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.15 |
| `attack@times` | 2 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 突击战术　`skchr_ash_2`

**技能描述（最高级）：**

> 立即触发第一天赋，攻击间隔大幅度缩短，且攻击被晕眩目标时攻击力提高至250%
> 攻击装有31发子弹，打完后技能结束（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.8 |
| `ash_s_2[atk_scale].atk_scale` | 2.5 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`ash_s_2[atk_scale]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **CheckAbnormalFlag** `_targetType`="TARGET"
- **AtkScaleUp** 

**`ash_s_2[atk_scale]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`ash_s_2[audio_start]` `lifeTimeType`=IMMEDIATELY

**`ash_s_2[atk_scale]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuff** buffKey=`ash_s_2[audio_finish]` `lifeTimeType`=IMMEDIATELY

**`ash_s_2[interrupt]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptCharacterAbility** `_charFrom`="BUFF_OWNER"

**`ash_s_2[trigger_ability]`** ← 事件 `ON_BUFF_START`

- **TriggerAbilityUseSelector** `_targetType`="BUFF_SOURCE"

---

### 攻坚榴弹　`skchr_ash_3`

**技能描述（最高级）：**

> 向前发射破墙弹，对沿途敌人造成300%的物理伤害并向后较大力度推动；爆炸对周围造成400%的物理伤害（从低地撞到高台直接爆炸且造成800%的物理伤害）；每次部署只能释放2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `force` | 2 |
| `not_hitwall_scale` | 4 |
| `hitwall_scale` | 8 |
| `range_radius` | 1.5 |

#### 攻击范围

`rangeId = 4-1`，5 格（direction=1）

```
■ ■ ■ ■ ■ 
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
