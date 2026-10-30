# 耀骑士临光 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1014_nearl2` |
| 职业 | 近卫 / `fearless` |
| 星级 | 6 星 |
| 生命（精二满级） | 3550 |
| 攻击（精二满级） | 1064 |
| 防御（精二满级） | 295 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 19 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1014_nearl2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 28.9%（0.433333 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_1_Loop_Down` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_3` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Down` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 灿焰长刃　`skchr_nearl2_1`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+70%，攻击速度+50
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.7 |
| `attack_speed` | 50 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 逐夜烁光　`skchr_nearl2_2`

**技能描述（最高级）：**

> 被动效果：部署不消耗部署位。
> 部署后攻击力+160%，获得4层护盾。技能结束后自动撤退，本次再部署时间延长25%，上一名部署干员势力为【卡西米尔】时本次再部署时间不再延长


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 27 秒 |
| duration / durationType | 27 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.6 |
| `times` | 4 |
| `respawn_time` | 1.25 |
| `nearl2_s_2[withdraw][combo].respawn_time` | 1 |
| `value` | 0.25 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nearl2_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
- **CreateBuffs** 
- **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nearl2_s_2[shield][a]` templateKey=`nearl2_s_2[shield]` `lifeTimeType`=INFINITY
- **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nearl2_s_2[shield][b]` templateKey=`nearl2_s_2[shield]` `lifeTimeType`=INFINITY
- **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nearl2_s_2[shield][c]` templateKey=`nearl2_s_2[shield]` `lifeTimeType`=INFINITY
- **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nearl2_s_2[shield][d]` templateKey=`nearl2_s_2[shield]` `lifeTimeType`=INFINITY

**`nearl2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`nearl2_s_2[end]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["nearl2_t_1[mark]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`nearl2_s_2[withdraw][combo]` templateKey=`nearl2_s_2[withdraw]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`nearl2_s_2[withdraw]` templateKey=`nearl2_s_2[withdraw]` `lifeTimeType`=INFINITY

**`nearl2_s_2[shield]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **FinishBuff** 

**`nearl2_s_2[withdraw]`** ← 事件 `ON_BUFF_FINISH`

- **CreateCardBuff** `_target`="BUFF_OWNER"
- **Withdraw** 

---

### 耀阳颔首　`skchr_nearl2_3`

**技能描述（最高级）：**

> 在周围四格可部署地面召唤一把"耀阳"对周围敌人造成110%耀骑士临光攻击力的真实伤害并晕眩3秒，自身攻击范围扩大，攻击力+140%、防御力+100%，攻击自身与"耀阳"阻挡的单位时伤害类型变为真实


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.4 |
| `def` | 1 |
| `value` | 1.1 |
| `value2` | 3 |

#### 攻击范围

`rangeId = 2-1`，9 格（direction=1）

```
■ · · 
■ ■ · 
■ ■ ■ 
■ ■ · 
■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nearl2_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`nearl2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **KillTokens** 

**`nearl2_s_3[damage]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **AdvancedApplyDamage** `_targetType`="TARGET"
  - **IfElse** 
    - **CheckBlocked** `_targetType`="BUFF_OWNER"
    - **AdvancedApplyDamage** `_targetType`="TARGET"
    - **AdvancedApplyDamage** `_targetType`="TARGET"

**`nearl2_s_3[effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckContainsCardBuff** `_target`="BUFF_OWNER" `_key`="nearl2_t_1"
  - **CheckContainsDerviedBuff** 
  - **IfNot** 
  - **CreateBuff** buffKey=`nearl2_s_3[combo_effect]` `lifeTimeType`=INFINITY
  - **FinishDerivedBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
