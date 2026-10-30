# 隐德来希 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4010_etlchi` |
| 职业 | 近卫 / `reaper` |
| 星级 | 6 星 |
| 生命（精二满级） | 2580 |
| 攻击（精二满级） | 700 |
| 防御（精二满级） | 452 |
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

来源：`bakemuzzledata/character/char_4010_etlchi_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 30.8%（0.4 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Loop_A` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_3_Loop_B` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 玫影觅迹　`skchr_etlchi_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至175%，并连续攻击两次


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
| `atk_scale` | 1.75 |

#### 攻击范围

`rangeId = 1-3`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ 
■ ■ 
· ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 绯红壁合　`skchr_etlchi_2`

**技能描述（最高级）：**

> 停止攻击，在自身及1名其他地面单位处召唤血镰，对周围所有敌人进行切割，每0.5秒造成相当于攻击力195%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.95 |
| `interval` | 0.5 |

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

**`etlchi_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IfTarget** `_targetType`="SOURCE"
  - **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **CheckBlockMode** `_targetType`="BUFF_OWNER"
  - **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=FLY_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **FinishBuff** 

**`etlchi_s_2[aura]`** ← 事件 `ON_BUFF_DISABLE`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 灵与欲的惜别　`skchr_etlchi_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+135%，攻击速度+100，立刻为攻击范围内最多3名生命值最高的地面敌人召唤对应的心烛，每次攻击对心烛至少造成35%攻击力的伤害，心烛继承原敌人当前60%的生命值，被攻击时原敌人也会流失同等生命值
> 心烛只受隐德来希攻击的影响


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 22 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.35 |
| `attack_speed` | 100 |
| `attack@max_target` | 3 |
| `attack@max_hp_scale` | 0.6 |
| `attack@def_scale` | 1 |
| `attack@magic_resistance_scale` | 1 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`etlchi_s_3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`etlchi_s_3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuffUseAbilitySelector** buffKey=`stlchi_s3[skill_end_kill_entlec]` templateKey=`stlchi_s3[skill_end_kill_entlec]` `lifeTimeType`=IMMEDIATELY `_targetType`="TARGET"
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
