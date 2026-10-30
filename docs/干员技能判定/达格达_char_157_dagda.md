# 达格达 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_157_dagda` |
| 职业 | 近卫 / `fighter` |
| 星级 | 5 星 |
| 生命（精二满级） | 2506 |
| 攻击（精二满级） | 574 |
| 防御（精二满级） | 310 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.78 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.78 ÷ 1.00 = 0.780 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_157_dagda_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.166667 秒** | 5 帧 |

> 占攻击间隔 21.4%（0.166667 秒 / 0.78 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill1` | 0.1 秒 | 3 帧 |
| 技能动画 | `Skill2` | 0.2 秒 | 6 帧 |


## 三、技能逐层拆解

---

### 反制技巧　`skchr_dagda_1`

**技能描述（最高级）：**

> 使下次受到的物理伤害减少60%，触发后下次攻击的攻击力提高至210%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 3 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `damage_resistance` | 0.6 |
| `attack@defensive_atk_scale` | 2.1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`dagda_s_1`** ← 事件 `ON_TAKE_DAMAGE`

- **DamageScale** 
- **InterruptCharacterAttack** `_charFrom`="BUFF_OWNER"
- **CreateBuff** buffKey=`dagda_s_trigger[take_damage]` `lifeTimeType`=INFINITY
- **FinishBuff** 

**`dagda_s_1[end_skill_trigger]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 精准捕杀　`skchr_dagda_2`

**技能描述（最高级）：**

> 攻击力+35%，攻击变为二连击，天赋发动概率提升至60%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.35 |
| `talent@prob` | 0.6 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`dagda_s_2[modify_t_1_prob]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

**`dagda_s_2[modify_t_1_prob]`** ← 事件 `ON_BUFF_FINISH`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
