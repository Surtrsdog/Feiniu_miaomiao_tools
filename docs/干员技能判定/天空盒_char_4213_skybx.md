# 天空盒 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4213_skybx` |
| 职业 | 狙击 / `skybreaker` |
| 星级 | 5 星 |
| 生命（精二满级） | 1558 |
| 攻击（精二满级） | 899 |
| 防御（精二满级） | 197 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.1 ÷ 1.00 = 2.100 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4213_skybx_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 15.9%（0.333333 秒 / 2.1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Begin` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_2_Close` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.266667 秒 | 8 帧 |


## 三、技能逐层拆解

---

### 源石火药驾临　`skchr_skybx_1`

**技能描述（最高级）：**

> 下次攻击变为投掷源石炸弹，爆炸范围扩大，造成相当于攻击力300%的物理伤害
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |

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

**`skybx_s_1[block_fly]`** ← 事件 `ON_BUFF_FINISH`

- **ChangeCharBlockMode** `_target`="BUFF_OWNER"
- **AlwaysNext** 
- **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"

**`skybx_s_1[block_fly]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`skybx_s_1[block_walk]`** ← 事件 `ON_BUFF_FINISH`

- **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"
- **AlwaysNext** 
- **ChangeCharBlockMode** `_target`="BUFF_OWNER"

---

### 电磁脉冲恩宠　`skchr_skybx_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击时攻击力提升至240%
> 过载：主动关闭时发射剩余全部弹药攻击随机敌人
> 技能拥有10枚弹药，可随时主动关闭


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 2.4 |
| `attack@trigger_time` | 10 |

#### 攻击范围

`rangeId = 3-10`，15 格（direction=1）

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`skybx_s_2[ammo_assign]`** ← 事件 `ON_BUFF_START`

- **AssignAmmoSkillRemainingCountToBB** `_targetType`="BUFF_OWNER"
- **ModifyAbilityBlackboard** 

**`skybx_s_2[counter]`** ← 事件 `ON_BUFF_START`

- **AssignAmmoSkillRemainingCountToBB** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

**`skybx_s_2[finish]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **ChangeCharBlockMode** `_target`="BUFF_OWNER"

**`skybx_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"
- **AssignValueToBB** 

**`skybx_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **ChangeCharBlockMode** `_target`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
