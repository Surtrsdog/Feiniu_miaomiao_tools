# 雪绒 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_466_qanik` |
| 职业 | 术师 / `corecaster` |
| 星级 | 5 星 |
| 生命（精二满级） | 1500 |
| 攻击（精二满级） | 625 |
| 防御（精二满级） | 119 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_466_qanik_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.666667 秒** | 20 帧 |

> 占攻击间隔 41.7%（0.666667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_Begin` | 0.2 秒 | 6 帧 |
| 技能动画 | `Skill_Loop` | 0 秒 | 0 帧 |


## 三、技能逐层拆解

---

### 冻风　`skchr_qanik_1`

**技能描述（最高级）：**

> 攻击速度+90，优先攻击空中单位


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 90 |
| `mode` | 1 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 坠雪　`skchr_qanik_2`

**技能描述（最高级）：**

> 使范围内最多2名地面敌人每0.5秒受到一次相当于攻击力75%的法术伤害并浮空7秒，目标浮空结束时会对周围小范围内所有敌人造成相当于攻击力300%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 7 秒 |
| duration / durationType | 7 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target` | 2 |
| `interval` | 0.5 |
| `trigger_atk_scale` | 0.75 |
| `critical_damage_scale` | 3 |
| `levitate_duration` | 7 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`qanik_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="TARGET"

**`qanik_s_2`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["qanik_s_2"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`qanik_s_2[derived]` templateKey=`qanik_s_2[lev]` `lifeTimeType`=LIMITED

**`qanik_s_2[lev]`** ← 事件 `ON_BUFF_FINISH`

- **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, TRAP_OR_ITEM, abnormalFlag=E_NUM)
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
