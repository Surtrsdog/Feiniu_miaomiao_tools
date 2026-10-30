# 塑心 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_245_cello` |
| 职业 | 辅助 / `ritualist` |
| 星级 | 6 星 |
| 生命（精二满级） | 1201 |
| 攻击（精二满级） | 485 |
| 防御（精二满级） | 109 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_245_cello_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 27.1%（0.433333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Attack` | 0.866667 秒 | 26 帧 |


## 三、技能逐层拆解

---

### “黄金的狂喜”　`skchr_cello_1`

**技能描述（最高级）：**

> 对一个未处于损伤爆发期间的敌人造成相当于攻击力300%的法术伤害并附带110%攻击力的凋亡损伤
> 可充能3次，技能未开启时无法普通攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 6 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `ep_damage_ratio` | 1.1 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

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

### “安魂的弥撒”　`skchr_cello_2`

**技能描述（最高级）：**

> 攻击速度+60，额外攻击1个目标，自身和攻击范围内攻击力最高的另一名友方干员对敌人造成伤害时附带自身25%攻击力的凋亡损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 24 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 60 |
| `ep_damage_ratio` | 0.25 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`cello_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishDerivedBuff** 
- **CreateBuffUseAbilitySelector** buffKey=`cello_s_2[attack]` templateKey=`cello_s_2[attack]` `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"

**`cello_s_2[attack]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **IfTargetSide** `_targetType`="MODIFIER_TARGET"
- **ApplyElementDamage** `_targetType`="MODIFIER_TARGET"

**`cello_s_2[attack]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["cello_s_2[effect]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`cello_s_2[effect]` templateKey=`cello_s[effect_holder]` `lifeTimeType`=INFINITY

---

### “自由的探戈”　`skchr_cello_3`

**技能描述（最高级）：**

> 停止攻击，攻击范围扩大，攻击力+180%，第二天赋效果提升至2.5倍；技能期间使攻击范围内其他干员生命上限最高的生命上限+30%、攻击力最高的攻击力+30%、防御力最高的防御力+30%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `scale_delta_to_one` | 2.5 |
| `cello_s_3[max_hp].max_hp` | 0.3 |
| `cello_s_3[atk].atk` | 0.3 |
| `cello_s_3[def].def` | 0.3 |

#### 攻击范围

`rangeId = y-8`，23 格（direction=1）

```
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`cello_s_3`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishDerivedBuff** 
- **CreateBuffUseAbilitySelector** buffKey=`cello_s_3[max_hp]` templateKey=`cello_s_3[effect_hp]` 属性修改=[MAX_HP MULTIPLIER blackboard] `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateBuffUseAbilitySelector** buffKey=`cello_s_3[atk]` templateKey=`cello_s_3[effect_atk]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateBuffUseAbilitySelector** buffKey=`cello_s_3[def]` templateKey=`cello_s_3[effect_def]` 属性修改=[DEF MULTIPLIER blackboard] `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"

**`cello_s_3[effect_atk]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["cello_s_3[effect_atk]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`cello_s_3[effect_atk]` templateKey=`cello_s[effect_holder]` `lifeTimeType`=INFINITY

**`cello_s_3[effect_def]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["cello_s_3[effect_def]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`cello_s_3[effect_def]` templateKey=`cello_s[effect_holder]` `lifeTimeType`=INFINITY

**`cello_s_3[effect_hp]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["cello_s_3[effect_hp]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`cello_s_3[effect_hp]` templateKey=`cello_s[effect_holder]` `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
