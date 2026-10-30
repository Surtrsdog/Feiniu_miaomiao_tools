# 熔泉 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_363_toddi` |
| 职业 | 狙击 / `siegesniper` |
| 星级 | 5 星 |
| 生命（精二满级） | 1667 |
| 攻击（精二满级） | 954 |
| 防御（精二满级） | 123 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.4 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.4 ÷ 1.00 = 2.400 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_363_toddi_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **1.36667 秒** | 41 帧 |

> 占攻击间隔 56.9%（1.36667 秒 / 2.4 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 1.36667 秒 | 41 帧 |
| 技能动画 | `Skill_2_Loop` | 1.63333 秒 | 49 帧 |


## 三、技能逐层拆解

---

### 信号矢　`skchr_toddi_1`

**技能描述（最高级）：**

> 立即标记一个敌方单位（优先重量较重的萨卡兹种族敌人）使其更容易受到我方的攻击且防御力-30%。每次攻击造成相当于攻击力180%的物理伤害。


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 1.8 |
| `def` | -0.3 |
| `taunt_level` | 1 |

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

### 便携破城矢　`skchr_toddi_2`

**技能描述（最高级）：**

> 攻击间隔稍微延长，发射龙矢对敌人造成相当于攻击力240%的物理伤害，击中目标后稍微延迟爆炸，对目标以及周围敌人造成相当于攻击力80%的物理伤害
> 攻击装有10发弹药，打完后技能结束（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | 0 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | 0.3 |
| `attack@atk_scale` | 2.4 |
| `attack@splash_atk_scale` | 0.8 |
| `attack@trigger_time` | 10 |
| `attack@splash_projectile_delay_time` | 1.5 |

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

**`toddi_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
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
