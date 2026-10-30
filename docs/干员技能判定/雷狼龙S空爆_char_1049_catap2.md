# 雷狼龙S空爆 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1049_catap2` |
| 职业 | 近卫 / `mercenary` |
| 星级 | 5 星 |
| 生命（精二满级） | 3010 |
| 攻击（精二满级） | 544 |
| 防御（精二满级） | 377 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.25 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 10 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.25 ÷ 1.00 = 1.250 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1049_catap2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 42.7%（0.533333 秒 / 1.25 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Begin` | 1.8 秒 | 54 帧 |
| 技能动画 | `Skill_1_Loop_A` | 0.8 秒 | 24 帧 |
| 技能动画 | `Skill_1_Loop_B` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Begin` | 1.2 秒 | 36 帧 |
| 技能动画 | `Skill_2_Loop_A` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Loop_B` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Overload` | 1.5 秒 | 45 帧 |
| 技能动画 | `Skill_2_Overload_B` | 1.5 秒 | 45 帧 |
| 技能动画 | `Skill_Down_1_Loop_A` | 0.8 秒 | 24 帧 |
| 技能动画 | `Skill_Down_1_Loop_B` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Down_2_Overload` | 1.5 秒 | 45 帧 |
| 技能动画 | `Skill_Down_2_Overload_B` | 1.5 秒 | 45 帧 |


## 三、技能逐层拆解

---

### 高压回填斩　`skchr_catap2_1`

**技能描述（最高级）：**

> 消耗20点部署费用，攻击间隔增大，交替使用五连击与十连击攻击阻挡的所有敌人，且每一击附带相当于攻击力35%的法术伤害
> 可充能5次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 5 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 4 秒 |
| duration / durationType | 4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_magic` | 0.35 |
| `base_attack_time` | 1 |
| `cost` | 20 |
| `atk_magic` | 0.35 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`catap2_s1[begin_hit_audio]`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"

**`catap2_s1[five_attack_finish]`** ← 事件 `ON_BUFF_START`

- **UpdateAbilityCoolDown** 

**`catap2_s1[five_hit_audio]`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"

**`catap2_s1[mag_dmg]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"

**`catap2_s1[ten_hit_audio]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **PlayAudio** `_target`="BUFF_OWNER"
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_SOURCE"
  - **PlayAudio** `_target`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_SOURCE"
  - **PlayAudio** `_target`="TARGET"

**`catap2_s1[ten_record]`** ← 事件 `ON_BUFF_START`

- **ModifyBlackboard** 

**`catap2_s1[ten_spell_on]`** ← 事件 `ON_BUFF_START`

- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`catap2_s1[trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **UpdateAbilityCoolDown** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`catap2_s1[trigger]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignCurSpToBB** `_targetType`="BUFF_OWNER"
- **AssignCharacterSkillSpCostToBB** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **BlackboardAdd** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **ClearCharacterSp** `_forceFlag`=False `_charFrom`="BUFF_OWNER"
- **ExtendAbilityCooldown** 
- **BlackboardAdd** 
- **CreateBuffStacked** buffKey=`catap2_s[atk_equip]` 属性修改=[ATK MULTIPLIER blackboard] `maxStackCnt`=100 `overrideType`=STACK `lifeTimeType`=INFINITY

---

### 超高输出属性解放斩　`skchr_catap2_2`

**技能描述（最高级）：**

> 消耗5点部署费用，攻击力和防御力+100%；技能期间可消耗10点部署费用使用装备应变，对前方造成一次相当于攻击力350%的物理伤害，且开启技能时每消耗一层充能附加一次相当于攻击力150%的法术伤害，之后技能立即结束
> 可充能5次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 5 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 4 秒 |
| duration / durationType | 4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `def` | 1 |
| `cost` | 5 |
| `attack@extra_physic_atk_scale` | 3.5 |
| `attack@extra_magic_atk_scale` | 1.5 |
| `retrigger_cost` | 10 |
| `attack@atk` | 1 |
| `attack@def` | 1 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`catap2_s2[extra_ability]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`catap2_s2[extra_shot_disarmed]` `lifeTimeType`=LIMITED
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`catap2_s2[extra_ability_mark]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`catap2_s2[extra_dmg]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="TARGET"
- **AddAbilityBlackboard** 
- **IfElse** 
  - **IsBlackboardEqualWithFloat** 
  - **CreateBuffUseAbilitySelector** buffKey=`catap2_s2[extra_physic_core]` templateKey=`catap2_s2[extra_physic_core]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"
  - **CreateBuffUseAbilitySelector** buffKey=`catap2_s2[extra_magic_core]` templateKey=`catap2_s2[extra_magic_core]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="BUFF_OWNER"
- …（共 33 个节点，已截断）

**`catap2_s2[extra_magic_core]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"

**`catap2_s2[extra_physic_core]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"

**`catap2_s2[init]`** ← 事件 `ON_BUFF_START`

- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 

**`catap2_s2[m3_switch_m0]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **PlayAudio** `_target`="BUFF_OWNER"
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`catap2_s2[predelay_resistance]`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`catap2_s2[resistance]` templateKey=`catap2_s2[resistance]` `lifeTimeType`=LIMITED

**`catap2_s2[resistance]`** ← 事件 `ON_TAKE_DAMAGE`

- **DamageScale** 

**`catap2_s2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`catap2_s2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`catap2_s2[trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **UpdateAbilityCoolDown** 
- **PlayAudio** `_target`="BUFF_OWNER"
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["catap2_s2[extra_ability_mark]"] `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`catap2_s2[trigger]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignCurSpToBB** `_targetType`="BUFF_OWNER"
- **AssignCharacterSkillSpCostToBB** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **BlackboardAdd** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **ClearCharacterSp** `_forceFlag`=False `_charFrom`="BUFF_OWNER"
- **ExtendAbilityCooldown** 
- **BlackboardAdd** 
- **CreateBuffStacked** buffKey=`catap2_s[atk_equip]` 属性修改=[ATK MULTIPLIER blackboard] `maxStackCnt`=100 `overrideType`=STACK `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`catap2_s2[layer_mark]` `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
