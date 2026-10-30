# 罗小黑 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4067_lolxh` |
| 职业 | 近卫 / `lord` |
| 星级 | 4 星 |
| 生命（精二满级） | 2040 |
| 攻击（精二满级） | 698 |
| 防御（精二满级） | 325 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4067_lolxh_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 46.2%（0.6 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill2_Attack` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill2_Combat` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Attack` | 0.633333 秒 | 19 帧 |


## 三、技能逐层拆解

---

### 掠光尾影　`skchr_lolxh_1`

**技能描述（最高级）：**

> 可以在下列状态和初始状态间切换：
> 攻击范围改为自身周围4格，攻击速度+40，获得45%的物理闪避，同时攻击阻挡的所有敌人


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `prob` | 0.45 |
| `attack_speed` | 40 |

#### 攻击范围

`rangeId = x-5`，5 格（direction=1）

```
· ■ · 
■ ■ ■ 
· ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 碎金为刃　`skchr_lolxh_2`

**技能描述（最高级）：**

> 攻击力+70%，远程攻击不再降低攻击力，额外攻击一名目标，目标生命值低于一半时额外追加一次无视敌人200防御力的攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.7 |
| `attack@hp_ratio` | 0.5 |
| `attack@def_penetrate_fixed` | 200 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lolxh_s_2[hit]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterByTargetHpRatio** `_condType`="LT" `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`lolxh_s_2[def_penetrate]` 属性修改=[DEF_PENETRATE_FIXED ADDITION blackboard] `lifeTimeType`=INFINITY
  - **AdvancedApplyDamage** `_targetType`="TARGET"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **FinishDerivedBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
