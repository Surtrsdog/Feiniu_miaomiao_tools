# 凯瑟琳 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4162_cathy` |
| 职业 | 辅助 / `craftsman` |
| 星级 | 5 星 |
| 生命（精二满级） | 2680 |
| 攻击（精二满级） | 550 |
| 防御（精二满级） | 420 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4162_cathy_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 33.3%（0.5 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 岁月锻打　`skchr_cathy_1`

**技能描述（最高级）：**

> 自身和拥有装置屏障的其他干员攻击力+15%，防御力+15%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `s1_atk` | 0.15 |
| `s1_def` | 0.15 |

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

### 战火淬炼　`skchr_cathy_2`

**技能描述（最高级）：**

> 停止攻击，生命上限+70%，防御力+30%，装置效果改为使目标干员每秒获得相当于凯瑟琳生命上限6%的屏障（不会超过天赋上限）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 0.7 |
| `def` | 0.3 |
| `overwrite_ratio` | 0.06 |
| `interval` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`cathy_s_2[aura]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

**`cathy_s_2[aura]`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

**`cathy_s_2[aura]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerBuffsByKeys** `_buffKeys`=["catsld_t_1[core]"] `_targetType`="BUFF_OWNER"

**`cathy_s_2[recycle]`** ← 事件 `ON_BUFF_START`

- **WithdrawTokens** 
- **RechargeToken** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
