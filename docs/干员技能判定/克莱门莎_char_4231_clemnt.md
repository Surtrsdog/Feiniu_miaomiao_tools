# 克莱门莎 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4231_clemnt` |
| 职业 | 近卫 / `primguard` |
| 星级 | 6 星 |
| 生命（精二满级） | 2720 |
| 攻击（精二满级） | 920 |
| 防御（精二满级） | 371 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4231_clemnt_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.366667 秒** | 11 帧 |

> 占攻击间隔 30.6%（0.366667 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_Begin` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Loop` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_Down_2_Begin` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 冲蚀　`skchr_clemnt_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提高至290%并造成相当于物理伤害35%的侵蚀损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.9 |
| `ep_damage_ratio` | 0.35 |

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

### 风暴潮　`skchr_clemnt_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击速度+100，每次攻击对目标及其周围最多5名地面敌人造成相当于攻击力250%的物理伤害；向前方召唤浮游放逐舱，放逐舱使周围累计不超过8重量的最多15名地面敌人不断向前移动；放逐舱在移动3格后消失并留下漩涡，处于漩涡的所有敌人移动速度-70%且每秒受到200点侵蚀损伤和相当于攻击力300%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 100 |
| `attack@aoe_atk_scale` | 2.5 |
| `attack@max_passenger_mass` | 8 |
| `attack@max_passenger_cnt` | 15 |
| `attack@move_speed` | -0.7 |
| `attack@water_element` | 200 |
| `attack@physical_atk_scale` | 3 |
| `attack@max_target` | 5 |

#### 攻击范围

`rangeId = 4-1`，5 格（direction=1）

```
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`clemnt_s2[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **ApplyElementDamage** `_targetType`="TARGET"
- **AlwaysNext** 
- **AdvancedApplyDamage** `_targetType`="TARGET"

**`clemnt_s2[emit_projectile]`** ← 事件 `ON_BUFF_START`

- **IfConditions** 
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **EmitProjectile** `_targetType`="TARGET"
    - **TriggerBuffsByKeys** `_buffKeys`=["clemnt_s2[emit_projectile]"] `_targetType`="PROJECTILE_SOURCE"
  - **EmitProjectile** `_targetType`="TARGET"
    - **TriggerBuffsByKeys** `_buffKeys`=["clemnt_s2[emit_projectile]"] `_targetType`="PROJECTILE_SOURCE"
- **ModifyBlackboard** 
- **ModifyBlackboard** 
- **CreateBuff** buffKey=`clemnt_s2[mass_not_full_effect]` `lifeTimeType`=INFINITY

**`clemnt_s2[emit_projectile]`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishDerivedBuff** 
- **EmitProjectile** `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`clemnt_s2[emit_projectile]`** ← 事件 `ON_BUFF_FINISH`

- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"

**`clemnt_s2[projectile_hit]`** ← 事件 `ON_BUFF_START`

- **AttachAsDerivedBuffById** 
- **CheckEntityDisappeared** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["immune_shu_blink", "immune_yu_blink", "immune_clemnt_blink"] `_targetType`="BUFF_OWNER"
  - **CheckEntityDisappeared** `_targetType`="BUFF_OWNER"
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **CheckAbnormalComboImmune** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **CheckMotionMode** `_targetType`="BUFF_OWNER"
    - **IfTarget** `_targetType`="BUFF_OWNER"
    - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="SOURCE"
    - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
    - **CalculateBlackboardValueViaParams** 
    - **AssignBuffBlackboard** `_targetType`="SOURCE"
    - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="SOURCE"
- …（共 19 个节点，已截断）

**`clemnt_s2[projectile_hit]`** ← 事件 `ON_BUFF_TRIGGER`

- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckEntityDisappeared** `_targetType`="BUFF_OWNER"
  - **FinishBuff** 
  - **AssignProjectileGridPosToBB** 
  - **IfElse** 
    - **CheckEnemyRealReachableToTile** 
    - **ForceSetToProjectilePosition** `_target`="BUFF_OWNER"
    - **FinishBuff** 

**`clemnt_s2[projectile_hit]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **ModifyBlackboard** 

**`clemnt_s2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **CreateBuff** buffKey=`clemnt_s2[force_disarmed]` `lifeTimeType`=LIMITED

**`clemnt_s2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`clemnt_s2[sync_passenger_info]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **BlackboardAdd** 
- **BlackboardAdd** 
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`clemnt_s2[mass_full_effect]` `lifeTimeType`=INFINITY

---

### 与海为敌　`skchr_clemnt_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击目标数+2，每次攻击对目标造成相当于攻击力235%的物理伤害并额外造成相当于物理伤害20%的侵蚀损伤；当全场有敌人侵蚀损伤爆发时，消耗1发弹药对目标所在位置及其周围四格内所有地面敌人造成3次相当于攻击力300%的物理伤害与相当于攻击力250%的元素伤害
> 技能装有10发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 42 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | 0 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@max_target` | 3 |
| `attack@atk_scale` | 2.35 |
| `attack@ep_damage_ratio` | 0.2 |
| `attack@ep_break_duration` | 1 |
| `projectile_life_time` | 3.5 |
| `s3_atk_scale` | 3 |
| `ep_damage_scale` | 2.5 |
| `trigger_time` | 10 |
| `audio_trigger_cnt` | 3 |
| `ep_break_duration` | 1 |

#### 攻击范围

`rangeId = 3-2`，4 格（direction=1）

```
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`clemnt_s3[emit_projectile]`** ← 事件 `ON_BUFF_START`

- **EmitProjectile** `_targetType`="BUFF_OWNER"

**`clemnt_s3[ep_break_listener]`** ← 事件 `ON_EP_BREAK_START`

- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`clemnt_s3[ep_break_mark]` `lifeTimeType`=LIMITED

**`clemnt_s3[rocket_damage]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"
- **AlwaysNext** 
- **AdvancedApplyDamage** `_targetType`="TARGET"

**`clemnt_s3[rocket_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **AssignAmmoSkillRemainingCountToBB** `_targetType`="BUFF_OWNER"
  - **IsBlackboardZero** 
  - **IfNot** 
  - **TriggerAbilityUseSelector** `_targetType`="BUFF_OWNER"

**`clemnt_s3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`clemnt_s3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
