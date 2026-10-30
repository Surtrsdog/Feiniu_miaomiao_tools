# 戴菲恩 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4110_delphn` |
| 职业 | 术师 / `mystic` |
| 星级 | 5 星 |
| 生命（精二满级） | 1532 |
| 攻击（精二满级） | 1240 |
| 防御（精二满级） | 128 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 26 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 3 ÷ 1.00 = 3.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4110_delphn_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 17.8%（0.533333 秒 / 3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Charge` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2_Loop` | 0.6 秒 | 18 帧 |


## 三、技能逐层拆解

---

### “贯注”　`skchr_delphn_1`

**技能描述（最高级）：**

> 攻击范围改变，攻击间隔大幅度缩短，每次攻击造成相当于攻击力50%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 5 秒 |
| duration / durationType | 5 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 0.5 |
| `base_attack_time` | 0.2 |

#### 攻击范围

`rangeId = 4-1`，5 格（direction=1）

```
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`delphn_s_1[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`delphn_s_1[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckConatinsMapTags** 
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### “抢攻”　`skchr_delphn_2`

**技能描述（最高级）：**

> 攻击力+100%，不再以生命值低于50%的敌人为目标，攻击会使命中目标每秒受到6%戴菲恩攻击力的法术伤害（最多叠加4次，持续至技能结束）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `max_cnt` | 0.24 |
| `attack@max_cnt` | 0.24 |
| `damage_addition` | 0.06 |
| `attack@damage_addition` | 0.06 |

#### 攻击范围

`rangeId = 3-14`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`delphn_s_2[cnt]`** ← 事件 `ON_BUFF_START`

- **AddBuffBlackboard** `_targetType`="TARGET"

**`delphn_s_2[damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IfTargetSide** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
    - **AdvancedApplyDamage** `_targetType`="TARGET"
    - **AlwaysNext** 
    - **CreateBuff** buffKey=`delphn_dot_audio_s2` `lifeTimeType`=IMMEDIATELY
    - **CreateEffect** `_targetType`="TARGET"
    - **FinishBuff** 
  - **FinishBuff** 

**`delphn_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckSkillIndex** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
  - **IfNot** 
  - **FinishBuff** 
  - **FinishBuff** 
- **IfTargetSide** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`delphn_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`delphn_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckConatinsMapTags** 
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
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
