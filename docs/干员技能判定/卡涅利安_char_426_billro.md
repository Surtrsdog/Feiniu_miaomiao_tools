# 卡涅利安 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_426_billro` |
| 职业 | 术师 / `phalanx` |
| 星级 | 6 星 |
| 生命（精二满级） | 2106 |
| 攻击（精二满级） | 846 |
| 防御（精二满级） | 228 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2 ÷ 1.00 = 2.000 秒
```

## 二、抬手（攻击前摇）

⚠️ 本干员在 `bakemuzzledata` 中**没有 `OnAttack` 事件**，无法从明文数据得出抬手数值。

原始状态标记：`SKILL_ONLY`

该干员只有技能动画（无普攻动画），属于 `skill_only` / `no_attack` 类，抬手需实测。

## 三、技能逐层拆解

---

### 沙暴守卫　`skchr_billro_1`

**技能描述（最高级）：**

> 攻击力+60%，防御力+100%；
> 蓄力额外效果：特性效果在技能期间继续生效


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `def` | 1 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`billro_s_1`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"

**`billro_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`billro_s_1[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_1[eff_cond][full]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_1[eff_cond][full]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_1[eff_cond][half]` `lifeTimeType`=INFINITY
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_1[eff_cond][half]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_1[eff_cond][half]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=2 `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_1[eff_cond][full]"
- …（共 27 个节点，已截断）

---

### 沙缚镣锁　`skchr_billro_2`

**技能描述（最高级）：**

> 攻击间隔大幅度缩短，每次攻击对目标造成0.3秒停顿；
> 蓄力额外效果：攻击力+20%且停顿变为束缚0.6秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -1.1 |
| `attack@sluggish` | 0.3 |
| `atk` | 0.2 |
| `attack@root` | 0.6 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`billro_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`billro_s_2_derived[enhance]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"

**`billro_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`billro_s_2[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_2[eff_cond][full]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_2[eff_cond][full]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_2[eff_cond][half]` `lifeTimeType`=INFINITY
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_2[eff_cond][half]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_2[eff_cond][half]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=2 `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_2[eff_cond][full]"
- …（共 27 个节点，已截断）

---

### 食噬之印　`skchr_billro_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力逐渐增至+280%
> 蓄力额外效果：每次攻击使目标受到来自卡涅利安的伤害提升20%（最多叠加5次），持续至技能结束


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 28 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 21 秒 |
| duration / durationType | 21 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.8 |
| `attack@damage_scale` | 0.2 |

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

**`billro_s_3`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=6 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=5 `_targetType`="TARGET"
  - **TriggerAbilityUseSelector** `_targetType`="TARGET"

**`billro_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`billro_s_3[atk]`** ← 事件 `ON_BUFF_TRIGGER`

- **RemainingRatioToAttributeModifier** 

**`billro_s_3[charge][enhance]`** ← 事件 `ON_TAKE_DAMAGE`

- **CheckEntityEquals** 
- **CheckContainsBuff** `_buffKeys`=["billro_s_3[mark_effect]"] `_targetType`="BUFF_OWNER"
- **DamageScale** 

**`billro_s_3[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["billro_talent_enhance_mark"] `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_3[eff_cond][full2]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][full]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][half]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][full2]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][half2]` `lifeTimeType`=INFINITY
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="billro_s_3[eff_cond][half]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][half]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`billro_s_3[eff_cond][half2]` `lifeTimeType`=INFINITY
- …（共 30 个节点，已截断）

**`billro_s_3[mark_effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByBuffStackCount** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["billro_s_3[mark_effect][full]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`billro_s_3[mark_effect][full]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **FilterByBuffStackCount** `_condType`="GE" `_targetType`="BUFF_OWNER"
    - **CheckContainsBuff** `_buffKeys`=["billro_s_3[mark_effect][part]"] `_targetType`="BUFF_OWNER"
    - **IfNot** 
    - **CreateBuff** buffKey=`billro_s_3[mark_effect][part]` `lifeTimeType`=INFINITY
    - **FinishDerivedBuff** 

**`billro_s_3[mark_effect]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
