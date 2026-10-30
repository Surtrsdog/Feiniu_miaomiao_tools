# 淬羽赫默 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1031_slent2` |
| 职业 | 辅助 / `blessing` |
| 星级 | 6 星 |
| 生命（精二满级） | 1927 |
| 攻击（精二满级） | 467 |
| 防御（精二满级） | 184 |
| 法抗 | 2500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 15 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1031_slent2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.666667 秒** | 20 帧 |

> 占攻击间隔 41.7%（0.666667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.633333 秒 | 19 帧 |
| 技能动画 | `Skill_2_Loop` | 0.633333 秒 | 19 帧 |


## 三、技能逐层拆解

---

### 进取之心　`skchr_slent2_1`

**技能描述（最高级）：**

> 攻击力+80%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 俯瞰视界　`skchr_slent2_2`

**技能描述（最高级）：**

> 攻击速度+60，技能期间可以使用一个辅助无人机
> 无人机投入战场后使周围友军享受3倍的第一天赋效果，技能结束或淬羽赫默离场时销毁


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 24 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 60 |
| `damage_resistance_scale` | 3 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`slent2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **WithdrawTokens** 
- **AlwaysNext** 
- **RechargeToken** 
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`slent2_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

---

### 无畏者协议　`skchr_slent2_3`

**技能描述（最高级）：**

> 攻击力+30%，第一天赋效果提升至1.8倍；技能期间仅一次，攻击范围内的一名干员受到致命伤时，使其生命值在10秒内不低于1
> 同一次作战中最多使用2次，可主动关闭（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 60 秒 |
| duration / durationType | 60 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.3 |
| `talent_scale` | 1.8 |
| `grave_duration` | 10 |
| `skill_max_trigger_time` | 2 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`slent2_s_3`** ← 事件 `ON_BEFORE_TRY_SET_HP_ZERO`

- **CheckEntitySuicide** 
- **IfNot** 
- **CheckContainsBuff** `_buffKeys`=["slent2_shallow_grave[self]"] `_targetType`="BUFF_SOURCE"
- **ConsumeTrySetHpZeroModifier** 
- **CreateBuff** buffKey=`slent2_shallow_grave` `lifeTimeType`=LIMITED
- **FinishBuffsById** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
