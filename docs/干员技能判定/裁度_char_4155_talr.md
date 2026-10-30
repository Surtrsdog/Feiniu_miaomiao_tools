# 裁度 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4155_talr` |
| 职业 | 特种 / `merchant` |
| 星级 | 5 星 |
| 生命（精二满级） | 2393 |
| 攻击（精二满级） | 741 |
| 防御（精二满级） | 391 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 8 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4155_talr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 50.0%（0.5 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Begin` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 量衣尺　`skchr_talr_1`

**技能描述（最高级）：**

> 攻击距离+1，攻击力+60%
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `ability_range_forward_extend` | 1 |

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

### 缝线缠身　`skchr_talr_2`

**技能描述（最高级）：**

> 停止攻击，立即束缚周围最多4名敌人，并每秒对被束缚的敌人造成攻击力160%的物理伤害；技能开启期间逐渐消耗25点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 8 秒 |
| duration / durationType | 8 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.6 |
| `max_target` | 4 |
| `cost_display` | 25 |
| `talr_s_2[cost].cost` | -1 |
| `talr_s_2[cost].interval` | 0.32 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`talr_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
- **CreateBuffUseAbilitySelector** buffKey=`talr_s_2[dmg]` templateKey=`talr_s_2[dmg]` `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"

**`talr_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`talr_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckContainsBuff** `_buffKeys`=["talr_s_2[do_not_finish_martk]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`talr_s_2[dmg]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="BUFF_OWNER"

**`talr_s_2[dmg]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`talr_s_2[do_not_finish_martk]` `maxStackCnt`=99 `overrideType`=STACK `lifeTimeType`=INFINITY
- **LogExtraBattleInfo** `_target`="BUFF_OWNER" `_key`="output_unmovable"

**`talr_s_2[dmg]`** ← 事件 `ON_BUFF_FINISH`

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
