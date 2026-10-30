# 褐果 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4041_chnut` |
| 职业 | 医疗 / `wandermedic` |
| 星级 | 4 星 |
| 生命（精二满级） | 1137 |
| 攻击（精二满级） | 389 |
| 防御（精二满级） | 101 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4041_chnut_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.833333 秒** | 25 帧 |

> 占攻击间隔 29.2%（0.833333 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill2_Attack` | 0.633333 秒 | 19 帧 |
| 技能动画 | `Skill2_Down_Attack` | 0.633333 秒 | 19 帧 |
| 技能动画 | `Skill2_Down_End` | 0 秒 | 0 帧 |
| 技能动画 | `Skill2_Down_Start` | 0.166667 秒 | 5 帧 |


## 三、技能逐层拆解

---

### 积微成著　`skchr_chnut_1`

**技能描述（最高级）：**

> 立即进行一次治疗，并且该次治疗元素损伤回复量提升至300%
> 可以充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `trait_scale` | 3 |
| `cnt` | 2 |

#### 攻击范围

`rangeId = 3-17`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chnut_s_1`** ← 事件 `ON_OUTPUT_MODIFIER`

- **IsElementHeal** 
- **ModifierScaleUp** 

---

### 厚土迸发　`skchr_chnut_2`

**技能描述（最高级）：**

> 攻击范围缩小，攻击速度+130，连续治疗同一目标时，治疗量和元素损伤回复量提高至150%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 70 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 130 |
| `attack@heal_continuously_scale` | 1.5 |

#### 攻击范围

`rangeId = 3-2`，4 格（direction=1）

```
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chnut_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`chnut_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **ForceCharacterFaceDefaultDirection** `_target`="TARGET"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
