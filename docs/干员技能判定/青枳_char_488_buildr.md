# 青枳 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_488_buildr` |
| 职业 | 先锋 / `pioneer` |
| 星级 | 5 星 |
| 生命（精二满级） | 2215 |
| 攻击（精二满级） | 455 |
| 防御（精二满级） | 360 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_488_buildr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 47.6%（0.5 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 冲锋号令·γ型　`skcom_charge_cost[3]`

**技能描述（最高级）：**

> 立即获得12点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 12 |

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

### 工程者之愿　`skchr_buildr_2`

**技能描述（最高级）：**

> 立即获得12点费用；技能持续时间内攻击力+35%，防御力+65%
> 第二次及以后使用时，每4秒额外获得1点费用，且持续时间无限


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
| `cost` | 12 |
| `duration` | 15 |
| `atk` | 0.35 |
| `def` | 0.65 |
| `buildr_s_2[b].duration` | -1 |
| `buildr_s_2[b].atk` | 0.35 |
| `buildr_s_2[b].def` | 0.65 |
| `buildr_s_2[b].cost` | 1 |
| `buildr_s_2[b].interval` | 4 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`buildr_s_2[b]`** ← 事件 `ON_BUFF_TRIGGER`

- **ModifyCost** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
