# 玛露西尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4141_marcil` |
| 职业 | 术师 / `splashcaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1805 |
| 攻击（精二满级） | 914 |
| 防御（精二满级） | 130 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **2.9 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 34 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.9 ÷ 1.00 = 2.900 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4141_marcil_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 17.2%（0.5 秒 / 2.9 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop_A` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2_Loop_B` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Attack` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 才女的实力　`skchr_marcil_1`

**技能描述（最高级）：**

> 短暂吟唱后开启技能，每次攻击消耗2点魔力，攻击力+140%，在找不到攻击目标时改为治疗友方干员
> 技能可随时主动关闭


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 80 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `chant_duration` | 1.5 |
| `skill_cost_min_sp` | 2 |
| `mana_init` | 25 |
| `atk` | 1.4 |
| `sp_cost` | 2 |
| `mana_max` | 80 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`marcil_s_1`** ← 事件 `ON_OUTPUT_ATK_OR_HEAL`

- **ModifySp** `_targetType`="TARGET" `_forceFlag`=True
- **TriggerBuffsByKeys** `_buffKeys`=["marcil_t"] `_targetType`="BUFF_OWNER"

**`marcil_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`marcil_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`marcil_s_1`** ← 事件 `ON_AFTER_ATTACK`

- **CheckHasSp** `_condType`="LT"
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`marcil_s_1`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckHasSp** `_condType`="LT"
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

---

### 召唤使魔　`skchr_marcil_2`

**技能描述（最高级）：**

> 吟唱11秒后，消耗35点魔力制作并使用使魔攻击，攻击力+100%，攻击使所有命中目标停顿0.5秒
> 第二次使用时使魔升级，攻击距离+1，攻击速度+60，攻击晕眩主目标0.5秒
> 技能持续时间无限，第一次使用可随时停止


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 80 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `chant_duration` | 11 |
| `skill_cost_min_sp` | 35 |
| `mana_init` | 10 |
| `atk` | 1 |
| `attack@sluggish` | 0.5 |
| `attack_speed` | 60 |
| `attack@stun` | 0.5 |
| `sp_cost` | 35 |
| `mana_max` | 80 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`marcil_s_2`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **ModifySp** `_targetType`="TARGET" `_forceFlag`=True
- **TriggerBuffsByKeys** `_buffKeys`=["marcil_t"] `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["marcil_s2_enhance"] `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **CreateBuff** buffKey=`marcil_s2_enhance[buff]` 属性修改=[ATK MULTIPLIER blackboard, ATTACK_SPEED ADDITION blackboard] `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`marcil_s2_enhance` templateKey=`marcil_s2_enhance` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **CreateBuff** buffKey=`marcil_s2[buff]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY

**`marcil_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 爆破魔法　`skchr_marcil_3`

**技能描述（最高级）：**

> 吟唱5秒后，消耗8点魔力，在正前方位置造成爆炸，对周围敌人造成390%攻击力的法术伤害，炸到的高台会崩开碎片晕眩其周围敌人4秒
> 可追加吟唱10秒，完成后消耗剩余所有魔力，每额外消耗8点魔力，追加1次爆炸
> 追加吟唱可随时停止


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 80 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `chant_duration` | 5 |
| `extra_chant_duration` | 10 |
| `skill_cost_min_sp` | 8 |
| `mana_max` | 80 |
| `mana_init` | 40 |
| `sp_cost_extra` | 8 |
| `atk_scale` | 3.9 |
| `interval` | 0.45 |
| `stun` | 4 |
| `trig_cnt` | 49 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`marcil_s_3[boom]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **ModifySp** `_targetType`="TARGET" `_forceFlag`=True
- **CheckContainsBuff** `_buffKeys`=["marcil_3_extra_chant"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **AssignValueToBB** 
- **FinishBuff** 

**`marcil_s_3[boom]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckHasSp** `_condType`="GE"
  - **TriggerAbility** `_targetType`="BUFF_OWNER"
  - **ModifySp** `_targetType`="TARGET" `_forceFlag`=True
  - **IfElse** 
    - **CheckTriggerable** 
    - **CheckHasSp** `_condType`="GE"
    - **IfNot** 
    - **FinishBuff** 
    - **FinishBuff** 
  - **FinishBuff** 

**`marcil_s_3[boom]`** ← 事件 `ON_SKILL_FINISH`

- **InterruptAbility** 

**`marcil_s_3[boom]`** ← 事件 `ON_BUFF_FINISH`

- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"
- **InterruptAbility** 
- **IsBlackboardZero** 
- **ModifyAbilityAttackTime** 
- **CreateBuff** buffKey=`marcil_s_3[boom][finish]` templateKey=`marcil_s_3[boom][finish]` `lifeTimeType`=LIMITED

**`marcil_s_3[boom][finish]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
