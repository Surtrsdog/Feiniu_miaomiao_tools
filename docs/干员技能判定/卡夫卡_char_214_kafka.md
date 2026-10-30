# 卡夫卡 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_214_kafka` |
| 职业 | 特种 / `executor` |
| 星级 | 5 星 |
| 生命（精二满级） | 1675 |
| 攻击（精二满级） | 525 |
| 防御（精二满级） | 311 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.93 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 9 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.93 ÷ 1.00 = 0.930 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_214_kafka_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 53.8%（0.5 秒 / 0.93 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_End` | 0.3 秒 | 9 帧 |


## 三、技能逐层拆解

---

### 怪异魔方　`skchr_kafka_1`

**技能描述（最高级）：**

> 部署后5秒内停止攻击，立即使周围地面敌人全部陷入沉睡，并在技能结束时对周围所有地面敌人造成相当于攻击力450%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4.5 |
| `duration` | 5 |

#### 攻击范围

`rangeId = x-5`，5 格（direction=1）

```
· ■ · 
■ ■ ■ 
· ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`kafka_s_1`** ← 事件 `ON_BUFF_FINISH`

- **IfTarget** `_targetType`="SOURCE"
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`kafka_s_1[effect_1]` `lifeTimeType`=LIMITED
- **CreateBuff** buffKey=`kafka_s_1[effect_2]` `lifeTimeType`=LIMITED

---

### 诡异剪刀　`skchr_kafka_2`

**技能描述（最高级）：**

> 部署后立即对前方目标格内所有敌人造成相当于攻击力400%的法术伤害，并在之后15秒内对目标格持续进行地面单体法术攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4 |
| `duration` | 15 |

#### 攻击范围

`rangeId = 3-16`，1 格（direction=1）

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`kafka_s_2[audio]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuff** buffKey=`kafka_s_2[audio_release]` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
