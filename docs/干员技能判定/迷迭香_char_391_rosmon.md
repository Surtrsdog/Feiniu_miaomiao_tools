# 迷迭香 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_391_rosmon` |
| 职业 | 狙击 / `bombarder` |
| 星级 | 6 星 |
| 生命（精二满级） | 1944 |
| 攻击（精二满级） | 688 |
| 防御（精二满级） | 245 |
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

来源：`bakemuzzledata/character/char_391_rosmon_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 25.4%（0.533333 秒 / 2.1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2` | 1.2 秒 | 36 帧 |
| 技能动画 | `Skill_3_Loop` | 0.033333 秒 | 1 帧 |


## 三、技能逐层拆解

---

### 思维膨大　`skchr_rosmon_1`

**技能描述（最高级）：**

> 下次攻击额外造成一次相当于攻击力180%的法术伤害


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
| `extra_atk_scale` | 1.8 |
| `append_atk_scale` | 0.5 |

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

**`rosmon_s_1`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"

---

### 末梢阻断　`skchr_rosmon_2`

**技能描述（最高级）：**

> 攻击间隔增大，攻击力+55%，溅射范围扩大，每次攻击额外造成2次余震；受到攻击和余震的目标有20%的几率晕眩1.5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | 0.5 |
| `atk` | 0.55 |
| `add_times` | 2 |
| `attack@prob` | 0.2 |
| `attack@stun` | 1.5 |

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

**`rosmon_s_2[stun]`** ← 事件 `ON_BUFF_START`

- **Dice** 
- **CreateBuff** buffKey=`stun` `lifeTimeType`=LIMITED

---

### “如你所愿”　`skchr_rosmon_3`

**技能描述（最高级）：**

> 攻击间隔缩短，攻击力+75%，同时攻击2个敌人但仅选择被阻挡的敌人作为目标；立即在攻击范围内的近战位部署两个战术装备（部署后晕眩周围敌人3秒，阻挡的敌人防御力-160）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.5 |
| `atk` | 0.75 |
| `attack@max_target` | 2 |
| `def` | 1 |
| `attack@append_atk_scale` | 0.5 |
| `stun` | 3 |

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

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
