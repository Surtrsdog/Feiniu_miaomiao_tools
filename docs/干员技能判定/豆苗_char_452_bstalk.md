# 豆苗 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_452_bstalk` |
| 职业 | 先锋 / `tactician` |
| 星级 | 4 星 |
| 生命（精二满级） | 1569 |
| 攻击（精二满级） | 405 |
| 防御（精二满级） | 125 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_452_bstalk_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.266667 秒** | 8 帧 |

> 占攻击间隔 26.7%（0.266667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill01` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill02` | 0.6 秒 | 18 帧 |


## 三、技能逐层拆解

---

### 定点指令　`skchr_bstalk_1`

**技能描述（最高级）：**

> 立即获得8点部署费用，并立刻刷新援军（如已存在则恢复其所有生命值）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 8 |

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

**`bstalk_s_1`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckFirstRallyPointMode** 
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
  - **HealToken** 

---

### “大家一起上”　`skchr_bstalk_2`

**技能描述（最高级）：**

> 立即在战术点周围四格的所有近战位临时召唤磐蟹（不包括战术点本身）；技能持续时间内回复总共12点部署费用，所有磐蟹的防御力+70%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `value` | 12 |
| `attack@def` | 0.7 |
| `attack@atk` | 0 |
| `interval` | 1.25 |
| `cost` | 1 |

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

**`bstalk_s_2[def_up]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["bstalk_s_2[def_up][override]"] `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`bstalk_s_2[def_up][override]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`bstalk_s_2[finish]`** ← 事件 `ON_BUFF_FINISH`

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
