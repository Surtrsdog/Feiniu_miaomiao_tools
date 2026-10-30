# 格劳克斯 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_326_glacus` |
| 职业 | 辅助 / `slower` |
| 星级 | 5 星 |
| 生命（精二满级） | 1267 |
| 攻击（精二满级） | 505 |
| 防御（精二满级） | 100 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.9 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 15 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.9 ÷ 1.00 = 1.900 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_326_glacus_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.633333 秒** | 19 帧 |

> 占攻击间隔 33.3%（0.633333 秒 / 1.9 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.833333 秒 | 25 帧 |


## 三、技能逐层拆解

---

### 双线装填　`skchr_glacus_1`

**技能描述（最高级）：**

> 攻击力+50%，额外攻击一个目标


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack@max_target` | 2 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 反制电磁脉冲　`skchr_glacus_2`

**技能描述（最高级）：**

> 向周围发射一道冲击波，击中的所有敌人受到攻击力400%的法术伤害并束缚6秒；如果目标是【无人机】，受到的伤害加倍并将效果改为晕眩


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale[drone]` | 8 |
| `atk_scale[normal]` | 4 |
| `frozen` | 6 |
| `stun` | 6 |

#### 攻击范围

`rangeId = x-3`，25 格（direction=1）

```
· · · ■ · · · 
· · ■ ■ ■ · · 
· ■ ■ ■ ■ ■ · 
■ ■ ■ ■ ■ ■ ■ 
· ■ ■ ■ ■ ■ · 
· · ■ ■ ■ · · 
· · · ■ · · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`glacus_s_2[drone]`** ← 事件 `ON_BUFF_FINISH`

- **CheckFilterTag** `_targetType`="TARGET"
- **CreateBuff** buffKey=`glacus_s2_stun` `lifeTimeType`=LIMITED

**`glacus_s_2[normal]`** ← 事件 `ON_BUFF_FINISH`

- **CheckFilterTag** `_targetType`="TARGET"
- **IfNot** 
- **CreateBuff** buffKey=`glacus_s2_frozen` `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
