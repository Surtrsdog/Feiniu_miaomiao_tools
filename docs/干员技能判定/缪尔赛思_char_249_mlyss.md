# 缪尔赛思 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_249_mlyss` |
| 职业 | 先锋 / `tactician` |
| 星级 | 6 星 |
| 生命（精二满级） | 1813 |
| 攻击（精二满级） | 497 |
| 防御（精二满级） | 117 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 15 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_249_mlyss_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 40.0%（0.4 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_2_Loop` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_3_loop` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 渐进性润化　`skchr_mlyss_1`

**技能描述（最高级）：**

> 期间逐渐回复13点费用，自身与流形攻击力+50%，攻击速度+50


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 28 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `mlyss_s_1[cost].cost` | 1 |
| `mlyss_s_1[cost].interval` | 1.154 |
| `atk` | 0.5 |
| `attack_speed` | 50 |
| `fake_cost` | 13 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`mlyss_s_1[buff]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_1[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuff** buffKey=`mlyss_s_1[token_holder]` templateKey=`mlyss_s_1[token_holder]` `lifeTimeType`=IMMEDIATELY
- **CreateBuff** buffKey=`mlyss_wtrman_s_1[effect_trigger]` templateKey=`mlyss_wtrman_s_1[effect_trigger]` `lifeTimeType`=IMMEDIATELY

**`mlyss_s_1[buff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_1[token_holder]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["mlyss_s_1[token_buff]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlyss_s_1[token_buff]` 属性修改=[ATK MULTIPLIER blackboard, ATTACK_SPEED ADDITION blackboard] `lifeTimeType`=INFINITY
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

---

### 生态耦合　`skchr_mlyss_2`

**技能描述（最高级）：**

> 立即获得15点费用，自身与流形攻击力+50%，若流形为近战复制体时，每秒回复5%的生命值，获得25%的庇护，若为远程复制体时，攻击变为二连击，随机攻击范围内的目标


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 15 |
| `atk` | 0.5 |
| `damage_resistance` | 0.25 |
| `hp_recovery_per_sec_by_max_hp_ratio` | 0.05 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mlyss_s_2[buff]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_2[buff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_2[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuff** buffKey=`mlyss_s_2[token_holder]` templateKey=`mlyss_s_2[token_holder]` `lifeTimeType`=IMMEDIATELY
- **CreateBuff** buffKey=`mlyss_s_2[token_melee_holder]` templateKey=`mlyss_s_2[token_melee_holder]` `lifeTimeType`=IMMEDIATELY
- **CreateBuff** buffKey=`mlyss_s_2[token_range_holder]` templateKey=`mlyss_s_2[token_range_holder]` `lifeTimeType`=IMMEDIATELY
- **CreateBuff** buffKey=`mlyss_wtrman_s_2[effect_trigger]` templateKey=`mlyss_wtrman_s_2[effect_trigger]` `lifeTimeType`=IMMEDIATELY

**`mlyss_s_2[token_buff_melee]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 

**`mlyss_s_2[token_buff_range_finish]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`mlyss_s_2[token_holder]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["mlyss_s_2[token_buff]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlyss_s_2[token_buff]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`mlyss_s_2[token_melee_holder]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **CheckContainsBuff** `_buffKeys`=["mlyss_s_2[token_buff_melee]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlyss_s_2[token_buff_melee]` templateKey=`mlyss_s_2[token_buff_melee]` 属性修改=[HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO ADDITION blackboard] `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`mlyss_s_2[token_range_holder]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`mlyss_s_2[token_buff_range]` templateKey=`switch_mode_no_restore` `lifeTimeType`=IMMEDIATELY
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 浅层非熵适应　`skchr_mlyss_3`

**技能描述（最高级）：**

> 立即获得15点费用，自身与流形攻击力+50%，若流形为近战复制体时每2秒对周围八格敌人向自己中心小力度地拖拽并使所有阻挡的单位持续晕眩，若为远程复制体时刷新所有流形且攻击附带持续1.5秒的束缚


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 15 |
| `atk` | 0.5 |
| `mlyss_s_3[token_melee_trigger].interval` | 2 |
| `mlyss_s_3[unmoveable].duration` | 1.5 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`mlyss_s_3[buff]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_3[buff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **FinishTokenBuffsById** 
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlyss_s_3[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuff** buffKey=`mlyss_s_3[token_holder]` templateKey=`mlyss_s_3[token_holder]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`mlyss_s_3[token_melee_holder]` templateKey=`mlyss_s_3[token_melee_holder]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`mlyss_s_3[token_range_holder]` templateKey=`mlyss_s_3[token_range_holder]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`mlyss_wtrman_s_3[effect_trigger]` templateKey=`mlyss_wtrman_s_3[effect_trigger]` `lifeTimeType`=INFINITY

**`mlyss_s_3[buff_refresh]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuff** buffKey=`mlyss_s_3[token_buff]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`mlyss_s_3[token_buff_range]` templateKey=`mlyss_s_3[token_buff_range]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`mlyss_wtrman_s_3[effect]` `lifeTimeType`=INFINITY

**`mlyss_s_3[token_buff_melee_finish]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`mlyss_s_3[token_buff_range]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **FilterAbilityFamily** 
- **CreateBuff** buffKey=`mlyss_s_3[unmoveable]` `lifeTimeType`=LIMITED

**`mlyss_s_3[token_holder]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["mlyss_s_3[token_buff]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlyss_s_3[token_buff]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`mlyss_s_3[token_melee_holder]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`mlyss_s_3[token_buff_melee]` templateKey=`switch_mode_no_restore` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`mlyss_s_3[token_melee_trigger]` templateKey=`mlyss_s_3[token_melee_trigger]` `lifeTimeType`=INFINITY
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`mlyss_s_3[token_melee_trigger]` templateKey=`mlyss_s_3[token_melee_trigger]` `lifeTimeType`=INFINITY
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`mlyss_s_3[token_melee_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`mlyss_s_3[token_range_holder]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **CheckContainsBuff** `_buffKeys`=["mlyss_s_3[token_buff_range]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlyss_s_3[token_buff_range]` templateKey=`mlyss_s_3[token_buff_range]` `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`mlyss_s_3[token_range_trigger]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["mlyss_wtrman_summon[override]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckContainsBuff** `_buffKeys`=["mlyss_wtrman_range[mark]"] `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`mlyss_s_3[token_range_audio]` `lifeTimeType`=IMMEDIATELY
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
