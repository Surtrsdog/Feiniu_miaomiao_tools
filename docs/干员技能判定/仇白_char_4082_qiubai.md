# 仇白 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4082_qiubai` |
| 职业 | 近卫 / `lord` |
| 星级 | 6 星 |
| 生命（精二满级） | 2480 |
| 攻击（精二满级） | 718 |
| 防御（精二满级） | 402 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4082_qiubai_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 38.5%（0.5 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Loop` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 留羽　`skchr_qiubai_1`

**技能描述（最高级）：**

> 下次攻击使目标束缚3秒，该次束缚结束时对目标和附近的所有敌人造成相当于攻击力300%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `aoe_scale` | 3 |
| `duration` | 3 |

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

**`qiubai_s_1[aoe]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
  - **EmitProjectile** `_targetType`="BUFF_OWNER"
  - **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **CreateBuff** buffKey=`qiubai_s_1[aoe_audio]` `lifeTimeType`=IMMEDIATELY

**`qiubai_s_1[unmovable_effect]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`qiubai_unmovable[effect]` `lifeTimeType`=LIMITED

---

### 承影　`skchr_qiubai_2`

**技能描述（最高级）：**

> 对前方范围内的地面敌人造成攻击力300%的法术伤害；攻击范围改变，攻击力+140%，攻击范围内的地面敌人停顿；技能结束时对范围内的地面敌人造成攻击力300%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 5 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 5 秒 |
| duration / durationType | 5 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `sword_begin_atk_scale` | 3 |
| `sword_end_atk_scale` | 3 |
| `atk` | 1.4 |
| `sword_end_duration` | 4.88 |

#### 攻击范围

`rangeId = 4-1`，5 格（direction=1）

```
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`qiubai_s_2[end_damage]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`qiubai_s_2[end_sword_wind]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuffUseAbilitySelector** buffKey=`qiubai_skill_2[end_damage]` templateKey=`qiubai_s_2[end_damage]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_SOURCE"

**`qiubai_s_2[end_sword_wind]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`qiubai_s_2[atk_buff]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY

**`qiubai_s_2[sword_wind_effect]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`qiubai_skill_2[up_effect]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
    - **CreateBuff** buffKey=`qiubai_skill_2[down_effect]` `lifeTimeType`=INFINITY
    - **IfElse** 
      - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
      - **CreateBuff** buffKey=`qiubai_skill_2[right_effect]` `lifeTimeType`=INFINITY
      - **CreateBuff** buffKey=`qiubai_skill_2[left_effect]` `lifeTimeType`=INFINITY

---

### 问雪　`skchr_qiubai_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+55%，伤害类型变为法术，额外攻击2个目标，第一天赋的伤害提升至2倍，远程攻击不再降低伤害，每次攻击使自身攻击速度+13（最多叠加8次）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 45 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.55 |
| `attack_speed` | 13 |
| `max_stack_cnt` | 8 |
| `talent_scale` | 2 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`qiubai_s_3[atk_speed]`** ← 事件 `ON_AFTER_ATTACK`

- **CreateBuff** buffKey=`qiubai_skill_3[stack]` 属性修改=[ATTACK_SPEED ADDITION blackboard] `overrideType`=STACK `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
