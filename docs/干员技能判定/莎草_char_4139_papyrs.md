# 莎草 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4139_papyrs` |
| 职业 | 医疗 / `chainhealer` |
| 星级 | 5 星 |
| 生命（精二满级） | 1715 |
| 攻击（精二满级） | 440 |
| 防御（精二满级） | 160 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4139_papyrs_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 17.5%（0.5 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 巧思乍现　`skchr_papyrs_1`

**技能描述（最高级）：**

> 下次治疗时的治疗量提升至攻击力的200%，天赋附加屏障效果提升至200%
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
| `heal_scale` | 2 |
| `shield_scale_skill` | 2 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`papyrs_s_1[fx_ctrl]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckSkillIndex** 
- **IfElse** 
  - **CheckCharSkillAvailable** `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["papyrs_s_1[fx_ready]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`papyrs_s_1[fx_ready]` `lifeTimeType`=INFINITY
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 临考发挥　`skchr_papyrs_2`

**技能描述（最高级）：**

> 立刻锁定攻击范围内除自身外生命值上限最高的干员，技能期间莎草仅可以该干员作为治疗主目标，攻击间隔缩短，攻击力+50%，每次治疗跳跃次数+1 


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -1.1 |
| `atk` | 0.5 |
| `attack@chain.extra_value` | 1 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`papyrs_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"
- **CreateBuffUseAbilitySelector** buffKey=`papyrs_s_2[target]` templateKey=`papyrs_s_2[target]` `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"

**`papyrs_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`papyrs_s_2[target]`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitAlive** 
- **InterruptCharacterSkill** `_charFrom`="BUFF_SOURCE"

**`papyrs_s_2[target]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckUnitAlive** 
- **IfNot** 
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
