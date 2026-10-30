# 艾丽妮 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4009_irene` |
| 职业 | 近卫 / `sword` |
| 星级 | 6 星 |
| 生命（精二满级） | 2935 |
| 攻击（精二满级） | 621 |
| 防御（精二满级） | 349 |
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

来源：`bakemuzzledata/character/char_4009_irene_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 35.9%（0.466667 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Attack` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Start` | 0.133333 秒 | 4 帧 |


## 三、技能逐层拆解

---

### 起风　`skchr_irene_1`

**技能描述（最高级）：**

> 下一次攻击对目标造成相当于攻击力200%的物理伤害并使其浮空1秒，再对其追加一次相当于攻击力200%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |
| `levitate` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 裂潮　`skchr_irene_2`

**技能描述（最高级）：**

> 对前方范围内最多6名地面敌人造成相当于攻击力400%的物理伤害并使其中重量小于等于3的目标浮空4秒
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 6 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4 |
| `levitate` | 4 |
| `max_target` | 6 |
| `value` | 3 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`irene_s_2[levitate]`** ← 事件 `ON_BUFF_START`

- **FilterByTargetMassLevel** `_condType`="LE" `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`irene_s_2_levitate` `lifeTimeType`=LIMITED

---

### 判决　`skchr_irene_3`

**技能描述（最高级）：**

> 对周围所有地面敌人造成相当于攻击力300%的物理伤害并使其浮空4秒，然后快速轰击12次，每次对随机目标周围小范围内所有敌人造成相当于攻击力250%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 16 / 24 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `levitate` | 4 |
| `multi_atk_scale` | 2.5 |
| `multi_times` | 12 |
| `multi_hit_interval` | 0.25 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
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
