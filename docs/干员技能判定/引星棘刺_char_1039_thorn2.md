# 引星棘刺 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1039_thorn2` |
| 职业 | 特种 / `alchemist` |
| 星级 | 6 星 |
| 生命（精二满级） | 1173 |
| 攻击（精二满级） | 501 |
| 防御（精二满级） | 106 |
| 法抗 | 3000% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 18 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1039_thorn2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 33.3%（0.5 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_3_Loop` | 0.7 秒 | 21 帧 |


## 三、技能逐层拆解

---

### 度算浪波　`skchr_thorn2_1`

**技能描述（最高级）：**

> 向友方单位投掷一个炼金单元，在8秒内使落点和周围8格的友方单位防御力+100，每秒回复相当于攻击力20%的生命值


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `hp_recovery_per_sec_ratio` | 0.2 |
| `projectile_delay_time` | 8 |
| `def` | 100 |
| `projectile_range` | 0 |

#### 攻击范围

`rangeId = 3-5`，13 格（direction=1）

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

### 解构涌潮　`skchr_thorn2_2`

**技能描述（最高级）：**

> 投掷一个炼金单元，在15秒内使落点周围的地面敌人受到的治疗和回复效果降低50%，每秒受到相当于攻击力180%的法术伤害，友方单位每秒恢复相当于攻击力18%的生命；炼金单元能在15秒内缓慢沿投掷方向移动且影响范围持续扩大
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 0.5 |
| `hp_recovery_per_sec` | -0.5 |
| `hp_recovery_per_sec_by_max_hp_ratio` | -0.5 |
| `projectile_delay_time` | 15 |
| `atk_scale` | 1.8 |
| `value` | 0.13 |
| `projectile_move_speed` | 0.1 |
| `projectile_range` | 1.1 |
| `remaining_time` | 15 |
| `hp_recovery_per_sec_ratio_chr` | 0.18 |

#### 攻击范围

`rangeId = 3-5`，13 格（direction=1）

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

**`thorn2_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **IfTargetSide** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **CreateBuff** buffKey=`thorn2_s_2[buff][ally]` 属性修改=[HP_RECOVERY_PER_SEC ADDITION blackboard] `lifeTimeType`=INFINITY
  - **IfTargetSide** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`thorn2_s2_heal` templateKey=`heal_scale` 属性修改=[HP_RECOVERY_PER_SEC FINAL_SCALER blackboard, HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO FINAL_SCALER blackboard] `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`thorn2_s2_damage` templateKey=`thorn2_s2_damage` `lifeTimeType`=INFINITY

---

### “我的海疆”　`skchr_thorn2_3`

**技能描述（最高级）：**

> 被动效果：攻击范围扩大
> 主动开启：向阻挡数最低的4名干员投掷炼金单元，在23秒内使围绕区域内的敌人攻击力---15%，防御力---35%，法术抗性---35%（不叠加），每秒受到攻击力210%的法术伤害，效果逐渐提升（15秒后达到最大，攻击力---30%，防御力---50%，法术抗性---50%，每秒伤害390%）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 48 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target_token` | 4 |
| `projectile_delay_time` | 23 |
| `max_stack_cnt` | 15 |
| `interval` | 1 |
| `atk_scale` | 2.1 |
| `max_atk_scale` | 3.9 |
| `atk_scale_per_interval` | 0.12 |
| `atk` | -0.15 |
| `max_atk` | -0.3 |
| `atk_per_interval` | -0.01 |
| `def` | -0.35 |
| `max_def` | -0.5 |
| `def_per_interval` | -0.01 |
| `magic_resistance` | -0.35 |
| `max_magic_resistance` | -0.5 |
| `magic_resistance_per_interval` | -0.01 |

#### 攻击范围

`rangeId = 3-9`，19 格（direction=1）

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

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
