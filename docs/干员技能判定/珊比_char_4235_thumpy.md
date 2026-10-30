# 珊比 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4235_thumpy` |
| 职业 | 重装 / `primprotector` |
| 星级 | 6 星 |
| 生命（精二满级） | 3514 |
| 攻击（精二满级） | 671 |
| 防御（精二满级） | 559 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 26 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4235_thumpy_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.3 秒** | 9 帧 |

> 占攻击间隔 18.8%（0.3 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Begin` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_2_Loop` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_3_Begin` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_3_Loop` | 0.3 秒 | 9 帧 |


## 三、技能逐层拆解

---

### “还不走？”　`skchr_thumpy_1`

**技能描述（最高级）：**

> 攻击力+50%，防御力+50%，同时攻击并以小力度推动所有阻挡的敌人


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
| `atk` | 0.5 |
| `def` | 0.5 |
| `attack@force` | 0 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`thumpy_s_1`** ← 事件 `ON_BUFF_START`

- **Knockback** `_target`="BUFF_OWNER" `_source`="BUFF_SOURCE"

---

### “慢慢走~”　`skchr_thumpy_2`

**技能描述（最高级）：**

> 攻击力和防御力+70%；向前方可通行地面喷洒占据4格的强力胶，每0.7秒造成相当于珊比攻击力50%的物理伤害和0.5秒停顿，其他干员对强力胶内的敌人造成物理伤害时附带相当于珊比攻击力15%的侵蚀损伤


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 23 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.7 |
| `def` | 0.7 |
| `atk_scale` | 0.5 |
| `max_cnt` | 5 |
| `sluggish` | 0.5 |
| `interval` | 0.7 |
| `ep_damage_ratio[trigger]` | 0 |
| `ep_damage_ratio[damage]` | 0.15 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`thumpy_s_2[block]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToBlockee** buffKey=`thumpy_s_2[trigger]` templateKey=`thumpy_s_2[trigger]` `lifeTimeType`=INFINITY

**`thumpy_s_2[block]`** ← 事件 `ON_OWNER_BLOCKEE_CHANGED`

- **FinishDerivedBuff** 
- **CreateBuffToBlockee** buffKey=`thumpy_s_2[trigger]` templateKey=`thumpy_s_2[trigger]` `lifeTimeType`=INFINITY

**`thumpy_s_2[cleaner]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryEnemyById** `_source`="BUFF_SOURCE"

**`thumpy_s_2[leave]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`thumpy_s_2[trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **CreateBuffById** 
  - **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
  - **ApplyElementDamage** `_targetType`="BUFF_OWNER"
  - **PlayAudio** `_target`="BUFF_OWNER"

**`thumpy_s_2[trigger]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfConditions** 
  - **IsCharacter** `_targetType`="MODIFIER_SOURCE"
  - **IfConditions** 
    - **FilterDamageModifer** `_source`="BUFF_SOURCE"
    - **FilterDamageModifer** `_source`="BUFF_OWNER"
    - **ApplyElementDamage** `_targetType`="BUFF_OWNER"

**`thumpy_s_2[trigger]`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"

---

### “不准走！”　`skchr_thumpy_3`

**技能描述（最高级）：**

> 阻挡数+2且同时攻击所有阻挡的敌人，攻击力+100%，防御力+135%；向前展开4格的便携传送带，使重量小于等于4且未被阻挡的敌人以每秒0.8格的速度移向珊比；传送带上的敌人每秒受到相当于珊比攻击力40%的物理伤害，且侵蚀损伤爆发时防御力额外-30


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 42 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 60 秒 |
| duration / durationType | 60 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `def` | 1.35 |
| `atk_scale` | 0.4 |
| `block_cnt` | 2 |
| `interval` | 1 |
| `conveyor_speed` | 0.8 |
| `ep_damage_ratio[trigger]` | 0 |
| `max_cnt` | 5 |
| `mass_level` | 4 |
| `thumpy[ep_break_water].def` | -30 |

#### 攻击范围

`rangeId = 0-1`，1 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`thumpy_s_3[block]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToBlockee** buffKey=`thumpy_s_3[trigger]` templateKey=`thumpy_s_3[trigger]` `lifeTimeType`=INFINITY

**`thumpy_s_3[block]`** ← 事件 `ON_OWNER_BLOCKEE_CHANGED`

- **FinishDerivedBuff** 
- **CreateBuffToBlockee** buffKey=`thumpy_s_3[trigger]` templateKey=`thumpy_s_3[trigger]` `lifeTimeType`=INFINITY

**`thumpy_s_3[cleaner]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryEnemyById** `_source`="BUFF_SOURCE"

**`thumpy_s_3[leave]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`thumpy_s_3[trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
  - **ApplyElementDamage** `_targetType`="BUFF_OWNER"

**`thumpy_s_3[trigger]`** ← 事件 `ON_BEFORE_EP_BREAK_START`

- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`thumpy[ep_break_water]` 属性修改=[DEF ADDITION blackboard] `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
