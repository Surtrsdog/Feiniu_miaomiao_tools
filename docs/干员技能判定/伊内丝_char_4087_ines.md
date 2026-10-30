# 伊内丝 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4087_ines` |
| 职业 | 先锋 / `agent` |
| 星级 | 6 星 |
| 生命（精二满级） | 2121 |
| 攻击（精二满级） | 589 |
| 防御（精二满级） | 281 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 11 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4087_ines_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 46.7%（0.466667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Combat` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 淬影突袭　`skchr_ines_1`

**技能描述（最高级）：**

> 下次攻击使目标3秒内每秒受到相当于伊内丝攻击力80%的法术伤害（不叠加），并获得2点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 3 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 2 |
| `bleed_atk_scale` | 0.8 |
| `bleed_duration` | 3 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ines_s_1[damage]`** ← 事件 `ON_BUFF_START`

- **ModifyCost** 
- **AssignAttributeToBB** `_targetType`="BUFF_SOURCE"

**`ines_s_1[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **FixedValueDamage** `_targetType`="TARGET"

---

### 暗夜无明　`skchr_ines_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+110%，自身获得隐匿，每次攻击获得1点部署费用并偷取目标7点攻击速度（最多70点，持续至技能结束或伊内丝离场）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 1 |
| `atk` | 1.1 |
| `attack@steal_atk_speed` | 7 |
| `attack@steal_atk_speed_max` | 70 |

#### 攻击范围

`rangeId = 3-13`，8 格（direction=1）

```
· ■ ■ · 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ines_s_2`** ← 事件 `ON_BEFORE_TARGET_APPLY_MODIFIER`

- **IsDamage** 
- **IfTarget** `_targetType`="MODIFIER_TARGET"
- **TriggerAbility** `_targetType`="MODIFIER_TARGET"

**`ines_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ines_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ines_s_2`** ← 事件 `ON_OUTPUT_DAMAGE`

- **ModifyCost** 

---

### 独影归途　`skchr_ines_3`

**技能描述（最高级）：**

> 首次部署时不消耗部署费用，放置一个影哨后离场并立刻刷新再部署时间
> 部署后攻击力+160%，立刻收回影哨对穿过的最多6名敌人造成相当于攻击力200%的物理伤害，技能期间每对一个敌人造成伤害就获得1点部署费用


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 1 |
| `atk` | 1.6 |
| `atk_scale` | 2 |
| `max_target` | 6 |
| `projectile_range` | 1.4 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ines_s_3`** ← 事件 `ON_OUTPUT_DAMAGE`

- **ModifyCost** 

**`ines_s_3`** ← 事件 `ON_BUFF_TRIGGER`

- **EmitProjectileFromManagedProjectiles** `_targetType`="BUFF_OWNER"
- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"

**`ines_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ines_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ines_s_3[deck]`** ← 事件 `ON_OWNER_FINISH`

- **CreateCardBuff** `_target`="TARGET"

**`ines_s_3[summon]`** ← 事件 `ON_BUFF_START`

- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **SandboxDisableClickCharacterInfo** `_target`="TARGET"
- **AlwaysNext** 
- **LegionModeOnlyMarkCardReturnToHand** 

**`ines_s_3[summon]`** ← 事件 `ON_OWNER_LOCATE`

- **Withdraw** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
