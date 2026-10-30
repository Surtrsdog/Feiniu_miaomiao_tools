# 夜半 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_476_blkngt` |
| 职业 | 先锋 / `tactician` |
| 星级 | 5 星 |
| 生命（精二满级） | 1625 |
| 攻击（精二满级） | 442 |
| 防御（精二满级） | 133 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_476_blkngt_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.266667 秒** | 8 帧 |

> 占攻击间隔 26.7%（0.266667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 半醒　`skchr_blkngt_1`

**技能描述（最高级）：**

> 立刻获得11点部署费用，眠兽进入休眠，期间每秒恢复14%最大生命；眠兽受到伤害时醒来，攻击力+55%，攻击速度+55%，持续10秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 17 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 11 |
| `hp_recovery_per_sec_by_max_hp_ratio` | 0.14 |
| `blkngt_hypnos_s_1[rage].atk` | 0.55 |
| `blkngt_hypnos_s_1[rage].attack_speed` | 0.55 |
| `blkngt_hypnos_s_1[rage].duration` | 10 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`blkngt_s_1`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckFirstRallyPointMode** 
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

### 安眠　`skchr_blkngt_2`

**技能描述（最高级）：**

> 立即使战术点周围的所有地面敌人陷入6秒沉睡并获得4点部署费用；6秒内眠兽的攻击变为群体法术攻击，攻击沉睡的目标时攻击力提升至210%
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `blkngt_s_2.atk_scale` | 2.1 |
| `cost` | 4 |
| `blkngt_s_2.duration` | 6 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`blkngt_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **IfElse** 
  - **CheckFirstRallyPointMode** 
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
