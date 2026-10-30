# 提丰 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_2012_typhon` |
| 职业 | 狙击 / `siegesniper` |
| 星级 | 6 星 |
| 生命（精二满级） | 1702 |
| 攻击（精二满级） | 1045 |
| 防御（精二满级） | 113 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.4 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.4 ÷ 1.00 = 2.400 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_2012_typhon_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.033333 秒** | 1 帧 |

> 占攻击间隔 1.4%（0.033333 秒 / 2.4 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_1_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_2_2_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_3_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_Down_2_1_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_Down_2_2_Loop` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 迅捷打击·γ型　`skcom_quickattack[3]`

**技能描述（最高级）：**

> 攻击力+45%，攻击速度+45


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.45 |
| `attack_speed` | 45 |

#### 攻击范围

`rangeId = 4-3`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 冰原秩序　`skchr_typhon_2`

**技能描述（最高级）：**

> 攻击力+50%，每次攻击发射两支箭矢（优先攻击不同目标），并有40%概率晕眩目标1秒
> 第二次及以后使用时持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 42 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack@prob` | 0.4 |
| `attack@stun` | 1 |
| `first_duration` | 20 |

#### 攻击范围

`rangeId = 4-3`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`typhon_s_2[first_shot]`** ← 事件 `ON_BUFF_START`

- **IfTargetSide** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`typhon_s_2[stun]`** ← 事件 `ON_BUFF_START`

- **Dice** 
- **CreateBuffById** 

**`typhon_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="SOURCE"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`typhon_s_2[trigger_second_shot]`** ← 事件 `ON_BUFF_START`

- **TriggerAbilityUseSelector** `_targetType`="TARGET"

---

### “永恒狩猎”　`skchr_typhon_3`

**技能描述（最高级）：**

> 立刻标记攻击范围内的一名目标，攻击间隔大幅增大，攻击变为对标记目标发射一轮箭雨；箭雨会随机攻击标记目标周围的敌人，共造成5次相当于攻击力175%的物理伤害并使目标晕眩0.4秒
> 攻击装有10发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | 3.1 |
| `attack@s3_stun` | 0.4 |
| `attack@s3_atk_scale` | 1.75 |
| `attack@s3_trigger_time` | 10 |
| `attack@s3_max_hit_num` | 5 |

#### 攻击范围

`rangeId = 4-3`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`typhon_s_3[clear_effect]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`typhon_s_3[effect_ctrl]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`typhon_s_3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **TriggerAbilityUseSelector** `_targetType`="TARGET"

**`typhon_s_3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`typhon_s_3[switch_mode_close]`** ← 事件 `ON_BUFF_FINISH`

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
