# 予愿安洁莉娜 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1015_aglna2` |
| 职业 | 特种 / `skywalker` |
| 星级 | 6 星 |
| 生命（精二满级） | 2385 |
| 攻击（精二满级） | 796 |
| 防御（精二满级） | 520 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 18 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1015_aglna2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 26.7%（0.4 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Combat` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 极速送达　`skchr_aglna2_1`

**技能描述（最高级）：**

> 部署后立刻起飞，攻击范围扩大，攻击力+135%，同时攻击两个目标


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 60 秒 |
| duration / durationType | 60 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.35 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`aglna2_s_1[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=6 `_targetType`="TARGET"

---

### 重力自定义　`skchr_aglna2_2`

**技能描述（最高级）：**

> 攻击范围扩大并向前方滑翔起飞，使掠过的攻击范围内的地面敌人浮空12秒、飞行敌人缚地22秒，随后攻击间隔较大幅缩短，攻击力+165%，攻击变为法术伤害且同时攻击5个目标


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 21 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 22 秒 |
| duration / durationType | 22 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.65 |
| `base_attack_time` | -0.8 |
| `attack@max_target` | 5 |
| `chant_duration` | 2.5 |
| `mass_level` | 10 |
| `buff_duration_ground_bound` | 22 |
| `buff_duration_levitate` | 12 |

#### 攻击范围

`rangeId = 3-10`，15 格（direction=1）

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`aglna2_s_2[chant_end]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **AlwaysExecuteNodeList** 
  - **IfElse** 
    - **CheckBlackboardContainsKey** 
    - **AssignBuffBlackboardFromOthers** `_targetType`="TARGET"
  - **AlwaysNext** 
  - **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"

**`aglna2_s_2[chant_end]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`aglna2_s_2[enemy]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CalculateBlackboardValueViaParams** 
- **IfElse** 
  - **CheckMotionMode** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`aglna2_s_2[enemy][ground_bound]` `lifeTimeType`=LIMITED
  - **CreateBuff** buffKey=`aglna2_s_2[enemy][levitate]` `lifeTimeType`=LIMITED

**`aglna2_s_2[fly]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`aglna2_s_2` `lifeTimeType`=INFINITY
- **SwitchMode** `_modeIndex`=10 `_targetType`="BUFF_OWNER"
- **SetCastSkillManualTriggerOnly** `_targetType`="BUFF_OWNER"

**`aglna2_s_2[fly]`** ← 事件 `ON_BUFF_FINISH`

- **SetCastSkillManualTriggerOnly** `_targetType`="BUFF_OWNER"
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`aglna2_s_2[flying]`** ← 事件 `ON_BUFF_START`

- **AlwaysExecuteNodeList** 
  - **SwitchDirection** `_source`="BUFF_OWNER"
    - **CreateBuff** buffKey=`aglna2_s_2[flying][eff]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`aglna2_s_2[flying][eff]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`aglna2_s_2[flying][eff]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`aglna2_s_2[flying][eff]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`aglna2_s_2[flying][eff_ground]` `lifeTimeType`=INFINITY

**`aglna2_s_2[mode]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckUnitAlive** 
  - **SwitchMode** `_modeIndex`=7 `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 酸橙的心事　`skchr_aglna2_3`

**技能描述（最高级）：**

> 立刻起飞，攻击力+30%，获得65%的对空庇护，攻击范围扩大，且周围8格视作予愿安洁莉娜的额外攻击范围，攻击对3个敌人造成攻击力380%的物理伤害且额外攻击1个飞行敌人；范围内飞行敌人移动速度-60%，原技能范围内有未被阻挡的可阻挡飞行敌人，且自身未阻挡时，移动至该敌人所在格
> 攻击装有33发弹药，打完后技能结束（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 24 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 3.8 |
| `attack@max_target` | 4 |
| `move_speed` | -0.6 |
| `aglna2_s_3[unblocked].attack_speed` | 0 |
| `aglna2_s_3[blocked].attack_speed` | 0 |
| `atk` | 0.3 |
| `damage_resistance` | 0.65 |
| `attack@attack_range_id` | 0 |
| `attack@max_walk_target` | 3 |
| `attack@trigger_time` | 33 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`aglna2_s_3[damage_reduce]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfConditions** 
  - **CheckMotionMode** `_targetType`="MODIFIER_SOURCE"
  - **CheckMotionMode** `_targetType`="PROJECTILE_SOURCE"
  - **IfConditions** 
    - **FilterDamageModifer** `_source`="BUFF_OWNER"
    - **FilterDamageModifer** `_source`="BUFF_OWNER"
    - **DamageScale** 

**`aglna2_s_3[mode]`** ← 事件 `ON_BUFF_START`

- **AlwaysExecuteNodeList** 
  - **IfElse** 
    - **FilterByCharacterSharedBlackboard** `_condType`="GT" `_target`="BUFF_OWNER"
    - **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckHeightTypeOfRootTile** `_targetType`="BUFF_OWNER"
      - **EnsureBlackboardDefaultValue** 
      - **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"
      - **EnsureBlackboardDefaultValue** 
      - **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"
    - **SwitchMode** `_modeIndex`=8 `_targetType`="BUFF_OWNER"
    - **AssignCharacterSkillRangeToBlackboard** `_targetType`="BUFF_OWNER"
    - **EmitProjectile** `_targetType`="TARGET"
  - **AlwaysNext** 
  - **ForceHideSkillRangeToShow** `_target`="BUFF_OWNER"
  - **TriggerAbility** `_targetType`="BUFF_OWNER"
- …（共 18 个节点，已截断）

**`aglna2_s_3[mode]`** ← 事件 `ON_BUFF_FINISH`

- **AlwaysExecuteNodeList** 
  - **SwitchMode** `_modeIndex`=9 `_targetType`="BUFF_OWNER"
  - **InterruptAbility** 
- **AlwaysNext** 
- **ForceHideSkillRangeToShow** `_target`="BUFF_OWNER"

**`aglna2_s_3[mode]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckFaceLOrR** `_target`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_l]"
      - **FinishDerivedBuffById** 
    - **AlwaysNext** 
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_r]"
      - **CreateBuff** buffKey=`aglna2_s_3[move_eff_r]` `lifeTimeType`=INFINITY
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_r]"
      - **FinishDerivedBuffById** 
    - **AlwaysNext** 
    - **IfElse** 
- …（共 20 个节点，已截断）

**`aglna2_s_3[move_mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

**`aglna2_s_3[move_mode]`** ← 事件 `ON_BUFF_FINISH`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"

**`aglna2_s_3[move_mode]`** ← 事件 `ON_BUFF_TRIGGER`

- **AlwaysExecuteNodeList** 
  - **IfElse** 
    - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
    - **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckFaceLOrR** `_target`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_l]"
      - **FinishDerivedBuffById** 
    - **AlwaysNext** 
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_r]"
      - **CreateBuff** buffKey=`aglna2_s_3[move_eff_r]` `lifeTimeType`=INFINITY
    - **IfElse** 
      - **CheckContainsDerviedBuff** `_derviedBuffKey`="aglna2_s_3[move_eff_r]"
      - **FinishDerivedBuffById** 
- …（共 20 个节点，已截断）

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
