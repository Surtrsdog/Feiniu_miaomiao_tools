# 乌啾 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4224_turdus` |
| 职业 | 医疗 / `chainhealer` |
| 星级 | 5 星 |
| 生命（精二满级） | 1650 |
| 攻击（精二满级） | 440 |
| 防御（精二满级） | 175 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 18 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4224_turdus_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 21.1%（0.6 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2` | 0.6 秒 | 18 帧 |


## 三、技能逐层拆解

---

### 火钳秘咒　`skchr_turdus_1`

**技能描述（最高级）：**

> 攻击速度+80，每次治疗的跳跃次数+1 


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 80 |
| `attack@chain.extra_value` | 1 |

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

### “捉迷藏！”　`skchr_turdus_2`

**技能描述（最高级）：**

> 流失15%当前生命值，立即进行一次治疗，并使目标每秒受到治疗量为35%攻击力的增益治疗，治疗的所有目标获得迷彩，持续12秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `turdus_s2[continues_heal].heal_scale` | 0.35 |
| `bonus_duration` | 12 |
| `turdus_s2[self_damage].hp_ratio` | 0.15 |

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

**`turdus_s2[continues_heal]`** ← 事件 `ON_BUFF_START`

- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_SOURCE"

**`turdus_s2[continues_heal]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="TARGET"

**`turdus_s2[self_damage]`** ← 事件 `ON_BUFF_START`

- **DamageViaCurHpRatio** `_targetType`="TARGET"

**`turdus_s2[try_camouflage]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["turdus_s2[camouflage]"] `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`turdus_s2[camouflage]` `lifeTimeType`=INFINITY

**`turdus_s2[try_camouflage]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
