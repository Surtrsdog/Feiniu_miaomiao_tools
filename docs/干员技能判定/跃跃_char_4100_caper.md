# 跃跃 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4100_caper` |
| 职业 | 狙击 / `loopshooter` |
| 星级 | 4 星 |
| 生命（精二满级） | 2200 |
| 攻击（精二满级） | 600 |
| 防御（精二满级） | 160 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4100_caper_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 53.3%（0.533333 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_Down_Loop` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_Loop` | 0.366667 秒 | 11 帧 |


## 三、技能逐层拆解

---

### 强力击·β型　`skchr_caper_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提高至230%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.3 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`caper_s_1[effect_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByTargetSpRatio** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`caper_s_1[effect]` `lifeTimeType`=INFINITY
  - **FinishDerivedBuff** 

---

### 乐趣加倍　`skchr_caper_2`

**技能描述（最高级）：**

> 攻击力+60%，每次攻击额外发射1个回旋投射物


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `cnt` | 2 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`caper_s_2`** ← 事件 `ON_BUFF_START`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`caper_s_2`** ← 事件 `ON_BUFF_DISABLE`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
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
