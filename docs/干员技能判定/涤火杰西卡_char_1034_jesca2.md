# 涤火杰西卡 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1034_jesca2` |
| 职业 | 重装 / `shotprotector` |
| 星级 | 6 星 |
| 生命（精二满级） | 3608 |
| 攻击（精二满级） | 522 |
| 防御（精二满级） | 716 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1034_jesca2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.066667 秒** | 2 帧 |

> 占攻击间隔 5.6%（0.066667 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.066667 秒 | 2 帧 |
| 技能动画 | `Skill_2_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_3_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_3_Skill` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.066667 秒 | 2 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.033333 秒 | 1 帧 |
| 技能动画 | `Skill_Down_3_Skill` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 坚守阵线　`skchr_jesca2_1`

**技能描述（最高级）：**

> 攻击力+70%，自身与机动盾牌防御力+70%，机动盾牌持续时间+30秒
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 70 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 0.7 |
| `atk` | 0.7 |
| `duration` | 30 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`jesca2_s_1[trigger]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`jesca2_s_1[trigger]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

---

### 掩蔽护卫　`skchr_jesca2_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+75%，攻击间隔大幅缩小，获得75%的物理和法术闪避


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.75 |
| `base_attack_time` | -0.9 |
| `prob` | 0.75 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 饱和迸射　`skchr_jesca2_3`

**技能描述（最高级）：**

> 攻击距离+1，攻击间隔增大，攻击力+310%，防御力+80%，机动盾牌防御力+170%
> 机动盾牌存在时，立刻向前发射一枚炮弹，命中或到达终点时对范围内所有敌人造成相当于攻击力250%的物理伤害，并使其晕眩6秒
> 攻击装有20发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 3.1 |
| `jesca2_s_3_token[def].def` | 1.7 |
| `ability_range_forward_extend` | 1 |
| `base_attack_time` | 0.6 |
| `attack@extrabomb.stun` | 6 |
| `attack@extrabomb.atk_scale` | 2.5 |
| `attack@trigger_time` | 20 |
| `attack@extrabomb.projectile_range` | 1.7 |
| `jesca2_s_3[def].def` | 0.8 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`jesca2_s_3[bomb]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckAbnormalCombo** `_targetType`="BUFF_OWNER"
    - **InterruptCharacterAttack** `_charFrom`="BUFF_OWNER"
    - **AlwaysNext** 
    - **CreateBuff** buffKey=`jesca2_s_3_trigger[extra_bomb]` `lifeTimeType`=INFINITY
    - **FinishBuff** 

**`jesca2_s_3[explosion]`** ← 事件 `ON_BUFF_START`

- **EmitProjectile** `_targetType`="BUFF_OWNER"
  - **AdvancedApplyDamage** `_targetType`="TARGET"

**`jesca2_s_3[switch]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["jesca2_jckshd_s_3[mark]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`jesca2_s_3[bomb]` templateKey=`jesca2_s_3[bomb]` `lifeTimeType`=INFINITY
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`jesca2_s_3[switch]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **InterruptAbility** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`jesca2_s_3[switch]`** ← 事件 `ON_DIRECTION_CHANGED`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`jesca2_s_3[trigger]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["jesca2_jckshd_s_3[mark]"] `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`jesca2_s_3[bomb]` templateKey=`jesca2_s_3[bomb]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`jesca2_s_3[bomb]` templateKey=`jesca2_s_3[bomb]` `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
