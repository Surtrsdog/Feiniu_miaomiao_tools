# 霜华 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_458_rfrost` |
| 职业 | 特种 / `traper` |
| 星级 | 5 星 |
| 生命（精二满级） | 1359 |
| 攻击（精二满级） | 529 |
| 防御（精二满级） | 157 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 11 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.85 ÷ 1.00 = 0.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_458_rfrost_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 39.2%（0.333333 秒 / 0.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 陷阱部署　`skchr_rfrost_1`

**技能描述（最高级）：**

> 被动效果：迎宾踏垫触发时对目标造成相当于攻击力的350%的物理伤害，并使其晕眩1.5秒
> 主动效果：立即获得一个迎宾踏垫


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cnt` | 1 |
| `atk_scale` | 3.5 |
| `stun` | 1.5 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 击倒猎物　`skchr_rfrost_2`

**技能描述（最高级）：**

> 被动效果：迎宾踏垫触发时造成200%的物理伤害，并使其束缚1.5秒；若其在攻击范围内,则立即对其进行攻击力180%的3次攻击；主动效果：立即获得一个迎宾踏垫


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cnt` | 1 |
| `atk_scale` | 1.8 |
| `constraint` | 1.5 |
| `times` | 3 |
| `trap_atk_scale` | 2 |

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

**`rfrost_s_2[interrupt]`** ← 事件 `ON_BUFF_START`

- **InterruptCharacterAttack** `_charFrom`="BUFF_OWNER"

**`rfrost_s_2[trigger]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
