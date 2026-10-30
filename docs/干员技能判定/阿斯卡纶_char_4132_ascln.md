# 阿斯卡纶 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4132_ascln` |
| 职业 | 特种 / `stalker` |
| 星级 | 6 星 |
| 生命（精二满级） | 1623 |
| 攻击（精二满级） | 954 |
| 防御（精二满级） | 333 |
| 法抗 | 3000% |
| **攻击间隔 baseAttackTime** | **3.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 0 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 3.5 ÷ 1.00 = 3.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4132_ascln_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.7 秒** | 21 帧 |

> 占攻击间隔 20.0%（0.7 秒 / 3.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.7 秒 | 21 帧 |
| 技能动画 | `Skill_2` | 0.933333 秒 | 28 帧 |
| 技能动画 | `Skill_3_Loop` | 0.933333 秒 | 28 帧 |


## 三、技能逐层拆解

---

### 追袭　`skchr_ascln_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至210%，并连续攻击两次
> 可充能3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 4 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.1 |
| `cnt` | 3 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 恩赐　`skchr_ascln_2`

**技能描述（最高级）：**

> 攻击力+130%，使攻击范围内地面敌人移动速度-60%，并在其被击倒时对周围敌人施加一层第一天赋效果


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.3 |
| `move_speed` | -0.6 |
| `range_radius` | 1.3 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ascln_s_2[enemy]`** ← 事件 `ON_OWNER_KILLED`

- **CheckMotionMode** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_SOURCE"
  - **CreateBuffInCircleRange** `_count`=0 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **CreateBuffInCircleRange** `_count`=0 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **CreateBuffInCircleRange** `_count`=0 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **AlwaysNext** 
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **PlayAudio** `_target`="BUFF_SOURCE"

---

### 降临　`skchr_ascln_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+50%，攻击间隔较大幅度缩短，使攻击范围内的地面敌人物理与法术命中率-50%。自身更易受到敌人攻击，敌人未命中自身或自身闪避时回复8%最大生命值


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 45 秒 |
| duration / durationType | 45 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -1.5 |
| `atk` | 0.5 |
| `taunt_level` | 2 |
| `attack@hp_ratio` | 0.08 |
| `attack@damage_hitrate_physical` | -0.5 |
| `attack@damage_hitrate_magical` | -0.5 |

#### 攻击范围

`rangeId = y-10`，18 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ascln_s_3[self]`** ← 事件 `ON_EVADE_DAMAGE`

- **HealViaMaxHpRatio** 
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`ascln_s_3[self]`** ← 事件 `ON_TAKE_DAMAGE`

- **FilterModifierCancelReason** 
- **HealViaMaxHpRatio** 
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
