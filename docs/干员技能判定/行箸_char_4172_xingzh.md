# 行箸 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4172_xingzh` |
| 职业 | 辅助 / `blessing` |
| 星级 | 5 星 |
| 生命（精二满级） | 1746 |
| 攻击（精二满级） | 423 |
| 防御（精二满级） | 181 |
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

来源：`bakemuzzledata/character/char_4172_xingzh_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 37.5%（0.6 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_2_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 盈帙满笥　`skchr_xingzh_1`

**技能描述（最高级）：**

> 立即对攻击范围内的所有目标进行一次治疗，回复量为行箸攻击力的330%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 3.3 |

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

**`xingzh_s_1`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyHeal** `_targetType`="TARGET"

---

### 食不厌精　`skchr_xingzh_2`

**技能描述（最高级）：**

> 攻击速度+50，额外治疗1名目标，且每秒恢复天赋生效目标相当于行箸攻击力20%的生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 60 / 75 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 50 |
| `attack@max_target` | 2 |
| `attack@xingzh_s_2[heal].interval` | 1 |
| `attack@xingzh_s_2[heal].atk_to_hp_recovery_ratio` | 0.2 |

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

**`xingzh_s_2[heal]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
