# 菲莱 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4148_philae` |
| 职业 | 重装 / `primprotector` |
| 星级 | 5 星 |
| 生命（精二满级） | 3227 |
| 攻击（精二满级） | 603 |
| 防御（精二满级） | 544 |
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

来源：`bakemuzzledata/character/char_4148_philae_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.766667 秒** | 23 帧 |

> 占攻击间隔 47.9%（0.766667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 灵河护佑　`skchr_philae_1`

**技能描述（最高级）：**

> 生命上限+90%，立刻清除自身的元素损伤并获得1800点损伤屏障


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 0.9 |
| `shield_value` | 1800 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`philae_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **ApplyElementHeal** 

**`philae_s_1`** ← 事件 `ON_APPLYING_MODIFIER`

- **IsElementDamage** 
- **BlockElementDamage** 

**`philae_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 冥河诅咒　`skchr_philae_2`

**技能描述（最高级）：**

> 停止攻击，生命上限+50%，受到攻击时对周围的地面敌人造成攻击力200%的法术伤害并附带25%攻击力的凋亡损伤（每2秒最多触发一次）；若技能期间受到元素损伤则攻击力+100%至技能结束


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |
| `ep_damage_ratio` | 0.25 |
| `atk` | 1 |
| `aoe_cd` | 2 |
| `max_hp` | 0.5 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`philae_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`philae_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`philae_s_2`** ← 事件 `ON_TAKE_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["philae_s_2[cd]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateBuff** buffKey=`philae_s_2[cd]` `lifeTimeType`=LIMITED
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`philae_s_2`** ← 事件 `ON_APPLYING_MODIFIER`

- **IfElse** 
  - **IsElementDamage** 
  - **CheckContainsBuff** `_buffKeys`=["philae_s_2[atk]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`philae_s_2[atk]` 属性修改=[ATK MULTIPLIER blackboard] `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **CreateEffect** `_targetType`="BUFF_OWNER"

**`philae_s_2[ep]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="TARGET"
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["philae_s_2[atk]"] `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
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
