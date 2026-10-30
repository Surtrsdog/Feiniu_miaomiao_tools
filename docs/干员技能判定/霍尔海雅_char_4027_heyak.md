# 霍尔海雅 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4027_heyak` |
| 职业 | 术师 / `corecaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1770 |
| 攻击（精二满级） | 633 |
| 防御（精二满级） | 130 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4027_heyak_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 25.0%（0.4 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Loop` | 0.866667 秒 | 26 帧 |


## 三、技能逐层拆解

---

### 但为求索　`skchr_heyak_1`

**技能描述（最高级）：**

> 下次攻击额外攻击一个目标并造成相当于攻击力300%的法术伤害，仅攻击到1名目标时使其浮空4秒
> 可充能3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 7 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3 |
| `levitate` | 4 |
| `cnt` | 3 |

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

**`heyak_s_1`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["heyak_s_1[mark]"] `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`heyak_s_1[levitate]` `overrideType`=EXTEND `lifeTimeType`=LIMITED

---

### 群星逶迤　`skchr_heyak_2`

**技能描述（最高级）：**

> 攻击变为攻击力45%的9连发，随机攻击范围内的目标，每发有15%的概率使目标浮空1秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 0.45 |
| `attack@prob` | 0.15 |
| `attack@levitate` | 1 |

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

**`heyak_s_2[hit_levitate]`** ← 事件 `ON_BUFF_START`

- **Dice** 
- **CheckAbnormalImmune** `_targetType`="TARGET"
- **CreateBuff** buffKey=`heyak_s[levitate]` `overrideType`=EXTEND `lifeTimeType`=LIMITED

---

### 博览者的狂语　`skchr_heyak_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击间隔延长，攻击变为向前吹出平行的旋风，旋风伤害随行进距离正比增强并在行进三格后达到最大，使命中的第一个目标浮空2.2秒，并造成最高420%攻击力的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 45 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 45 秒 |
| duration / durationType | 45 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@min_atk_scale` | 2.8 |
| `attack@max_atk_scale` | 4.2 |
| `attack@levitate` | 2.2 |
| `base_attack_time` | 1.4 |

#### 攻击范围

`rangeId = 3-10`，15 格（direction=1）

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`heyak_s_3[hit_levitate]`** ← 事件 `ON_BUFF_START`

- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`heyak_s[levitate]` `overrideType`=EXTEND `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
