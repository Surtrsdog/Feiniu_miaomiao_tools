# 酒神 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1042_phatm2` |
| 职业 | 辅助 / `ritualist` |
| 星级 | 6 星 |
| 生命（精二满级） | 1200 |
| 攻击（精二满级） | 490 |
| 防御（精二满级） | 104 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1042_phatm2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Loop_1` | 0.9 秒 | 27 帧 |
| 技能动画 | `Skill_2_Loop_2` | 0.9 秒 | 27 帧 |
| 技能动画 | `Skill_3_Loop` | 0 秒 | 0 帧 |


## 三、技能逐层拆解

---

### 暗夜回声　`skchr_phatm2_1`

**技能描述（最高级）：**

> 下次攻击造成两次相当于攻击力150%的法术伤害并使目标束缚3秒，该次束缚期间目标受到的神经损伤提升至1.8倍，优先攻击未处于爆发期间的敌人


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 2 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.5 |
| `ep_damage_scale` | 1.8 |
| `unmove` | 3 |
| `times` | 2 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`phatm2_s_1[unmove]`** ← 事件 `ON_TAKE_EP_DAMAGE`

- **EpDamageScale** 

---

### 群体性谵妄　`skchr_phatm2_2`

**技能描述（最高级）：**

> 攻击速度+35，第一天赋溅射范围扩大；期间可以使用一个本能的召唤，部署后诱导至多4名进入范围的可达敌人（优先精英或领袖）10秒，首个目标到达后撤退并使周围所有敌人在6秒内停顿、每0.5秒受到酒神攻击力150%的法术伤害和攻击力25%的神经损伤
> 持续时间无限，本能的召唤有独立再部署时间


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.5 |
| `ep_damage_ratio_token` | 0.25 |
| `cnt` | 1 |
| `buff_time` | 6 |
| `sluggish` | 6 |
| `interval_damage` | 0.5 |
| `max_target` | 4 |
| `attack_speed` | 35 |
| `talent@range_radius` | 1.5 |
| `attack@projectile_range` | 0 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`phatm2_s_2`** ← 事件 `ON_BUFF_ENABLE`

- **RechargeToken** 

**`phatm2_s_2`** ← 事件 `ON_BUFF_DISABLE`

- **AssignValueToBB** 
- **RechargeToken** 

**`phatm2_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`phatm2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`phatm2_s_2[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **ApplyFixedElementDamage** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FixedValueDamage** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="BUFF_OWNER"

**`phatm2_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"

**`phatm2_s_2[die]`** ← 事件 `ON_OWNER_FINISH`

- **CharacterHasValidToken** 
- **KillTokens** 

**`phatm2_s_2[die]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 

---

### 空剧场　`skchr_phatm2_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+125%，优先攻击未处于损伤爆发期间的敌人，技能期间酒神造成过神经损伤的敌人每秒受到攻击力10%的神经损伤直至爆发；范围内敌人神经损伤冷却恢复速度+50%，神经损伤爆发时在其地面位置生成/刷新一个迷狂牢笼


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.25 |
| `ep_damage_ratio` | 0.1 |
| `interval` | 1 |
| `phatm2_s_3[token_cooldown].interval` | 30 |
| `talent@ep_break_recover_speed` | 0.5 |

#### 攻击范围

`rangeId = y-8`，23 格（direction=1）

```
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`phatm2_s_3[die]`** ← 事件 `ON_BUFF_FINISH`

- **KillTokens** 

**`phatm2_s_3[die]`** ← 事件 `ON_SKILL_FINISH`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`phatm2_s_3[sanity]`** ← 事件 `ON_AFTER_OUTPUT_ELEMENT_DAMAGE`

- **FilterModifierByRealDelta** `_condType`="LT"
- **FilterElementDamageModifer** 
- **CreateBuff** buffKey=`phatm2_s_3[trigger]` templateKey=`phatm2_s_3[trigger]` `lifeTimeType`=INFINITY

**`phatm2_s_3[sanity]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`phatm2_s_3[token]`** ← 事件 `ON_BEFORE_EP_BREAK_START`

- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **IfElse** 
  - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
  - **CreateBuffToCharacterOnTargetRootTile** `_target`="BUFF_OWNER" `_source`="BUFF_SOURCE"
  - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CheckHeightTypeOfRootTile** `_targetType`="BUFF_OWNER"
  - **SpawnTokenOnTargetTile** `_targetType`="BUFF_OWNER"

**`phatm2_s_3[token][trigger]`** ← 事件 `ON_BUFF_START`

- **FilterId** `_targetType`="BUFF_OWNER"
- **CharSearchBlockeeImmediate** `_targetType`="BUFF_OWNER"

**`phatm2_s_3[token_clear_cooldown]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`phatm2_s_3[token_cooldown]`** ← 事件 `ON_BUFF_TRIGGER`

- **InstantKill** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`phatm2_s_3[trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IsTargetInEPBreakRecovery** `_target`="BUFF_OWNER"
  - **FinishBuff** 
  - **ApplyElementDamage** `_targetType`="TARGET"
  - **IsTargetInEPBreakRecovery** `_target`="BUFF_OWNER"
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
