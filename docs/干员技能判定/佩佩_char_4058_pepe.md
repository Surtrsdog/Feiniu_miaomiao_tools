# 佩佩 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4058_pepe` |
| 职业 | 近卫 / `hammer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2851 |
| 攻击（精二满级） | 1290 |
| 防御（精二满级） | 387 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.8 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.8 ÷ 1.00 = 1.800 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4058_pepe_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.833333 秒** | 25 帧 |

> 占攻击间隔 46.3%（0.833333 秒 / 1.8 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.833333 秒 | 25 帧 |
| 技能动画 | `Skill_2_Loop` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_3_Loop_A` | 1.16667 秒 | 35 帧 |
| 技能动画 | `Skill_3_Loop_B` | 1.16667 秒 | 35 帧 |


## 三、技能逐层拆解

---

### 盖戳！　`skchr_pepe_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力290%的物理伤害，处于异常状态时可以释放技能并清除异常状态
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.9 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`pepe_s_1`** ← 事件 `ON_TAKE_DAMAGE`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["cripple"] `_targetType`="BUFF_OWNER"
  - **FinishBuff** 
  - **SetSharedFlag** 

**`pepe_s_1`** ← 事件 `ON_APPLIED_MODIFIER`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["cripple"] `_targetType`="BUFF_OWNER"
  - **FilterByTargetHp** `_condType`="LE" `_targetType`="MODIFIER_TARGET"
  - **CreateBuff** buffKey=`cripple` templateKey=`cripple` 属性修改=[MOVE_SPEED FINAL_SCALER blackboard, BLOCK_CNT FINAL_SCALER 0.0, HP_RECOVERY_PER_SEC FINAL_SCALER 0.0, HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO FINAL_SCALER 0.0] `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **AlwaysNext** 
- **FinishBuff** 

---

### 阻遏混乱锤　`skchr_pepe_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+90%，攻击速度+80，随机攻击范围内的目标
> 每次使用时，使后续开启技能的攻击速度额外+40，最多叠加2层


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 18 秒 |
| duration / durationType | 18 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.9 |
| `attack_speed` | 80 |
| `attack_speed_extra` | 40 |
| `max_stack_cnt` | 2 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`pepe_s_2[attack_speed]`** ← 事件 `ON_SKILL_START`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **BlackboardAdd** 
    - **BlackboardAdd** 
  - **AlwaysNext** 
  - **CreateBuff** buffKey=`pepe_s_2[attack_speed_extra]` 属性修改=[ATTACK_SPEED ADDITION blackboard] `lifeTimeType`=INFINITY
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`pepe_s_2[effect_3]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
    - **IfElse** 
      - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
      - **CreateBuff** buffKey=`pepe_s_2[effect_1]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
      - **CreateBuff** buffKey=`pepe_s_2[effect_2]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **AssignValueToBB** 

**`pepe_s_2[attack_speed]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 
- **AssignValueToBB** 
- **AssignValueToBB** 

**`pepe_s_2[attack_speed]`** ← 事件 `ON_SKILL_FINISH`

- **FinishDerivedBuff** 

---

### 时光震荡　`skchr_pepe_3`

**技能描述（最高级）：**

> 攻击间隔略微增大，攻击力+240%，攻击使命中的目标晕眩0.8秒，对主目标提升至1.5秒，每次攻击后使溅射范围扩大且攻击力额外+25%，最多叠加4层


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.4 |
| `attack@stun` | 0.8 |
| `attack@atk` | 0.25 |
| `attack@stun_main` | 1.5 |
| `attack@ability_range_forward_extend` | 0.25 |
| `attack@max_stack_cnt` | 4 |
| `base_attack_time` | 0.2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`pepe_s_3[mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`pepe_s_3[mode]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`pepe_s_3[sp]`** ← 事件 `ON_TAKE_DAMAGE`

- **IsIgnoreForSp** 
- **IfNot** 
- **ModifySp** `_targetType`="TARGET" `_forceFlag`=False

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
