# 渡桥 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4147_mitm` |
| 职业 | 先锋 / `tactician` |
| 星级 | 5 星 |
| 生命（精二满级） | 1370 |
| 攻击（精二满级） | 495 |
| 防御（精二满级） | 122 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4147_mitm_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.366667 秒** | 11 帧 |

> 占攻击间隔 36.7%（0.366667 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_Loop` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 遥控解体　`skchr_mitm_1`

**技能描述（最高级）：**

> 立即获得6点部署费用，并使樱桃三号自毁且对周围四格敌人造成相当于渡桥攻击力400%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 9 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 6 |
| `aoe_damage_scale` | 4 |

#### 攻击范围

`rangeId = x-5`，5 格（direction=1）

```
· ■ · 
■ ■ ■ 
· ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mitm_s_1`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="BUFF_OWNER"
- **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **Withdraw** 

**`mitm_s_1[cost]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"
- **ModifyCost** 

---

### 承压功率　`skchr_mitm_2`

**技能描述（最高级）：**

> 技能持续时间内逐渐获得12点部署费用，攻击力+80%；樱桃三号停止攻击，阻挡数+1，防御力+140%
> 技能结束后樱桃三号销毁自身


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@max_target` | 1 |
| `atk` | 0.8 |
| `mode` | 1 |
| `mitm_s_2[to_token].block_cnt` | 2 |
| `mitm_s_2[to_token].def` | 1.4 |
| `mitm_s_2[to_token].hp` | 1 |
| `mitm_s_2[cost].cost` | 1 |
| `mitm_s_2[cost].interval` | 1.25 |
| `mitm_s_2[cost].display` | 12 |
| `block_cnt_display` | 1 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`mitm_s_2[cost]`** ← 事件 `ON_BUFF_TRIGGER`

- **ModifyCost** 

**`mitm_s_2[to_token]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **PlayAudio** `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`mitm_s_2[to_token][attribute]` 属性修改=[BLOCK_CNT ADDITION blackboard, DEF MULTIPLIER blackboard] `lifeTimeType`=INFINITY

**`mitm_s_2[to_token]`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **Withdraw** 

**`mitm_s_2[token_switch_mode]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
