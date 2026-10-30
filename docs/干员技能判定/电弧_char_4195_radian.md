# 电弧 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4195_radian` |
| 职业 | 辅助 / `summoner` |
| 星级 | 6 星 |
| 生命（精二满级） | 1069 |
| 攻击（精二满级） | 466 |
| 防御（精二满级） | 143 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4195_radian_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 25.0%（0.4 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Loop` | 0.133333 秒 | 4 帧 |
| 技能动画 | `Skill_3_Loop` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 律动线　`skchr_radian_1`

**技能描述（最高级）：**

> 被动：召唤物可部署在近战位
> 开启：自身和召唤物防御力+80%并获得100%最大生命值的屏障，持续至技能结束
> 技能开启时获得1个召唤物


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `hp_ratio` | 1 |
| `def` | 0.8 |
| `cnt` | 1 |

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

**`radian_s_1[shield]`** ← 事件 `ON_BUFF_START`

- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_OWNER"

**`radian_s_1[shield]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **FinishBuff** 

**`radian_s_1[shield_token]`** ← 事件 `ON_BUFF_TRIGGER`

- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_OWNER"
- **AssignValueToBB** 

**`radian_s_1[shield_token]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
  - **FinishBuff** 

---

### 环形鳞地　`skchr_radian_2`

**技能描述（最高级）：**

> 被动：召唤物可部署在近战位，会持续向前方发射子弹
> 开启：自身和召唤物攻击力+80%，召唤物攻击额外创造出2颗子弹且子弹飞行距离+2
> 技能开启时获得1个召唤物


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 16 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `base_attack_time` | 0 |
| `cnt` | 1 |

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

**`radian_s_2[token]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`radian_s_2[token]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 手牵手　`skchr_radian_3`

**技能描述（最高级）：**

> 被动：召唤物可部署在远程位，召唤物找不到攻击目标且可攻击时，可以与其自身范围内其他电弧的召唤物协同攻击
> 开启：自身和召唤物攻击力+150%，对敌人造成伤害时，使敌人受到停顿与35％法术脆弱效果，持续2秒
> 技能开启时获得1个召唤物


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `cnt` | 1 |
| `sluggish` | 2 |
| `attack@sluggish` | 2 |
| `weak[magic][limit]` | 2 |
| `attack@weak[magic][limit]` | 2 |
| `damage_scale` | 1.35 |
| `attack@damage_scale` | 1.35 |

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

**`radian_s_3[token]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **CreateBuff** buffKey=`sluggish` `lifeTimeType`=LIMITED
- **CreateBuff** buffKey=`weak[magic][limit]` `lifeTimeType`=LIMITED

**`radian_s_3[token]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`radian_s_3[token]`** ← 事件 `ON_BUFF_FINISH`

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
