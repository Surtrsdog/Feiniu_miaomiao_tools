# 黍 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_2025_shu` |
| 职业 | 重装 / `guardian` |
| 星级 | 6 星 |
| 生命（精二满级） | 3213 |
| 攻击（精二满级） | 479 |
| 防御（精二满级） | 602 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 22 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_2025_shu_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 44.4%（0.533333 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_3_Attack_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_3_Attack_2` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 化被草木　`skchr_shu_1`

**技能描述（最高级）：**

> 下一次攻击会为周围血量不足一半的一名友方单位恢复相当于攻击力180%的生命
> 可充能3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 1.8 |
| `ct` | 3 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 嘉禾盈仓　`skchr_shu_2`

**技能描述（最高级）：**

> 停止攻击专注治疗范围内至多两名我方单位，攻击力+120%，阻挡数+1，第一天赋效果提升至1.5倍
> 治疗拥有特殊间隔


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.2 |
| `extra_extend_scale` | 1.5 |
| `block_cnt` | 1 |
| `attack@max_target` | 2 |
| `base_attack_time` | 1.3 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`shu_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **ModifyAbilityBlackboard** 
- **RefreshAttachListenerToTileAbility** 

**`shu_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **ModifyAbilityBlackboard** 
- **RefreshAttachListenerToTileAbility** 

---

### 离离枯荣　`skchr_shu_3`

**技能描述（最高级）：**

> 治疗范围扩大，攻击同时可治疗我方干员，攻击力+50%，有地面敌人处于播种地块时技能范围内的我方单位攻击力+25%、攻击速度+25，敌人经过播种地块时获得如下效果：当远离该地块超过2格时被传送回该地块


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `e_atk` | 0.25 |
| `e_attack_speed` | 25 |
| `e_max_stack_cnt` | 1 |
| `max_distance` | 2 |

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

> 匹配方式：按命名规则匹配（层级 B）

**`shu_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`shu_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`shu_s_3`** ← 事件 `ON_OUTPUT_MODIFIER`

- **IsHeal** 
- **TriggerAbility** `_targetType`="MODIFIER_TARGET"

**`shu_s_3`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **RefreshAttachListenerToTileAbility** 

**`shu_s_3`** ← 事件 `ON_BUFF_TRIGGER`

- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **IfNot** 
- **ModifyBlackboard** 
- **CalculateBlackboardValueViaParams** 
- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **IfNot** 
- **ModifyBlackboard** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ALLY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

**`shu_s_3[enemy][enter]`** ← 事件 `ON_BUFF_START`

- **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **CreateBuff** buffKey=`shu_s_3[trigger]` templateKey=`shu_s_3[trigger]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **CheckContainsBuff** `_buffKeys`=["shu_s_3[enemy][mark]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`shu_s_3[enemy][mark]` templateKey=`shu_s_3[enemy][mark]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`shu_s_3[enemy][enter]`** ← 事件 `ON_BUFF_FINISH`

- **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **CreateBuff** buffKey=`shu_s_3[trigger]` templateKey=`shu_s_3[trigger]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`shu_s_3[enemy][enter]`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["shu_s_3"] `_targetType`="BUFF_SOURCE"
  - **AttachAsDerivedBuffById** 
  - **FinishBuff** 

**`shu_s_3[enemy][leave]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`shu_s_3[enemy][mark]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckEntityDisappeared** `_targetType`="BUFF_OWNER"
  - **FinishBuff** 
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["shu_s_3"] `_targetType`="BUFF_SOURCE"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["immune_shu_blink"] `_targetType`="BUFF_OWNER"
      - **FinishBuff** 
      - **AttachAsDerivedBuffById** 
      - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
      - **AssignRootTileToBB** `_targetType`="BUFF_OWNER"
    - **FinishBuff** 

**`shu_s_3[enemy][mark]`** ← 事件 `ON_BEFORE_DISAPPEAR`

- **FinishBuff** 

**`shu_s_3[enemy][mark]`** ← 事件 `ON_OWNER_ROOT_TILE_CHANGED`

- **FilterRootTileOffset** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **TriggerBuff** 

**`shu_s_3[enemy][mark]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckAbnormalCombo** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateEffect** `_targetType`="TARGET"
- **ForceSetToTilePosition** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="TARGET"

**`shu_s_3[heal_in_attack]`** ← 事件 `ON_BUFF_START`

- **CreateBuffUseAbilitySelector** buffKey=`shu_s_3[heal]` templateKey=`heal_on_start` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"

**`shu_s_3[in_range]`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **TriggerBuff** 

**`shu_s_3[in_range]`** ← 事件 `ON_BUFF_TRIGGER`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
- **AttributeModifierWithBB** `_targetType`="BUFF_OWNER"
- **AttributeModifierWithBB** `_targetType`="BUFF_OWNER"

**`shu_s_3[refresh][buff]`** ← 事件 `ON_BUFF_START`

- **TriggerBuffsByKeys** `_buffKeys`=["shu_s_3[in_range]"] `_targetType`="BUFF_OWNER"

**`shu_s_3[trigger]`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **TriggerBuffsByKeys** `_buffKeys`=["shu_s_3"] `_targetType`="BUFF_OWNER"
- **FinishBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
