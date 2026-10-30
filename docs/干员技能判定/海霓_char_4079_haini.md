# 海霓 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4079_haini` |
| 职业 | 辅助 / `underminer` |
| 星级 | 5 星 |
| 生命（精二满级） | 1625 |
| 攻击（精二满级） | 440 |
| 防御（精二满级） | 103 |
| 法抗 | 2500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4079_haini_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 33.3%（0.533333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Loop` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 迷惑性洋流图　`skchr_haini_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至200%，并同时攻击4个敌人


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |
| `max_target` | 4 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 阻滞性显色剂　`skchr_haini_2`

**技能描述（最高级）：**

> 攻击力+50%，额外攻击一个目标，攻击范围内的非精英和领袖敌人移动速度-60%，且被击倒时使天赋效果提升0.5倍，最多提升至3倍，持续至技能结束


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack@move_speed` | -0.6 |
| `attack@talent_up` | 0.5 |
| `attack@max_talent_up` | 3 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`haini_s_2[enemy_killed]`** ← 事件 `ON_OWNER_KILLED`

- **TriggerBuffsByKeys** `_buffKeys`=["haini_s_2[modify_talent]"] `_targetType`="BUFF_SOURCE"

**`haini_s_2[modify_t_buff_bb]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **TriggerBuffsByKeys** `_buffKeys`=["haini_t_1"] `_targetType`="BUFF_OWNER"

**`haini_s_2[modify_talent]`** ← 事件 `ON_BUFF_TRIGGER`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **ModifyAbilityBlackboard** 
  - **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`haini_s_2[full_effect]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`haini_s_2[full_effect2]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- …（共 25 个节点，已截断）

**`haini_s_2[modify_talent]`** ← 事件 `ON_BUFF_FINISH`

- **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- **ModifyAbilityBlackboard** 
- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

**`haini_s_2[recover_t_buff_bb]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **TriggerBuffsByKeys** `_buffKeys`=["haini_t_1"] `_targetType`="BUFF_OWNER"

**`haini_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`haini_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

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
