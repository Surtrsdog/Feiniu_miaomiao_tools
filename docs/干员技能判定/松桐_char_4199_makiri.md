# 松桐 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4199_makiri` |
| 职业 | 先锋 / `counsellor` |
| 星级 | 5 星 |
| 生命（精二满级） | 2002 |
| 攻击（精二满级） | 600 |
| 防御（精二满级） | 400 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4199_makiri_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 38.9%（0.466667 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_Loop` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 入场安排　`skchr_makiri_1`

**技能描述（最高级）：**

> 立即获得10点部署费用，并使当前待部署区最右边的1名干员部署费用-4


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 10 |
| `cnt` | 1 |
| `value` | -4 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`makiri_s_1`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CreateCardBuffByDeckSequenceOrder** `_count`=0

---

### 万手成局　`skchr_makiri_2`

**技能描述（最高级）：**

> 逐渐回复总共15点部署费用，攻击力+70%，每秒恢复10%的最大生命值；技能开启时立即使待部署区所有重装与辅助干员费用-1，并且最大生命值+15%（生命加成最多叠加2次，持续至下次撤退）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 1 |
| `max_hp` | 0.15 |
| `makiri_s_2[passive].hp_recovery_per_sec_by_max_hp_ratio` | 0.1 |
| `makiri_s_2[passive].atk` | 0.7 |
| `max_stack_cnt` | 2 |
| `cost_decrease` | -1 |
| `interval` | 1 |
| `value` | 15 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`makiri_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"
- **EnsureBlackboardDefaultValue** 
- **CalculateBlackboardValueViaParams** 
- **AlwaysNext** 
- **CreateCardBuffWithDeckSelector** `_source`="BUFF_OWNER"
- **CreateDeckBuffWithDeckSelector** 

**`makiri_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
