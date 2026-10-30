# 斥罪 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4065_judge` |
| 职业 | 重装 / `unyield` |
| 星级 | 6 星 |
| 生命（精二满级） | 4055 |
| 攻击（精二满级） | 876 |
| 防御（精二满级） | 616 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 36 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4065_judge_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.566667 秒** | 17 帧 |

> 占攻击间隔 35.4%（0.566667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Attack` | 0.3 秒 | 9 帧 |
| 技能动画 | `Skill_3_Attack` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_Down_3_Attack` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 一锤定音　`skchr_judge_1`

**技能描述（最高级）：**

> 下次攻击额外造成相当于攻击力200%的法术伤害
> 蓄力额外效果：攻击时攻击力提升至200%并使目标晕眩5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale_2` | 2 |
| `judge_s_1_enhance_checker.atk_scale` | 2 |
| `stun` | 5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`judge_s_1_enhance_checker`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=1 `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`judge_s_1_enhance[mark]` `lifeTimeType`=INFINITY
- **ClearCharacterSp** `_forceFlag`=False `_charFrom`="BUFF_OWNER"

**`judge_s_1_enhance_checker`** ← 事件 `ON_CALCULATE_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["judge_s_1_enhance[mark]"] `_targetType`="BUFF_OWNER"
- **AtkScaleUp** 

**`judge_s_1_enhance_checker`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 坚心苦修　`skchr_judge_2`

**技能描述（最高级）：**

> 停止攻击，获得60%的庇护，每秒对周围所有地面敌人造成相当于攻击力140%的法术伤害，技能期间第一天赋的屏障获取效果提升100%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `damage_resistance` | 0.6 |
| `atk_scale` | 1.4 |
| `shield_scale` | 1 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`judge_s_2[aoe]`** ← 事件 `ON_BUFF_TRIGGER`

- **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`judge_s_2[aoe]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`judge_s_2[aoe]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`judge_s_2[shield_scale]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`judge_s_2[shield_scale]`** ← 事件 `ON_BUFF_FINISH`

- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

---

### 披荆斩棘　`skchr_judge_3`

**技能描述（最高级）：**

> 立即获得相当于生命上限130%的屏障，攻击间隔增大，攻击力+400%，自身更容易受到敌人攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 0 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `hp_ratio` | 1.3 |
| `base_attack_time` | 0.9 |
| `atk` | 4 |
| `taunt_level` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`judge_s_3[shield]`** ← 事件 `ON_BUFF_START`

- **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
- **TriggerBuffsByKeys** `_buffKeys`=["judge_t_1"] `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
