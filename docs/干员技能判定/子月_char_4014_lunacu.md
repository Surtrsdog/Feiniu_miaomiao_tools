# 子月 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4014_lunacu` |
| 职业 | 狙击 / `longrange` |
| 星级 | 5 星 |
| 生命（精二满级） | 1536 |
| 攻击（精二满级） | 1034 |
| 防御（精二满级） | 155 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.7 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.7 ÷ 1.00 = 2.700 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4014_lunacu_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.7 秒** | 21 帧 |

> 占攻击间隔 25.9%（0.7 秒 / 2.7 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.1 秒 | 3 帧 |


## 三、技能逐层拆解

---

### 狩猎时刻　`skchr_lunacu_1`

**技能描述（最高级）：**

> 攻击力+100%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 18 秒 |
| duration / durationType | 18 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 伏击之影　`skchr_lunacu_2`

**技能描述（最高级）：**

> 攻击速度+140；获得8秒迷彩，技能期间击倒敌人后获得8秒迷彩


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 140 |
| `lunacu_s_2[cam].cam_duration` | 8 |
| `lunacu_s_2[start_cam].start_cam_duration` | 8 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`lunacu_s_2`** ← 事件 `ON_TARGET_KILLED`

- **CreateBuff** buffKey=`lunacu_s_2[cam]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
- **CheckContainsBuff** `_buffKeys`=["lunacu_s_2[start_cam]"] `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`lunacu_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **CreateBuff** buffKey=`lunacu_s_2[start_cam]` `lifeTimeType`=LIMITED

**`lunacu_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=-1 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
