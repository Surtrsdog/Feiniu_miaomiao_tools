# 灵知 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_206_gnosis` |
| 职业 | 辅助 / `underminer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2035 |
| 攻击（精二满级） | 455 |
| 防御（精二满级） | 132 |
| 法抗 | 2500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_206_gnosis_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 29.2%（0.466667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_4_End` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 高速思考　`skchr_gnosis_1`

**技能描述（最高级）：**

> 下次攻击连续攻击两次，每次造成相当于攻击力170%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.7 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 零度爆发　`skchr_gnosis_2`

**技能描述（最高级）：**

> 对范围内所有敌人造成4秒寒冷和相当于攻击力200%的法术伤害；蓄力：额外造成一层寒冷


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 6 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |
| `cold` | 4 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`gnosis_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["gnosis_s_2_enhance_mask"] `_targetType`="BUFF_SOURCE"
  - **IfElse** 
    - **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`c2e_cold` `lifeTimeType`=LIMITED
    - **IfElse** 
      - **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
      - **CreateBuff** buffKey=`c2e_cold` `lifeTimeType`=LIMITED
      - **CreateBuff** buffKey=`c2e_freeze[double_cold]` `lifeTimeType`=LIMITED
  - **CreateBuff** buffKey=`c2e_cold` `lifeTimeType`=LIMITED

**`gnosis_s_2[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="EQUALS" `_count`=1 `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["gnosis_s_2[effect1]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`gnosis_s_2[effect1]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **CheckContainsBuff** `_buffKeys`=["gnosis_s_2[effect2]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=2 `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`gnosis_s_2[effect2]` `lifeTimeType`=INFINITY

---

### 失温症　`skchr_gnosis_3`

**技能描述（最高级）：**

> 攻击速度+130，同时攻击2个敌人；范围内所有敌人的冻结延长至技能结束，且技能结束时对所有冻结的敌人造成600%的法术伤害并结束冻结；优先攻击未冻结的单位


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 13 秒 |
| duration / durationType | 13 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 6 |
| `attack_speed` | 130 |
| `max_target` | 2 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`gnosis_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`gnosis_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`gnosis_s_3`** ← 事件 `ON_SKILL_FINISH`

- **InterruptCharacterAttack** `_charFrom`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`gnosis_s_3[check_freeze]`** ← 事件 `ON_BUFF_START`

- **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
- **CheckContainsDerviedBuff** `_derviedBuffKey`="gnosis_s_3[checked]"
- **IfNot** 
- **CreateBuff** buffKey=`gnosis_s_3[checked]` `lifeTimeType`=INFINITY
- **CreateBuffById** 
- **CreateBuffById** 

**`gnosis_s_3[check_freeze]`** ← 事件 `ON_ABNORMAL_FLAG_DIRTY`

- **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
- **CheckContainsDerviedBuff** `_derviedBuffKey`="gnosis_s_3[checked]"
- **IfNot** 
- **CreateBuff** buffKey=`gnosis_s_3[checked]` `lifeTimeType`=INFINITY
- **CreateBuffById** 
- **CreateBuffById** 

**`gnosis_s_3[clear_freeze]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
