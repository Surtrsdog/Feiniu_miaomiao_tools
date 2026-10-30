# 休谟斯 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_491_humus` |
| 职业 | 近卫 / `reaper` |
| 星级 | 4 星 |
| 生命（精二满级） | 2150 |
| 攻击（精二满级） | 616 |
| 防御（精二满级） | 403 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_491_humus_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.3 秒** | 9 帧 |

> 占攻击间隔 23.1%（0.3 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.366667 秒 | 11 帧 |


## 三、技能逐层拆解

---

### 固废切割　`skchr_humus_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至250%，并额外回复自身80生命值


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
| `atk_scale` | 2.5 |
| `value` | 80 |

#### 攻击范围

`rangeId = 1-3`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ 
■ ■ 
· ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`humus_s_1`** ← 事件 `ON_BUFF_START`

- **FixedValueHeal** `_targetType`="BUFF_OWNER"

---

### 高效处理　`skchr_humus_2`

**技能描述（最高级）：**

> 技能持续时间内阻挡数+1，生命值高于50%时，获得+45%攻击力的精力充沛；高于80%时效果翻倍


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `humus_s_2[peak_1].peak_performance.atk` | 0.45 |
| `humus_s_2[peak_1].peak_performance.hp_ratio` | 0.5 |
| `humus_s_2[peak_2].peak_performance.atk` | 0.9 |
| `humus_s_2[peak_2].peak_performance.hp_ratio` | 0.8 |
| `block_cnt` | 1 |

#### 攻击范围

`rangeId = 1-3`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ 
■ ■ 
· ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`humus_s_2[peak]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 

**`humus_s_2[peak]`** ← 事件 `ON_BUFF_FINISH`

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
