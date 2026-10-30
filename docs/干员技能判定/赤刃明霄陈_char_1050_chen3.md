# 赤刃明霄陈 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1050_chen3` |
| 职业 | 近卫 / `artsfghter` |
| 星级 | 6 星 |
| 生命（精二满级） | 2910 |
| 攻击（精二满级） | 670 |
| 防御（精二满级） | 425 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.25 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.25 ÷ 1.00 = 1.250 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1050_chen3_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 34.7%（0.433333 秒 / 1.25 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 赤霄·奔夜　`skchr_chen3_1`

**技能描述（最高级）：**

> 攻击力+120%，攻击变为二连击，攻击使目标敌人特殊能力失效持续至技能结束


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 18 秒 |
| duration / durationType | 18 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chen3_s1[derived_silence]`** ← 事件 `ON_BUFF_START`

- **AttachAsDerivedBuffById** 

---

### 赤霄·绝影-驰　`skchr_chen3_2`

**技能描述（最高级）：**

> 对周围最近的1名敌人发动10次斩击，每次造成攻击力480%的法术伤害，敌人被击倒时转移至目标周围最近的其他敌人并使剩余攻击次数+1；斩击结束时，若目标未被击倒且其位置可部署则移动至该位置，否则返回原位置。接下来攻击力+300%，获得60%物理和法术闪避


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 6 秒 |
| duration / durationType | 6 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4.8 |
| `chen3_s2[respawn_buff].atk` | 3 |
| `chen3_s2[respawn_buff].prob` | 0.6 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`chen3_s2[ban_sp]`** ← 事件 `ON_BUFF_START`

- **ClearCharacterSp** `_forceFlag`=False `_charFrom`="BUFF_OWNER"
- **CreateBuff** buffKey=`chen3_s2[disable_sp_recover]` `lifeTimeType`=INFINITY

**`chen3_s2[dead_listener]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **AttachAsDerivedBuffById** 
- **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"

**`chen3_s2[dead_listener]`** ← 事件 `ON_OWNER_FINISH`

- **CheckUnitAlive** 
- **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **ExtendAbilityCooldown** 
- **AddAbilityBlackboard** 

**`chen3_s2[record_position]`** ← 事件 `ON_BUFF_START`

- **IfTargetEqual** 
- **IfNot** 
- **AssignGridPositionToBlackboard** `_targetType`="BUFF_OWNER"
- **AddCharacterSharedBlackboard** `_target`="BUFF_SOURCE"
- **AddCharacterSharedBlackboard** `_target`="BUFF_SOURCE"

**`chen3_s2[respawn_buff]`** ← 事件 `ON_TAKE_DAMAGE`

- **Evade** 

**`chen3_s2[respawn_buff]`** ← 事件 `ON_OWNER_LOCATE`

- **CreateBuff** buffKey=`chen3_s2[respawn_effect]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`chen3_s2[respawn_effect_2]` `lifeTimeType`=INFINITY

**`chen3_s2[respawn_default]`** ← 事件 `ON_OWNER_LOCATE`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`chen3_s2[target_kill]`** ← 事件 `ON_TARGET_KILLED`


**`chen3_s2[target_kill]`** ← 事件 `ON_BUFF_FINISH`

- **UpdateAbilityCoolDown** 

**`chen3_s2[target_kill]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboard** `_targetType`="TARGET"

**`chen3_s2[time_bb]`** ← 事件 `ON_BUFF_START`

- **ModifyAbilityBlackboard** 

**`chen3_s2[try_resapwn]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **IsBlackboardEqualWithFloat** 
  - **EmitProjectile** `_targetType`="TARGET"
    - **CheckUnitAlive** 
    - **FinishBuffsById** `_targetType`="SOURCE"
    - **AddExcludeCharacterToDynamicBuffTile** `_targetType`="SOURCE"
    - **AlwaysNext** 
    - **AddCharacterSharedBlackboard** `_target`="SOURCE"
    - **AlwaysNext** 
    - **RespawnCharacter** `_targetType`="SOURCE"
    - **IfNot** 
    - **AddCharacterSharedBlackboard** `_target`="SOURCE"
  - **EmitProjectile** `_targetType`="TARGET"
    - **CheckUnitAlive** 
- …（共 24 个节点，已截断）

---

### 赤霄·天喟　`skchr_chen3_3`

**技能描述（最高级）：**

> 技能开启时向前释放一道可转向的剑气，对穿过的敌人造成相当于其当前生命值6%的法术伤害（至少造成自身攻击力580%的法术伤害）；攻击范围扩大，每次攻击对最多4名地面敌人造成3次攻击力210%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `hp_ratio` | 0.06 |
| `projectile_min_atk_scale` | 5.8 |
| `attack@atk_scale` | 2.1 |
| `attack@max_target` | 4 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chen3_s3[ensure_dmg]`** ← 事件 `ON_OUTPUT_MODIFIER`

- **CheckModifierContainsKey** 
- **EnsureDmgOrHeal** `_key`="projectile_min_atk_scale"

**`chen3_s3[finish_projectile]`** ← 事件 `ON_BUFF_FINISH`

- **FinishManagedProjectiles** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
