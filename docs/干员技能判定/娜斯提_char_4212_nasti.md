# 娜斯提 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4212_nasti` |
| 职业 | 辅助 / `craftsman` |
| 星级 | 6 星 |
| 生命（精二满级） | 2585 |
| 攻击（精二满级） | 614 |
| 防御（精二满级） | 446 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 19 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4212_nasti_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 28.9%（0.433333 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.8 秒 | 24 帧 |
| 技能动画 | `Skill_3_Begin` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### “拱卫”　`skchr_nasti_1`

**技能描述（最高级）：**

> 携带此技能时：装置使前方干员防御力提升
> 攻击力+80%，防御力+80%，同时攻击阻挡的所有敌人；装置效果改为使前方干员阻挡数+1，防御力+55%，装置每秒流失2%最大生命值
> 技能开启时获得一个装置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 28 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `talent@def` | 0.55 |
| `atk` | 0.8 |
| `def` | 0.8 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nasti_s1[audio_1]`** ← 事件 `ON_BUFF_FINISH`

- **PlayAudio** `_target`="BUFF_OWNER"

**`nasti_s1[effect_manager]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`nasti_s1[effect_2]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`nasti_s1[effect_3]` `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`nasti_s1[effect_manager]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuff** buffKey=`nasti_s1[effect]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

### “执行”　`skchr_nasti_2`

**技能描述（最高级）：**

> 携带此技能时：装置部署后逐渐回复自身生命值，激活后每0.5秒流失1点生命值，使前方干员获得1点技力和相当于娜斯提生命上限5%的屏障
> 立即激活场上装置，停止攻击，每0.5秒获得相当于生命上限10%的屏障（最多不超过生命上限80%）
> 技能结束时获得一个装置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 23 / 28 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 4 秒 |
| duration / durationType | 4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@nasti_s2[update_shield].interval` | 0.5 |
| `attack@nasti_s2[update_shield].shield_each_hp_rate` | 0.1 |
| `attack@nasti_s2[update_shield].shield_max_hp_rate` | 0.8 |
| `talent@shield_max_hp_rate` | 0.8 |
| `talent@shield_each_hp_rate` | 0.05 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nasti_s2[finish_shield]`** ← 事件 `ON_OWNER_FINISH`

- **FinishBuffsOfEveryCharacterById** 

**`nasti_s2[shield_core]`** ← 事件 `ON_BUFF_TRIGGER`

- **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
- **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`nasti_s2[shield_effect]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`nasti_s2[shield_core]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`nasti_s2[shield_core]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 

**`nasti_s2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`nasti_s2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **AlwaysNext** 
- **RechargeToken** 

**`nasti_s2[switch_token_core]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`nasti_s2[switch_token_core]`** ← 事件 `ON_BUFF_FINISH`

- **InstantKill** `_targetType`="BUFF_OWNER"

**`nasti_s2[token_mode]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`nasti_s2[update_shield]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["nasti_s2[shield_core]"] `_targetType`="BUFF_OWNER"
  - **TriggerBuffsByKeys** `_buffKeys`=["nasti_s2[shield_core]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`nasti_s2[shield_core]` templateKey=`nasti_s2[shield_core]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`nasti_s2[update_shield]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["nasti_s2[shield_core]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`nasti_s2[shield_core]` templateKey=`nasti_s2[shield_core]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

### 栖脚地　`skchr_nasti_3`

**技能描述（最高级）：**

> 携带此技能时：装置可建造并升级一个可以放置远程干员并为其提供增益的特殊高台
> 攻击力+160%，防御力+160%；小工程师装置为高台装置回复技力和生命的效果翻倍
> 技能开启时获得一个装置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 17 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.6 |
| `def` | 1.6 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nasti_s3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`nasti_s3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`nasti_s3[tile_buff]`** ← 事件 `ON_OWNER_LOCATE`

- **IsBlackboardEqualWithFloat** 
- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=False
- **BlackboardAdd** 

**`nasti_s3[tile_buff]`** ← 事件 `ON_BUFF_START`

- **BlackboardAdd** 
- **CheckUnitAlive** 
- **IsBlackboardEqualWithFloat** 
- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=False
- **BlackboardAdd** 

**`nasti_s3[token_mode]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`nasti_s3[token_mode]`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`nasti_s3[trigger_token_skill]`** ← 事件 `ON_BUFF_START`

- **TriggerTokenSkill** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
