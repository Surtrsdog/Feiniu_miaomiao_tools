# 医生 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4125_rdoc` |
| 职业 | 近卫 / `instructor` |
| 星级 | 5 星 |
| 生命（精二满级） | 2217 |
| 攻击（精二满级） | 657 |
| 防御（精二满级） | 360 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4125_rdoc_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.033333 秒** | 1 帧 |

> 占攻击间隔 3.2%（0.033333 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Heal` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_1_Loop` | 0.1 秒 | 3 帧 |
| 技能动画 | `Skill_2` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_1_Heal` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.1 秒 | 3 帧 |
| 技能动画 | `Skill_Down_2` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 以暴制暴　`skchr_rdoc_1`

**技能描述（最高级）：**

> 立即对自身进行一次相当于攻击力400%的治疗，之后攻击间隔大幅度缩短
> 攻击装有31发子弹，打完后技能结束（期间可随时停止技能）；每次部署只能释放3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `skill_max_trigger_time` | 3 |
| `attack@trigger_time` | 31 |
| `heal_scale` | 4 |
| `base_attack_time` | -0.7 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`rdoc_s1[heal_eff]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 激素手枪　`skchr_rdoc_2`

**技能描述（最高级）：**

> 立即朝正前方发射一枚激素子弹，若击中的首个目标为友方干员，对其进行一次相当于攻击力750%的治疗
> 每次部署只能释放3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 7.5 |
| `skill_max_trigger_time` | 3 |

#### 攻击范围

`rangeId = 4-1`，5 格（direction=1）

```
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`rdoc_s2[direction]`** ← 事件 `ON_BUFF_START`

- **ForceCharacterFaceDefaultDirection** `_target`="BUFF_OWNER"

**`rdoc_s2[heal]`** ← 事件 `ON_BUFF_START`

- **VertifyTarget** `_target`="BUFF_OWNER" `_source`="BUFF_SOURCE" targetOptions(targetSide=ALLY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`rdoc_s2[heal_audio]` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
