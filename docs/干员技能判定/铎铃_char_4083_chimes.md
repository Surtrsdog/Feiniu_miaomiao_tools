# 铎铃 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4083_chimes` |
| 职业 | 近卫 / `crusher` |
| 星级 | 5 星 |
| 生命（精二满级） | 5669 |
| 攻击（精二满级） | 1438 |
| 防御（精二满级） | 0 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.5 ÷ 1.00 = 2.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4083_chimes_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.566667 秒** | 17 帧 |

> 占攻击间隔 22.7%（0.566667 秒 / 2.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_End` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 攻击力强化·γ型　`skcom_atk_up[3]`

**技能描述（最高级）：**

> 攻击力+100%


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
| `atk` | 1 |

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

### 乡心无改　`skchr_chimes_2`

**技能描述（最高级）：**

> 停止攻击，获得40%的庇护，攻击力逐渐增至+50%。技能结束时对前方所有地面敌人造成此时攻击力230%的物理伤害并使其晕眩1秒
> 可主动关闭技能（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 5 秒 |
| duration / durationType | 5 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `damage_resistance` | 0.4 |
| `atk` | 0.5 |
| `attack@stun` | 1 |
| `attack@atk_scale` | 2.3 |
| `maxcnt` | 5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chimes_s_2[cast]`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`chimes_s_2_atk` `maxStackCnt`=6 `overrideType`=STACK `lifeTimeType`=INFINITY
- **AttributeModifierWithCertainBuffCount** `_targetType`="BUFF_OWNER"

**`chimes_s_2[end]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`chimes_s_2[prepareToEnd]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`chimes_s_2[toMode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
