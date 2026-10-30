# 蕾缪安 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4193_lemuen` |
| 职业 | 狙击 / `longrange` |
| 星级 | 6 星 |
| 生命（精二满级） | 1448 |
| 攻击（精二满级） | 1201 |
| 防御（精二满级） | 175 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.7 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 22 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.7 ÷ 1.00 = 2.700 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4193_lemuen_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.166667 秒** | 5 帧 |

> 占攻击间隔 6.2%（0.166667 秒 / 2.7 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2_End` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_3_End` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.166667 秒 | 5 帧 |


## 三、技能逐层拆解

---

### 重逢问候　`skchr_lemuen_1`

**技能描述（最高级）：**

> 攻击时攻击力提升至210%，额外攻击1名敌人
> 攻击装有6发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 2.1 |
| `attack@trigger_time` | 6 |

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

### 归乡邀约　`skchr_lemuen_2`

**技能描述（最高级）：**

> 攻击速度+80，攻击力+70%，场上有被通缉敌人时会消耗子弹对其瞄准最多3.5秒后进行无视闪避的狙击（期间攻击力从180%逐渐提升至425%，攻击力高于敌人剩余生命值和防御力之和时停止瞄准并立刻攻击）
> 攻击装有7发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 80 |
| `atk` | 0.7 |
| `attack@trigger_time` | 7 |
| `attack@aim_duration` | 3.5 |
| `attack@trig_cnt` | 14 |
| `attack@interval` | 0.25 |
| `attack@ex_atk_scale` | 0.175 |
| `attack@main_atk_scale` | 1.8 |
| `attack@fin_atk_scale` | 4.25 |

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

### 礼炮·强制追思　`skchr_lemuen_3`

**技能描述（最高级）：**

> 停止攻击，每0.5秒消耗1发子弹依次锁定敌人，技能结束时对每名被锁定的敌人所在位置进行轰炸，轰炸造成攻击力300%的范围物理伤害（中心伤害提升至攻击力的450%）
> 攻击装有5发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 32 / 38 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@trigger_time` | 5 |
| `attack@projectile_range` | 1.5 |
| `attack@aim_interval` | 0.5 |
| `attack@emit_offset` | 0.2 |
| `attack@proj_atk_scale_1` | 4.5 |
| `attack@dist_1` | 0.8 |
| `attack@proj_atk_scale_2` | 3 |
| `attack@dist_2` | 1.5 |
| `attack@limited_hit_time` | 1 |

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

**`lemuen_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`lemuen_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"

**`lemuen_s_3`** ← 事件 `ON_OWNER_FINISH`

- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"

**`lemuen_s_3`** ← 事件 `ON_ABILITY_CAST_ON_TARGET`

- **CreateBuff** buffKey=`lemuen_s3_audio_triggered` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
