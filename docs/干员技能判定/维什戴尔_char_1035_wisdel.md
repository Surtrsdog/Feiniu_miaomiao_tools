# 维什戴尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1035_wisdel` |
| 职业 | 狙击 / `bombarder` |
| 星级 | 6 星 |
| 生命（精二满级） | 1888 |
| 攻击（精二满级） | 687 |
| 防御（精二满级） | 256 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **2.1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 25 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.1 ÷ 1.00 = 2.100 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1035_wisdel_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.6 秒** | 18 帧 |

> 占攻击间隔 28.6%（0.6 秒 / 2.1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Overload_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 定点清算　`skchr_wisdel_1`

**技能描述（最高级）：**

> 下次攻击额外造成2次余震并使所有目标晕眩1.5秒，此次攻击的溅射范围略微扩大且余震伤害变为攻击力的120%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `append_atk_scale` | 1.2 |
| `stun_duration` | 1.5 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 饱和复仇　`skchr_wisdel_2`

**技能描述（最高级）：**

> 攻击力+35%，攻击间隔缩短，可同时攻击3名敌人
> 过载：攻击改为攻击力80%的4连发，随机攻击范围内的目标
> 该技能可随时主动关闭


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.7 |
| `atk` | 0.35 |
| `attack@atk_scale_ol` | 0.8 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`wisdel_s_2[overload_start]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
- **PlayAudio** `_target`="BUFF_OWNER"

**`wisdel_s_2[switch]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`wisdel_s_2[switch]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 爆裂黎明　`skchr_wisdel_3`

**技能描述（最高级）：**

> 立刻在攻击范围内召唤2个魂灵之影（最多存在3个，技能结束后保留），攻击力+180%，攻击间隔大幅增大，攻击时攻击力提升至220%，溅射范围大幅扩大且第一天赋的发动概率提高至100%
> 攻击装有6发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 40 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `max_cnt` | 2 |
| `base_attack_time` | 2.9 |
| `attack@atk_scale_3` | 2.2 |
| `attack@prob` | 1 |
| `attack@trigger_time` | 6 |
| `sp` | 3 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`wisdel_s_3[trigger_spawn]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
