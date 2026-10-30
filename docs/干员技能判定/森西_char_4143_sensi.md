# 森西 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4143_sensi` |
| 职业 | 重装 / `guardian` |
| 星级 | 5 星 |
| 生命（精二满级） | 2770 |
| 攻击（精二满级） | 470 |
| 防御（精二满级） | 580 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4143_sensi_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 38.9%（0.466667 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 2.6 秒 | 78 帧 |
| 技能动画 | `Skill_2` | 9.3 秒 | 279 帧 |


## 三、技能逐层拆解

---

### 单人份料理　`skchr_sensi_1`

**技能描述（最高级）：**

> 开始烹饪，3秒内停止攻击，烹饪完成后治疗周围一名友方角色，使其恢复相当于攻击力280%的生命，且随机获得下列一项增益：攻击力+20%，攻击速度+20，生命上限+25%，持续8秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 6 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 3 秒 |
| duration / durationType | 3 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 2.8 |
| `atk` | 0.2 |
| `attack_speed` | 20 |
| `max_hp` | 0.25 |
| `up_duration` | 8 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`sensi_s_1[random]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **RandomCreateBuff** 

**`sensi_s_1[random_effect]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[atk]"] `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[atk_speed]"] `_targetType`="BUFF_SOURCE"
    - **CreateEffect** `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[max_hp]"] `_targetType`="BUFF_SOURCE"
      - **CreateEffect** `_targetType`="BUFF_OWNER"
      - **CreateEffect** `_targetType`="BUFF_OWNER"

**`sensi_s_1[random_result]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **IsCharacter** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[atk]"] `_targetType`="BUFF_SOURCE"
    - **CreateBuff** buffKey=`sensi_s_1[atk_attribute]` 属性修改=[ATK MULTIPLIER blackboard] `overrideType`=EXTEND `lifeTimeType`=LIMITED
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[atk_speed]"] `_targetType`="BUFF_SOURCE"
      - **CreateBuff** buffKey=`sensi_s_1[atk_speed_attribute]` 属性修改=[ATTACK_SPEED ADDITION blackboard] `overrideType`=EXTEND `lifeTimeType`=LIMITED
      - **FinishBuffsById** `_targetType`="BUFF_OWNER"
      - **FinishBuffsById** `_targetType`="BUFF_OWNER"
      - **IfElse** 
        - **CheckContainsBuff** `_buffKeys`=["sensi_s_1[max_hp]"] `_targetType`="BUFF_SOURCE"
        - **CreateBuff** buffKey=`sensi_s_1[max_hp_attribute]` 属性修改=[MAX_HP MULTIPLIER blackboard] `overrideType`=EXTEND `lifeTimeType`=LIMITED
        - **FinishBuffsById** `_targetType`="BUFF_OWNER"
- …（共 18 个节点，已截断）

---

### 团体魔物大餐　`skchr_sensi_2`

**技能描述（最高级）：**

> 开始烹饪，10秒内停止攻击，期间使周围的友方角色每秒恢复相当于森西攻击力45%的生命，之后对附近一定范围内所有友方角色进行一次相当于攻击力180%的治疗，并回复10点魔力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `tick_heal_scale` | 0.45 |
| `heal_scale` | 1.8 |
| `magic_sp` | 10 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`sensi_s_2[recover_magic]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="TARGET"
  - **CreateBuff** buffKey=`sensi_s_2_audio` `lifeTimeType`=IMMEDIATELY
  - **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=False
  - **IfElse** 
    - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
    - **CreateEffect** `_targetType`="TARGET"
    - **CreateBuff** buffKey=`sensi_s_2_audio` `lifeTimeType`=IMMEDIATELY
    - **IfElse** 
      - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
      - **CreateEffect** `_targetType`="TARGET"
      - **CreateBuff** buffKey=`sensi_s_2_audio` `lifeTimeType`=IMMEDIATELY
      - **IfElse** 
        - **CheckTargetRootTile** `_targetType`="BUFF_OWNER"
        - **CreateEffect** `_targetType`="TARGET"
- …（共 19 个节点，已截断）

**`sensi_s_2[tick_heal]`** ← 事件 `ON_BUFF_TRIGGER`

- **AOEHeal** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ALLY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
