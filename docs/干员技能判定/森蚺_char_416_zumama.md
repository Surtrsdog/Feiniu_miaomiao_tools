# 森蚺 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_416_zumama` |
| 职业 | 重装 / `duelist` |
| 星级 | 6 星 |
| 生命（精二满级） | 4468 |
| 攻击（精二满级） | 1007 |
| 防御（精二满级） | 615 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 33 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_416_zumama_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 29.2%（0.466667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.633333 秒 | 19 帧 |
| 技能动画 | `Skill_2_Loop` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_2_Loop_Down` | 0.566667 秒 | 17 帧 |


## 三、技能逐层拆解

---

### 轻型挂斧　`skchr_zumama_1`

**技能描述（最高级）：**

> 攻击力+25%，防御力+25%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 0.25 |
| `atk` | 0.25 |

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

### 震慑劈砍　`skchr_zumama_2`

**技能描述（最高级）：**

> 攻击间隔略微增大，攻击力+180%，技能期间持续使阻挡的敌人全部晕眩


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 28 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 18 秒 |
| duration / durationType | 18 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `base_attack_time` | 0.4 |

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

### 钢铁意志　`skchr_zumama_3`

**技能描述（最高级）：**

> 攻击力+230%，防御力+160%，阻挡数+2，每秒恢复6%生命
> 技能结束后自身晕眩5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.3 |
| `def` | 1.6 |
| `block_cnt` | 2 |
| `hp_recovery_per_sec_by_max_hp_ratio` | 0.06 |
| `stun` | 5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`zumama_s_3`** ← 事件 `ON_BUFF_START`

- **ForceCharacterAnimatorFaceFront** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`zumama_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **ForceCharacterAnimatorFaceFront** 
- **CreateBuffById** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`zumama_s_3[buff]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`zumama_s_3[buff]` 属性修改=[ATK MULTIPLIER blackboard, DEF MULTIPLIER blackboard, BLOCK_CNT ADDITION blackboard, HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO ADDITION blackboard] `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
