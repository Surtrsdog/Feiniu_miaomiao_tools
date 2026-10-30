# 八幡海铃 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4186_tmoris` |
| 职业 | 特种 / `stalker` |
| 星级 | 5 星 |
| 生命（精二满级） | 1729 |
| 攻击（精二满级） | 809 |
| 防御（精二满级） | 331 |
| 法抗 | 3000% |
| **攻击间隔 baseAttackTime** | **3.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 0 |
| 部署费用 | 22 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 3.5 ÷ 1.00 = 3.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4186_tmoris_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 13.3%（0.466667 秒 / 3.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.366667 秒 | 11 帧 |


## 三、技能逐层拆解

---

### 颤栗之弦　`skchr_tmoris_1`

**技能描述（最高级）：**

> 发动一次5连击，对攻击范围内的地面敌人每次造成相当于70%攻击力的法术伤害。
> 其他Ave Mujica成员开启技能时，额外释放一次
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 2.1 秒 |
| duration / durationType | 2.1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 0.7 |
| `times` | 5 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tmoris_s_1[audio]`** ← 事件 `ON_SKILL_START`

- **IsInFever** 
- **IfNot** 
- **PlayAudio** `_target`="BUFF_OWNER"

**`tmoris_s_1[effect]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"

**`tmoris_s_1[fever]`** ← 事件 `ON_SKILL_FINISH`

- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=True

---

### 无存之所　`skchr_tmoris_2`

**技能描述（最高级）：**

> 立即使攻击范围内的敌人恐惧1.5秒，每秒对攻击范围内的敌人造成攻击力100%的法术伤害，第一天赋造成停顿的概率提升至2.2倍


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 1 |
| `attack@interval` | 1 |
| `fear` | 1.5 |
| `talent_scale` | 2.2 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tmoris_s_2[audio]`** ← 事件 `ON_SKILL_START`

- **IsInFever** 
- **IfNot** 
- **IsFeverFull** 
- **IfNot** 
- **PlayAudio** `_target`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
