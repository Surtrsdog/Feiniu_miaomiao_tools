# 百炼嘉维尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1026_gvial2` |
| 职业 | 近卫 / `centurion` |
| 星级 | 6 星 |
| 生命（精二满级） | 2906 |
| 攻击（精二满级） | 766 |
| 防御（精二满级） | 391 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1026_gvial2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 33.3%（0.4 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_2_Loop_Down` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 精准痛击　`skchr_gvial2_1`

**技能描述（最高级）：**

> 攻击力+80%，每次攻击治疗自身相当于造成伤害40%的生命值


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `heal_scale` | 0.4 |

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

### 链锯强袭　`skchr_gvial2_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+180%，防御力+50%；攻击到未被阻挡的敌人时，将其中等力度地拖拽至面前


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `def` | 0.5 |
| `block_cnt` | 0 |
| `attack@force` | 1 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`gvial2_s_2[drag]`** ← 事件 `ON_BUFF_START`

- **CheckBlocked** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **EmitProjectile** `_targetType`="TARGET"

---

### 丛林之魂　`skchr_gvial2_3`

**技能描述（最高级）：**

> 攻击力+140%，攻击速度+100，阻挡数+2，技能期间暂时只受到50%的伤害，其余伤害延后至技能结束，变为持续20秒等量的生命流失效果


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.4 |
| `attack_speed` | 100 |
| `damage_resistance` | 0.5 |
| `final_duration` | 20 |
| `interval` | 0.1 |
| `priority` | 1000 |
| `block_cnt` | 2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`gvial2_s_3`** ← 事件 `ON_TAKE_DAMAGE`

- **DamageScale** 

**`gvial2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`gvial2_s_3[final_bleed]` templateKey=`gvial2_s_3[bleed]` `lifeTimeType`=LIMITED

**`gvial2_s_3[bleed]`** ← 事件 `ON_BUFF_TRIGGER`

- **FixedValueDamage** `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
