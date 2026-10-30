# 余 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_2026_yu` |
| 职业 | 重装 / `primprotector` |
| 星级 | 6 星 |
| 生命（精二满级） | 3333 |
| 攻击（精二满级） | 685 |
| 防御（精二满级） | 577 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 26 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_2026_yu_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Begin` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 今日做东　`skchr_yu_1`

**技能描述（最高级）：**

> 被动效果：自身更容易受到敌人攻击
> 生命上限+70%，防御力+70%，每次受到攻击对目标造成相当于余攻击力50%的灼燃损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 0 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 0.7 |
| `def` | 0.7 |
| `ep_damage_ratio` | 0.5 |
| `taunt_level` | 1 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`yu_s_1[inverse_damage]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfElse** 
  - **IfDamageTargetSide** `_targetType`="MODIFIER_TARGET"
  - **ApplyElementDamage** `_targetType`="MODIFIER_SOURCE"
  - **CreateEffect** `_targetType`="MODIFIER_SOURCE"

---

### 厚礼上宾　`skchr_yu_2`

**技能描述（最高级）：**

> 立即对周围所有敌人造成相当于攻击力100%的法术伤害并将其中的地面可达目标传送至自身位置，阻挡数+2，生命上限+160%，攻击力+290%，普通攻击造成法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 26 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1.6 |
| `atk` | 2.9 |
| `atk_scale` | 1 |
| `block_cnt` | 2 |

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

> 匹配方式：按命名规则匹配（层级 B）

**`yu_s_2[buff_eff]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`yu_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`yu_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"

**`yu_s_2[try_tp]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["immune_shu_blink", "immune_yu_blink"] `_targetType`="BUFF_OWNER"
  - **CheckEntityDisappeared** `_targetType`="BUFF_OWNER"
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **CheckMotionMode** `_targetType`="BUFF_OWNER"
    - **IfTarget** `_targetType`="BUFF_OWNER"
    - **AssignRootTileToBB** `_targetType`="BUFF_SOURCE"
    - **CheckEnemyRealReachableToTile** 
    - **ForceSetToTilePosition** `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 灶里乾坤　`skchr_yu_3`

**技能描述（最高级）：**

> 生命上限+110%，攻击力+110%，防御力+110%，将第二天赋效果赋予全场所有干员；生成一面跨越整个战场的火墙，其他友方穿过火墙造成法术伤害时附带相当于余攻击力10%的灼燃损伤，敌方子弹穿过火墙时有20%几率被清除


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 42 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 45 秒 |
| duration / durationType | 45 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1.1 |
| `atk` | 1.1 |
| `def` | 1.1 |
| `ep_damage_ratio` | 0.1 |
| `prob` | 0.2 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`yu_s_3[ally]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfConditions** 
  - **FilterDamageModifer** `_source`="BUFF_OWNER"
  - **IfTargetSide** `_targetType`="MODIFIER_TARGET"
  - **IfElse** 
    - **IfTargetEqual** 
    - **IfElse** 
      - **IfTargetSide** `_targetType`="MODIFIER_SOURCE"
      - **SwitchDirection** `_source`="BUFF_SOURCE"
        - **IfConditions** 
          - **CheckTargetGridPositionRowOrColWithBB** `_target`="MODIFIER_SOURCE"
          - **CheckTargetGridPositionRowOrColWithBB** `_target`="MODIFIER_TARGET"
          - **ApplyElementDamage** `_targetType`="MODIFIER_TARGET"
          - **CreateEffect** `_targetType`="MODIFIER_TARGET"
          - **IfConditions** 
            - **CheckTargetGridPositionRowOrColWithBB** `_target`="MODIFIER_SOURCE"
            - **CheckTargetGridPositionRowOrColWithBB** `_target`="MODIFIER_TARGET"
- …（共 48 个节点，已截断）

**`yu_s_3[ally]`** ← 事件 `ON_BUFF_START`

- **AssignRootTileToBB** `_targetType`="BUFF_SOURCE"

**`yu_s_3[effect]`** ← 事件 `ON_BUFF_START`

- **AssignDirectionToBB** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`yu_s_3[effect_finish]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`yu_s_3[mode_restart]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

**`yu_s_3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"
- **InterruptAbility** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
