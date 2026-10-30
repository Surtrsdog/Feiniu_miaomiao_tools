# 哈蒂娅 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_394_hadiya` |
| 职业 | 近卫 / `mercenary` |
| 星级 | 5 星 |
| 生命（精二满级） | 2895 |
| 攻击（精二满级） | 530 |
| 防御（精二满级） | 393 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.25 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 10 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.25 ÷ 1.00 = 1.250 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_394_hadiya_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 42.7%（0.533333 秒 / 1.25 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2_Begin` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2_Loop` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 沙地战术改良　`skchr_hadiya_1`

**技能描述（最高级）：**

> 防御力+100%
> 装备应变：消耗10点部署费用，攻击力+100%，持续到技能结束
> 技力满时可使用装备应变来开启技能


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 13 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 1 |
| `extra.atk` | 1 |
| `retrigger_cost` | 10 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hadiya_s_1[buff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 剑角之锋　`skchr_hadiya_2`

**技能描述（最高级）：**

> 消耗10点部署费用组合剑和杖，攻击范围扩大，攻击力+150%，同时攻击3个目标；
> 技能期间可消耗15点部署费用使用装备应变，延长15秒技能持续时间


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 26 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `attack@max_target` | 3 |
| `cost` | 10 |
| `retrigger_cost` | 15 |
| `extra.duration` | 15 |

#### 攻击范围

`rangeId = 3-2`，4 格（direction=1）

```
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hadiya_s_2[buff]`** ← 事件 `ON_BUFF_START`

- **TriggerBuffsByKeys** `_buffKeys`=["hadiya_t_1"] `_targetType`="BUFF_OWNER"

**`hadiya_s_2[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`hadiya_s_2[buff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`hadiya_s_2[extand_time]`** ← 事件 `ON_BUFF_START`

- **ExtendAbilityCooldown** 

**`hadiya_s_2[extand_time]`** ← 事件 `ON_BUFF_FINISH`

- **UpdateAbilityCoolDown** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
