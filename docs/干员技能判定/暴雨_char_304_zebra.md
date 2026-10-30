# 暴雨 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_304_zebra` |
| 职业 | 重装 / `protector` |
| 星级 | 5 星 |
| 生命（精二满级） | 3380 |
| 攻击（精二满级） | 378 |
| 防御（精二满级） | 721 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_304_zebra_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 36.1%（0.433333 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.233333 秒 | 7 帧 |


## 三、技能逐层拆解

---

### 应急迷彩　`skchr_zebra_1`

**技能描述（最高级）：**

> 下一次攻击会使周围血量不足一半的一名友方干员获得迷彩并每秒恢复70点生命，持续（持续时间见触发条件表）秒（不会对已有该技能效果的干员重复释放）
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 4 秒 |
| duration / durationType | 4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `hp_recovery_per_sec` | 70 |
| `cnt` | 2 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`zebra_s_1`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["zebra_s_1[camouflage]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`zebra_s_1[camouflage]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`zebra_s_1`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 群体迷彩　`skchr_zebra_2`

**技能描述（最高级）：**

> 停止攻击敌人；防御力+55%，生命上限+55%，使自身和周围4格内的友方干员获得迷彩


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 0.55 |
| `def` | 0.55 |

#### 攻击范围

`rangeId = x-5`，5 格（direction=1）

```
· ■ · 
■ ■ ■ 
· ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`zebra_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["zebra_s_2[camouflage]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`zebra_s_2[camouflage]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`zebra_s_2`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
