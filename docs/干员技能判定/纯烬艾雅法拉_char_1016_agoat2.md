# 纯烬艾雅法拉 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1016_agoat2` |
| 职业 | 医疗 / `wandermedic` |
| 星级 | 6 星 |
| 生命（精二满级） | 1439 |
| 攻击（精二满级） | 424 |
| 防御（精二满级） | 109 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1016_agoat2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 14.0%（0.4 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Loop` | 0.266667 秒 | 8 帧 |


## 三、技能逐层拆解

---

### 无声润物　`skchr_agoat2_1`

**技能描述（最高级）：**

> 攻击力+40%，每次可额外治疗一名单位，攻击范围内所有友方单位每秒回复纯烬艾雅法拉攻击力8%的元素损伤
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
| `atk` | 0.4 |
| `agoat2_s_1[aura].ep_heal_ratio` | 0.08 |

#### 攻击范围

`rangeId = 3-17`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`agoat2_s_1[activate]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

### 云霭荫佑　`skchr_agoat2_2`

**技能描述（最高级）：**

> 立即对攻击范围内所有友方单位进行一次治疗，并生成一个持续20秒的范围损伤屏障，为范围内的友方单位吸收相当于攻击力900%的元素损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `agoat2_s_2[shield].atk_scale` | 9 |
| `duration` | 20 |

#### 攻击范围

`rangeId = 3-17`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`agoat2_s_2`** ← 事件 `ON_APPLYING_MODIFIER`

- **IsElementDamage** 
- **BlockElementDamage** 

**`agoat2_s_2[activate]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["agoat2_s_2[shield]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`agoat2_s_2[shield]` templateKey=`agoat2_s_2[shield]` `lifeTimeType`=IMMEDIATELY
  - **TriggerAbility** `_targetType`="BUFF_OWNER"

**`agoat2_s_2[shield]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["agoat2_s_2[in_skill]"] `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **InterruptAbility** 
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["agoat2_s_2[shield][timing]"] `_targetType`="BUFF_OWNER"
      - **InterruptAbility** 
      - **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`agoat2_s_2[shield]`** ← 事件 `ON_BUFF_START`

- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`agoat2_s_2[shield][timing]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
- **AssignBuffBlackboard** `_targetType`="TARGET"
- **AssignBuffBlackboard** `_targetType`="TARGET"

---

### 火山回响　`skchr_agoat2_3`

**技能描述（最高级）：**

> 攻击范围扩大至整个战场，治疗变为60%治疗量和元素损伤回复量的5连发，优先治疗不同的目标，第二天赋的效果提升至5倍


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 50 秒 |
| duration / durationType | 50 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@heal_scale` | 0.6 |
| `talent_scale` | 5 |

#### 攻击范围

`rangeId = 3-17`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`agoat2_s_3[end]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`agoat2_s_3[heal_clear]`** ← 事件 `ON_BUFF_START`

- **CreateBuffUseAbilitySelector** buffKey=`agoat2_s_3[healed_clear]` templateKey=`agoat2_s_3[healed_clear]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"

**`agoat2_s_3[healed_clear]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`agoat2_s_3[switch]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
- **CreateBuffUseAbilitySelector** buffKey=`agoat2_s_3[healed_clear]` templateKey=`agoat2_s_3[healed_clear]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"

**`agoat2_s_3[switch]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **CreateBuff** buffKey=`agoat2_s_3[switch][end]` templateKey=`agoat2_s_3[switch][end]` `lifeTimeType`=LIMITED

**`agoat2_s_3[switch][end]`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["agoat2_s_3[end]"] `_targetType`="BUFF_OWNER"
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
