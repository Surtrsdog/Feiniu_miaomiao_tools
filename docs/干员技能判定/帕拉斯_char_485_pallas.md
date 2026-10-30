# 帕拉斯 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_485_pallas` |
| 职业 | 近卫 / `instructor` |
| 星级 | 6 星 |
| 生命（精二满级） | 1963 |
| 攻击（精二满级） | 687 |
| 防御（精二满级） | 455 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_485_pallas_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 44.4%（0.466667 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_02` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_02_Down` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_03_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_03_Loop_Down` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 胜利的连击　`skchr_pallas_1`

**技能描述（最高级）：**

> 下次攻击造成相当于攻击力175%的物理伤害，并连续攻击两次


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
| `atk_scale` | 1.75 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 信念的长鞭　`skchr_pallas_2`

**技能描述（最高级）：**

> 攻击范围向前延伸一格，攻击力+80%，每次攻击有85%几率使目标晕眩0.2秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `ability_range_forward_extend` | 1 |
| `attack@buff_prob` | 0.85 |
| `attack@stun` | 0.2 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 英勇的祝福　`skchr_pallas_3`

**技能描述（最高级）：**

> 攻击力+100%，额外攻击两个目标，身前一格为近战位并部署我方干员时使其获得以下增益：生命值高于80%获得+50%攻击力的精力充沛、防御力+35%、阻挡数+1（若身前一格不存在干员或不为近战位时，该效果由自身获得）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@max_target` | 3 |
| `attack@peak_performance.atk` | 0.5 |
| `attack@def` | 0.35 |
| `attack@peak_performance.hp_ratio` | 0.8 |
| `attack@block_cnt` | 1 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`pallas_s_3[peak]`** ← 事件 `ON_BUFF_START`

- **CheckEntityEquals** 
- **IfNot** 
- **IfElse** 
  - **CheckHeightTypeOfRootTile** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`pallas_s_3[peak][stop]` `lifeTimeType`=INFINITY
  - **FinishBuff** 

**`pallas_s_3[peak]`** ← 事件 `ON_BUFF_ENABLE`

- **CreateBuff** buffKey=`peak_performance[inf]` `lifeTimeType`=LIMITED
- **CreateBuff** buffKey=`pallas_s_3[effect]` `lifeTimeType`=INFINITY

**`pallas_s_3[peak]`** ← 事件 `ON_BUFF_DISABLE`

- **FinishDerivedBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
