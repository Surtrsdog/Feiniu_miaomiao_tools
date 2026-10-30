# 烛煌 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1040_blaze2` |
| 职业 | 术师 / `primcaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1608 |
| 攻击（精二满级） | 662 |
| 防御（精二满级） | 131 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1040_blaze2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 27.1%（0.433333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Loop` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 炙手之援　`skchr_blaze2_1`

**技能描述（最高级）：**

> 立即选择攻击范围内生命上限最高的一名干员，每秒对其周围所有敌人造成相当于攻击力70%的法术伤害和相当于法术伤害30%的灼燃损伤，持续20秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 0.7 |
| `element_multiplier` | 0.3 |
| `max_duration` | 20 |
| `range_radius` | 1.5 |
| `interval` | 1 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`blaze2_s_1`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffInCircleRange** `_count`=0 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

**`blaze2_s_1`** ← 事件 `ON_TAKE_DAMAGE`


**`blaze2_s_1`** ← 事件 `ON_BUFF_START`

- **AssignAttributeToBB** `_targetType`="BUFF_SOURCE"

**`blaze2_s_1[aura]`** ← 事件 `ON_BUFF_START`

- **FixedValueDamage** `_targetType`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"

---

### 沸血燎原　`skchr_blaze2_2`

**技能描述（最高级）：**

> 攻击范围改变，攻击间隔增大，攻击力+150%，同时攻击3名敌人；攻击时流失5%的生命并在目标所在位置留下灼烧地段：经过的敌人移动速度-50%，每秒受到烛煌攻击力35%的法术伤害和相当于法术伤害30%的灼燃损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 23 / 36 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `base_attack_time` | 0.9 |
| `atk_scale` | 0.35 |
| `attack@max_target` | 3 |
| `attack@hp_ratio` | 0.05 |
| `element_damage_scale` | 0.3 |
| `move_speed` | -0.5 |

#### 攻击范围

`rangeId = x-2`，21 格（direction=1）

```
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`blaze2_s_2[cleaner]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryEnemyById** `_source`="BUFF_OWNER"

**`blaze2_s_2[finish]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryEnemyById** `_source`="BUFF_OWNER"

**`blaze2_s_2[leave_tile]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`blaze2_s_2[on_tile]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`blaze2_s_2[slow]` 属性修改=[MOVE_SPEED MULTIPLIER blackboard] `lifeTimeType`=INFINITY

**`blaze2_s_2[on_tile]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"

**`blaze2_s_2[self_damage]`** ← 事件 `ON_BUFF_START`

- **DamageViaMaxHpRatio** `_targetType`="BUFF_OWNER"

**`blaze2_s_2[tile_trigger]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

### 众恶的焚场　`skchr_blaze2_3`

**技能描述（最高级）：**

> 攻击范围改变，攻击力+115%，攻击间隔大幅缩短，攻击变为群体攻击；若目标处于灼燃损伤爆发期间则额外造成攻击力80%的元素伤害
> 自身每秒流失最大生命的3%，攻击装有25发弹药，全场有敌人进入灼燃损伤爆发时获得2颗额外弹药，弹药打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.15 |
| `base_attack_time` | -1.3 |
| `attack@trigger_time` | 25 |
| `attack@atk_scale` | 0.8 |
| `lose_hp_scale` | 0.03 |
| `ammo_recover` | 2 |
| `skill_max_trigger_time` | -1 |

#### 攻击范围

`rangeId = 4-11`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`blaze2_s_3[additional_damage]`** ← 事件 `ON_BUFF_START`

- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"

**`blaze2_s_3[listener]`** ← 事件 `ON_BEFORE_EP_BREAK_START`

- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **AmmoSkillCountModifier** `_targetType`="BUFF_SOURCE"

**`blaze2_s_3[lose_hp]`** ← 事件 `ON_BUFF_TRIGGER`

- **DamageViaMaxHpRatio** `_targetType`="BUFF_OWNER"

**`blaze2_s_3[lose_hp]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
