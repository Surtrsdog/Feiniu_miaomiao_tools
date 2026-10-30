# 圣约送葬人 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1032_excu2` |
| 职业 | 近卫 / `reaper` |
| 星级 | 6 星 |
| 生命（精二满级） | 2491 |
| 攻击（精二满级） | 707 |
| 防御（精二满级） | 461 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1032_excu2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.3 秒** | 9 帧 |

> 占攻击间隔 23.1%（0.3 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack_A` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2_Attack_B` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Attack_A` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Attack_B` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_End` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_2_Attack_A` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_Down_2_Attack_B` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_3_Attack_A` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_Down_3_Attack_B` | 0.266667 秒 | 8 帧 |


## 三、技能逐层拆解

---

### 遗嘱执行　`skchr_excu2_1`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+50%，攻击时无视目标400的防御力
> 攻击装有8发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | 0 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `def_penetrate_fixed` | 400 |
| `attack@trigger_time` | 8 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`excu2_s_1`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`excu2_s_1`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 近身铳斗　`skchr_excu2_2`

**技能描述（最高级）：**

> 攻击力+80%，防御力+80%，阻挡数+1，受到敌人的近战攻击时有40%几率闪避并补充1颗弹药
> 攻击装有12发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 6 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | 0 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `def` | 0.8 |
| `block_cnt` | 1 |
| `prob` | 0.4 |
| `recover_cnt` | 1 |
| `attack@trigger_time` | 12 |

#### 攻击范围

`rangeId = 1-3`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ 
■ ■ 
· ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`excu2_s_2`** ← 事件 `ON_TAKE_DAMAGE`

- **IfTargetSide** `_targetType`="MODIFIER_SOURCE"
- **Evade** 
- **AmmoSkillCountModifier** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`excu2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`excu2_s_2`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 圣约决裁　`skchr_excu2_3`

**技能描述（最高级）：**

> 攻击间隔略微增大，攻击范围扩大，攻击力+180%，每消耗1颗弹药攻击力额外+6%（最多30层），特性的回复生命效果提高至3倍；技能结束时，对技能期间攻击过的目标造成相当于攻击力250%的物理伤害
> 攻击装有16发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 12 / 24 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | 0 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `attack@atk` | 0.06 |
| `trait_ratio` | 3 |
| `attack@final_atk_scale` | 2.5 |
| `base_attack_time` | 0.5 |
| `attack@trigger_time` | 16 |
| `attack@max_stack_cnt` | 30 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`excu2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"

**`excu2_s_3`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **CreateBuff** buffKey=`excu2_s_3[trait]` templateKey=`excu2_s_3[trait]` 属性修改=[ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`excu2_s_3[mark][effect]` templateKey=`excu2_s_3[mark][effect]` `lifeTimeType`=INFINITY

**`excu2_s_3[end][during]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`excu2_s_3[end][spell]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`excu2_s_3[mark][effect]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **CreateBuff** buffKey=`excu2_s_3[mark]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`excu2_s_3[mark][end]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="TARGET"

**`excu2_s_3[trait]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="TARGET"
- **AssignBuffBlackboardFromOthers** `_targetType`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **AssignBuffBlackboard** `_targetType`="TARGET"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`excu2_s_3[effect][b]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`excu2_s_3[effect][f]` `lifeTimeType`=INFINITY

**`excu2_s_3[trait]`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
