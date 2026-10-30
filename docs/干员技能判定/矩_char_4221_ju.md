# 矩 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4221_ju` |
| 职业 | 狙击 / `siegesniper` |
| 星级 | 5 星 |
| 生命（精二满级） | 1600 |
| 攻击（精二满级） | 990 |
| 防御（精二满级） | 120 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.4 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 25 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.4 ÷ 1.00 = 2.400 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4221_ju_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 22.2%（0.533333 秒 / 2.4 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 良弓难张　`skchr_ju_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力250%的物理伤害，不会选择生命值高于一半的敌人作为目标
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale_s1` | 2.5 |

#### 攻击范围

`rangeId = 4-3`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 良翼难乘　`skchr_ju_2`

**技能描述（最高级）：**

> 攻击力+100%，额外攻击1个目标；技能期间对攻击范围内生命值低于一半的敌人仅一次造成相当于攻击力100%的额外物理伤害（该次伤害有短暂间隔）
> 每个敌人最多受到一次额外物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@max_target_s2` | 2 |
| `atk_scale_s2_extra` | 1 |
| `hp_ratio` | 0.5 |

#### 攻击范围

`rangeId = 4-3`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ju_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckModifierContainsKey** 
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["ju_s_2[done]"] `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
      - **IfElse** 
        - **FilterByTargetHpRatio** `_condType`="LT" `_targetType`="BUFF_OWNER"
        - **CreateBuff** buffKey=`ju_s_2[damage_dalay]` templateKey=`ju_s_2[damage_dalay]` `overrideType`=UNIQUE `lifeTimeType`=LIMITED
        - **CreateBuff** buffKey=`ju_s_2[done]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`ju_s_2[damage]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **IfTarget** `_targetType`="BUFF_OWNER"
  - **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
  - **PlayAudio** `_target`="BUFF_OWNER"
  - **AlwaysNext** 
  - **CreateEffect** `_targetType`="BUFF_OWNER"

**`ju_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`ju_s_2[source]` `overrideType`=UNIQUE `lifeTimeType`=LIMITED
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"

**`ju_s_2[damage_dalay]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuff** buffKey=`ju_s_2[damage_trigger]` templateKey=`ju_s_2[damage_trigger]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`ju_s_2[damage_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IfTarget** `_targetType`="BUFF_SOURCE"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["ju_s_2[source]"] `_targetType`="BUFF_SOURCE"
    - **CreateBuff** buffKey=`ju_s_2[damage]` templateKey=`ju_s_2[damage]` `overrideType`=UNIQUE `lifeTimeType`=LIMITED
    - **FinishBuff** 
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
