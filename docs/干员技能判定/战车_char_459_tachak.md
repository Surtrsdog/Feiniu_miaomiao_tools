# 战车 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_459_tachak` |
| 职业 | 近卫 / `sword` |
| 星级 | 5 星 |
| 生命（精二满级） | 2626 |
| 攻击（精二满级） | 621 |
| 防御（精二满级） | 309 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_459_tachak_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 25.6%（0.333333 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.866667 秒 | 26 帧 |


## 三、技能逐层拆解

---

### 燃烧榴弹　`skchr_tachak_1`

**技能描述（最高级）：**

> 发射燃烧榴弹在目标周围四格产生6秒的燃烧区域，范围内的地面敌人每秒受到相当于战车攻击力70%的法术伤害；战车攻击燃烧范围内目标时无视其200的防御力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `projectile_delay_time` | 6 |
| `atk_scale` | 0.7 |
| `def_penetrate_fixed` | 200 |
| `interval` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tachak_s_1[def_penetrate_fixed]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["tachak_s_1[mark]"] `_targetType`="TARGET"
- **CreateBuff** buffKey=`tachak_s_1[def_penetrate_fixed_mode]` 属性修改=[DEF_PENETRATE_FIXED ADDITION blackboard] `lifeTimeType`=INFINITY

**`tachak_s_1[def_penetrate_fixed]`** ← 事件 `ON_AFTER_OUTPUT_DAMAGE`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`tachak_s_1[def_penetrate_fixed]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 倾泻弹药　`skchr_tachak_2`

**技能描述（最高级）：**

> 攻击间隔大幅度缩短，随机攻击范围内的目标，每次攻击有15%的概率攻击力提升至200%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 4 秒 |
| duration / durationType | 4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.85 |
| `prob` | 0.15 |
| `atk_scale` | 2 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tachak_s_2[signal]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **CreateBuff** buffKey=`tachak_s_2[release_projectile]` `lifeTimeType`=IMMEDIATELY

**`tachak_s_2[speed_up_random_attack_up]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **Dice** 
- **AtkScaleUp** 

**`tachak_s_2[speed_up_random_attack_up]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuff** buffKey=`tachak_s_2[buff_end]` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
