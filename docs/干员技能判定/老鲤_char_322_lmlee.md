# 老鲤 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_322_lmlee` |
| 职业 | 特种 / `merchant` |
| 星级 | 6 星 |
| 生命（精二满级） | 2427 |
| 攻击（精二满级） | 789 |
| 防御（精二满级） | 465 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 9 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_322_lmlee_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 46.7%（0.466667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_Start` | 0.2 秒 | 6 帧 |
| 技能动画 | `Skill_3_Loop` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 小惩大诫　`skchr_lmlee_1`

**技能描述（最高级）：**

> 攻击力+60%，并获得40%的法术闪避
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `prob` | 0.4 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 驱凶辟邪　`skchr_lmlee_2`

**技能描述（最高级）：**

> 被动效果：攻击速度+30；主动开启：标记目标使其更易受我方攻击，5秒后标记爆炸对周围造成300%的法术伤害。期间我方每对目标造成一次伤害，爆炸伤害增加老鲤攻击力的20%（最多增加30次，达到上限或目标被击倒时提前爆炸）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `default_atk_scale` | 3 |
| `factor_atk_scale` | 0.2 |
| `max_stack_cnt` | 30 |
| `taunt_level` | 1 |
| `paper_duration` | 5 |
| `attack_speed` | 30 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lmlee_s_2`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`lmlee_s_2[end]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuffToCertainSideUnits** buffKey=`lmlee_s_2[remove]` templateKey=`lmlee_s_2[remove]` `lifeTimeType`=IMMEDIATELY

**`lmlee_s_2[paper]`** ← 事件 `ON_TAKE_DAMAGE`

- **CreateBuff** buffKey=`lmlee_s_2[count]` `overrideType`=STACK `lifeTimeType`=INFINITY
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`lmlee_s_2[paper]`** ← 事件 `ON_BUFF_FINISH`

- **ResetBuffAbilityAtkScaleWithBuffCnt** `_targetType`="BUFF_OWNER"
- **EmitProjectile** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`lmlee_s_2[paper]`** ← 事件 `ON_BUFF_TRIGGER`

- **FilterByBuffStackCount** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`lmlee_s_2[remove]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 贵客盈门　`skchr_lmlee_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力和防御力+50%；攻击小力度推开范围内除当前目标外的敌人。自身容易成为攻击目标，且有70%概率闪避来自范围外的物理或法术伤害
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `def` | 0.5 |
| `taunt_level` | 1 |
| `prob` | 0.7 |
| `attack@prob_knockback` | 1 |
| `attack@force` | 0 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lmlee_s_3[atk]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`lmlee_s_3[starteff]` `lifeTimeType`=INFINITY

**`lmlee_s_3[evade]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfElse** 
  - **CheckTargetInRange** `_targetType`="MODIFIER_SOURCE"
  - **Evade** 

**`lmlee_s_3[knockback]`** ← 事件 `ON_BUFF_START`

- **Dice** 
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`lmlee_skill_3_audio[knockback]` `lifeTimeType`=LIMITED
- **CreateBuffInRange** `_targetType`="TARGET" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=E_NUM)

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
