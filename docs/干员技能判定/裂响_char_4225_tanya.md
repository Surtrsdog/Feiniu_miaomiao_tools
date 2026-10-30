# 裂响 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4225_tanya` |
| 职业 | 重装 / `primprotector` |
| 星级 | 5 星 |
| 生命（精二满级） | 3195 |
| 攻击（精二满级） | 602 |
| 防御（精二满级） | 549 |
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

来源：`bakemuzzledata/character/char_4225_tanya_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.566667 秒** | 17 帧 |

> 占攻击间隔 35.4%（0.566667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.633333 秒 | 19 帧 |
| 技能动画 | `Skill_2` | 0.666667 秒 | 20 帧 |


## 三、技能逐层拆解

---

### 涤净　`skchr_tanya_1`

**技能描述（最高级）：**

> 生命上限+100%，自身每秒回复120点元素损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1 |
| `ep_heal` | 120 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tanya_s_1`** ← 事件 `ON_BUFF_TRIGGER`

- **FixedValueElementHeal** `_targetType`="BUFF_OWNER"

**`tanya_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`tanya_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 溃决　`skchr_tanya_2`

**技能描述（最高级）：**

> 获得5层可叠加的防御力+20%的增益，受到攻击后消耗1层，并对周围所有地面敌人造成相当于攻击力35%的侵蚀损伤
> 增益最多叠加5层


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 12 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 0.2 |
| `ep_damage_ratio` | 0.35 |
| `max_stack_cnt` | 5 |
| `cnt` | 5 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tanya_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuffStacked** buffKey=`tanya_s_2[def]` 属性修改=[DEF MULTIPLIER blackboard] `overrideType`=STACK `lifeTimeType`=INFINITY

**`tanya_s_2[check]`** ← 事件 `ON_APPLIED_MODIFIER`

- **FilterModifierByRealDelta** `_condType`="LT"
- **CheckContainsBuff** `_buffKeys`=["tanya_s_2[def]"] `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuffInRange** `_targetType`="TARGET" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateEffect** `_targetType`="SOURCE"
- **PlayAudio** `_target`="BUFF_OWNER"

**`tanya_s_2[ep_damage]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
