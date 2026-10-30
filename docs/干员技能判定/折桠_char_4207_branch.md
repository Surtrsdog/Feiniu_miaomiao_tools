# 折桠 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4207_branch` |
| 职业 | 重装 / `unyield` |
| 星级 | 5 星 |
| 生命（精二满级） | 3748 |
| 攻击（精二满级） | 865 |
| 防御（精二满级） | 540 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 35 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4207_branch_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.733333 秒** | 22 帧 |

> 占攻击间隔 45.8%（0.733333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Begin` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2_Loop` | 0.8 秒 | 24 帧 |


## 三、技能逐层拆解

---

### 绝境抵抗　`skchr_branch_1`

**技能描述（最高级）：**

> 防御力+120%，获得抵抗


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 10 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 1.2 |
| `one_minus_status_resistance` | -0.5 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`branch_s_1`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`status_resistance[inf]` `lifeTimeType`=LIMITED

---

### 生存决心　`skchr_branch_2`

**技能描述（最高级）：**

> 技能开启时使自身周围的地面敌人战栗5秒；攻击力+150%，防御力+50%，同时攻击阻挡的所有敌人


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `not_combat` | 5 |
| `def` | 0.5 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`branch_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`branch_s_2[first]` `lifeTimeType`=INFINITY
- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

**`branch_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
