# Touch — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_613_acmedc` |
| 职业 | 医疗 / `physician` |
| 星级 | 6 星 |
| 生命（精二满级） | 1360 |
| 攻击（精二满级） | 525 |
| 防御（精二满级） | 145 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 19 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_613_acmedc_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.366667 秒** | 11 帧 |

> 占攻击间隔 12.9%（0.366667 秒 / 2.85 秒）。开技能不会让抬手变快。



## 三、技能逐层拆解

---

### 慨赠　`skchr_acmedc_1`

**技能描述（最高级）：**

> 攻击力+60%，每次治疗有50%概率额外治疗一次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `attack@prob` | 0.5 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`acmedc_s_1`** ← 事件 `ON_BUFF_START`

- **RandomAction** 
  - **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"

---

### 宛如天启　`skchr_acmedc_2`

**技能描述（最高级）：**

> 自身攻击距离+1，每次治疗2个目标，所有医疗干员攻击力+40%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk` | 0.4 |
| `mode` | 2 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = 3-10`，15 格（direction=1）

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 恳切福音　`skchr_acmedc_3`

**技能描述（最高级）：**

> 自身攻击距离+2，攻击力+40%，每次治疗2个目标，并额外治疗一次目标或目标相邻1个友方单位，治疗量为主目标的30%。对生命值不高于一半的友方单位治疗量提高为原来的150%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 50 / 70 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.4 |
| `mode` | 3 |
| `attack@max_target` | 2 |
| `heal_scale` | 1.5 |
| `hp_ratio` | 0.5 |
| `attack@addition_heal_scale` | 0.3 |

#### 攻击范围

`rangeId = 5-2`，18 格（direction=1）

```
■ ■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`acmedc_s_3[heal]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"

**`acmedc_s_3[heal_trigger]`** ← 事件 `ON_BUFF_START`

- **TriggerAbilityUseSelectorMergeBB** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
