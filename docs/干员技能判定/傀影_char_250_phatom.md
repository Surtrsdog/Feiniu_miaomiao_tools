# 傀影 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_250_phatom` |
| 职业 | 特种 / `executor` |
| 星级 | 6 星 |
| 生命（精二满级） | 1645 |
| 攻击（精二满级） | 558 |
| 防御（精二满级） | 322 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.93 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 10 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.93 ÷ 1.00 = 0.930 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_250_phatom_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.266667 秒** | 8 帧 |

> 占攻击间隔 28.7%（0.266667 秒 / 0.93 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 暗夜魅影　`skchr_phatom_1`

**技能描述（最高级）：**

> 部署后立即获得50%的物理闪避和可吸收相当于自己最大生命80%物理伤害的屏障，持续10秒


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
| `prob` | 0.5 |
| `hp_ratio` | 0.8 |
| `duration` | 10 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`phatom_s_1[shield_physical]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["phatom_s_1[shield][internal]"] `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`phatom_s_1[shield][internal]` templateKey=`shield_physical` `lifeTimeType`=INFINITY

**`phatom_s_1[shield_physical]`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

---

### 血色乐章　`skchr_phatom_2`

**技能描述（最高级）：**

> 部署后立即获得10层可叠加的攻击力+20%的增益（每攻击一次消耗一层）


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
| `times` | 10 |
| `atk` | 0.2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`phatom_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuffs** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`phatom_s_2[atk]`** ← 事件 `ON_AFTER_OUTPUT_DAMAGE`

- **FinishBuff** 
- **CheckContainsBuff** `_buffKeys`=["phatom_s_2[atk]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`phatom_s_2[reset]` templateKey=`switch_mode_after_attack` `lifeTimeType`=INFINITY

---

### 夜幕突袭　`skchr_phatom_3`

**技能描述（最高级）：**

> 部署后立即对周围所有敌人造成相当于攻击力300%的物理伤害，将其小力地推开并随机施加以下任意一个状态（停顿、束缚、晕眩）4.5秒


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
| `atk_scale` | 3 |
| `force` | 0 |
| `sluggish` | 4.5 |
| `root` | 4.5 |
| `stun` | 4.5 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
