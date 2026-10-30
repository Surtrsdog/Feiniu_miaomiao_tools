# 伯塔尼 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4223_botany` |
| 职业 | 辅助 / `ritualist` |
| 星级 | 5 星 |
| 生命（精二满级） | 1080 |
| 攻击（精二满级） | 461 |
| 防御（精二满级） | 108 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4223_botany_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.8 秒 | 24 帧 |
| 技能动画 | `Skill_2_Loop` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 谐波破坏　`skchr_botany_1`

**技能描述（最高级）：**

> 下一次攻击造成相当于攻击力110%的法术伤害并附带100%攻击力的侵蚀损伤；若目标未受到侵蚀损伤，则额外造成相当于攻击力50%的法术伤害并附带35%攻击力的的侵蚀损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.1 |
| `ep_damage_ratio` | 1 |
| `botany_s1_extra.atk_scale` | 0.5 |
| `botany_s1_extra.ep_damage_ratio` | 0.35 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`botany_s1_extra`** ← 事件 `ON_BUFF_START`

- **CheckTargetEpIsFull** `_targetType`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 静域回声　`skchr_botany_2`

**技能描述（最高级）：**

> 攻击范围扩大，同时攻击2个目标，每次攻击额外附带相当于攻击力150%的物理伤害和攻击力65%的侵蚀损伤，范围内敌人侵蚀损伤冷却恢复速度+25%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@extra_atk_scale` | 1.5 |
| `attack@ep_damage_ratio` | 0.65 |
| `attack@ep_break_recover_speed` | 0.25 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

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

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
