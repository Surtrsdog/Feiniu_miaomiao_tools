# 响石 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4214_cairn` |
| 职业 | 重装 / `primprotector` |
| 星级 | 5 星 |
| 生命（精二满级） | 3483 |
| 攻击（精二满级） | 546 |
| 防御（精二满级） | 560 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 25 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4214_cairn_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 37.5%（0.6 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2` | 0.6 秒 | 18 帧 |


## 三、技能逐层拆解

---

### 覆盖式休整　`skchr_cairn_1`

**技能描述（最高级）：**

> 生命上限+130%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1.3 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`cairn_s_1[self]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`cairn_s_1[self]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 震撼型指路　`skchr_cairn_2`

**技能描述（最高级）：**

> 立即获得90%最大生命值的屏障（屏障持续10秒，最多不超过生命上限90%），并使自身周围地面敌人10秒内每秒受到相当于攻击力80%的法术伤害和攻击力10%的神经损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 22 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `buff_duration` | 10 |
| `shield_max_hp_ratio` | 0.9 |
| `atk_scale` | 0.8 |
| `ep_damage_ratio` | 0.1 |
| `shield_hp_ratio` | 0.9 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`cairn_s_2[create_shield]`** ← 事件 `ON_BUFF_START`

- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["cairn_s_2[shield]"] `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
  - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **AssignBuffBlackboard** `_targetType`="TARGET"
  - **CreateBuff** buffKey=`cairn_s_2[shield]` templateKey=`cairn_s_2[shield]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
  - **CreateBuff** buffKey=`cairn_s_2[shield]` templateKey=`cairn_s_2[shield]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
  - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

**`cairn_s_2[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="TARGET"
- **AlwaysNext** 
- **IfConditions** 
  - **CheckUnitAlive** 
  - **ApplyElementDamage** `_targetType`="TARGET"
  - **ApplyElementDamage** `_targetType`="TARGET"
- **AlwaysNext** 
- **PlayAudio** `_target`="TARGET"

**`cairn_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **AssignAttributeToBB** `_targetType`="SOURCE"

**`cairn_s_2[shield]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
- **FinishBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
