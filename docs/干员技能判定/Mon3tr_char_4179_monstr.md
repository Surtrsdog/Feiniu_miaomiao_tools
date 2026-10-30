# Mon3tr — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4179_monstr` |
| 职业 | 医疗 / `chainhealer` |
| 星级 | 6 星 |
| 生命（精二满级） | 1735 |
| 攻击（精二满级） | 528 |
| 防御（精二满级） | 221 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 18 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4179_monstr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.566667 秒** | 17 帧 |

> 占攻击间隔 19.9%（0.566667 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_2_Loop` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_3_Loop` | 0.666667 秒 | 20 帧 |


## 三、技能逐层拆解

---

### 策略：超压链接　`skchr_monstr_1`

**技能描述（最高级）：**

> 下次治疗可以恢复相当于攻击力200%的生命，治疗的跳跃次数+1


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 2 |
| `chain.max_target` | 4 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`monstr_s_1[ready]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=1 `_targetType`="BUFF_OWNER"
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="monstr_s_1[ready_eff]"
  - **IfNot** 
  - **CreateBuff** buffKey=`monstr_s_1[ready_eff]` `lifeTimeType`=INFINITY
  - **FinishDerivedBuff** 

---

### 策略：超负荷　`skchr_monstr_2`

**技能描述（最高级）：**

> 技能期间优先治疗重构体，重构体每受到一次Mon3tr的治疗，就会进行一次跳跃治疗，第二天赋的效果提升至2.8倍


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 13 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `talent_scale` | 2.8 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`monstr_s_2[mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`monstr_s_2[mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`monstr_s_2[proj]`** ← 事件 `ON_BUFF_FINISH`

- **FilterId** `_targetType`="BUFF_OWNER"
- **EmitProjectile** `_targetType`="BUFF_OWNER"

---

### 策略：熔毁　`skchr_monstr_3`

**技能描述（最高级）：**

> 攻击范围改变，移动至重构体位置，攻击力+330%，攻击间隔降低，阻挡数+2，生命上限+5000，每秒流失80点生命值，同时攻击阻挡的所有敌人，伤害类型变为真实，攻击治疗自身相当于攻击力50%的生命值
> 技能结束或受到致命伤害时，返回初始位置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 11 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 3.3 |
| `damage_per_second` | 80 |
| `max_hp` | 5000 |
| `block_cnt` | 2 |
| `base_attack_time` | -1.5 |
| `attack@heal_scale` | 0.5 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`monstr_s_3[bleeding]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["monstr_s_3[undeadable]"] `_targetType`="BUFF_OWNER"
  - **FixedValueDamage** `_targetType`="BUFF_OWNER"

**`monstr_s_3[bleeding]`** ← 事件 `ON_BUFF_START`

- **CalculateBlackboardValueViaParams** 

**`monstr_s_3[heal_chain]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`monstr_s_3[reborned_passive]`** ← 事件 `ON_BUFF_START`

- **ClearCharacterSp** `_forceFlag`=True `_charFrom`="BUFF_OWNER"
- **CreateBuff** buffKey=`monstr_s_3[undead]` templateKey=`monstr_s_3[undead]` `lifeTimeType`=INFINITY
- **CreateCardBuffToMyToken** 
- **AddExcludeCharacterToDynamicBuffTile** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"
- **ForceCharacterAnimatorFaceFront** 
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SetAdditonalBuildCondition** `_target`="BUFF_OWNER"

**`monstr_s_3[reborned_passive]`** ← 事件 `ON_BUFF_FINISH`

- **FinishCardBuff** 
- **ForceCharacterAnimatorFaceFront** 

**`monstr_s_3[restore_mode]`** ← 事件 `ON_OWNER_FINISH`

- **AssignHpRatioToBB** `_targetType`="BUFF_OWNER"
- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`monstr_s_3[restore_mode]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`monstr_s_3[route]`** ← 事件 `ON_BUFF_FINISH`

- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`monstr_s_3[route]`** ← 事件 `ON_OWNER_BORN`

- **IfElse** 
  - **FilterByCharacterSharedBlackboard** `_condType`="GT" `_target`="BUFF_OWNER"
  - **ForceCharacterAnimatorFaceFront** 
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **IfElse** 
    - **FilterByCharacterSharedBlackboard** `_condType`="GT" `_target`="BUFF_OWNER"
    - **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=3 `_target`="BUFF_OWNER"
    - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
    - **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=True
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=3 `_target`="BUFF_OWNER"
    - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`monstr_s_3[sync_hp]`** ← 事件 `ON_BUFF_START`

- **AssignCharacterSharedBBToBlackboard** 
- **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- **FetchHpToBlackboard** `_targetType`="BUFF_OWNER"

**`monstr_s_3[sync_hp]`** ← 事件 `ON_OWNER_FINISH`

- **IfElse** 
  - **FilterDeathReason** `_source`="BUFF_OWNER"
  - **AssignHpRatioToBB** `_targetType`="BUFF_OWNER"
  - **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"
  - **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`monstr_s_3[undead]`** ← 事件 `ON_BEFORE_TRY_SET_HP_ZERO`

- **CreateBuff** buffKey=`monstr_s_3[undeadable]` `lifeTimeType`=INFINITY
- **AssignHpRatioToBB** `_targetType`="BUFF_OWNER"
- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
