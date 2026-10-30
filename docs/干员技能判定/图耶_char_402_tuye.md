# 图耶 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_402_tuye` |
| 职业 | 医疗 / `physician` |
| 星级 | 5 星 |
| 生命（精二满级） | 1550 |
| 攻击（精二满级） | 493 |
| 防御（精二满级） | 135 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_402_tuye_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 15.2%（0.433333 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_1_Down` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2_Attack` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 水流环　`skchr_tuye_1`

**技能描述（最高级）：**

> 立即进行一次治疗并使目标获得一个持续5秒的屏障（可以吸收相当于图耶攻击力200%的伤害）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |
| `duration` | 5 |

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

**`tuye_s_1[shield]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **IsBlackboardZero** 
- **FinishBuff** 

---

### 强心剂　`skchr_tuye_2`

**技能描述（最高级）：**

> 攻击力+60%，仅治疗生命低于一半的干员。范围内干员生命低于20%时立即治疗其相当于攻击力300%的生命，触发3次后技能立即结束。持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `max_hp_ratio` | 0.2 |
| `heal_scale` | 3 |
| `skill_interval` | 1 |

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

**`tuye_s_2[finish_effect_1]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`tuye_s_2[finish_effect_2]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`tuye_s_2[finish_effect_3]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`tuye_s_2[trigger_heal]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbility** `_targetType`="TARGET"

**`tuye_s_2[trigger_heal]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`tuye_s_2[trigger_heal]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
