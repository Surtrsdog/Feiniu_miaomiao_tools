# 煌 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_017_huang` |
| 职业 | 近卫 / `centurion` |
| 星级 | 6 星 |
| 生命（精二满级） | 2821 |
| 攻击（精二满级） | 765 |
| 防御（精二满级） | 370 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_017_huang_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 27.8%（0.333333 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_1_Down` | 0.6 秒 | 18 帧 |
| 技能动画 | `Skill_2_Loop` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop_Down` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop_Down_End` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_2_Loop_End` | 0 秒 | 0 帧 |


## 三、技能逐层拆解

---

### 强力击·γ型　`skchr_huang_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提高至290%


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
| `atk_scale` | 2.9 |

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

### 链锯延伸模块　`skchr_huang_2`

**技能描述（最高级）：**

> 攻击力+100%，防御力+35%，攻击距离加长
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 70 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `def` | 0.35 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 沸腾爆裂　`skchr_huang_3`

**技能描述（最高级）：**

> 技能开启后，攻击力和防御力逐渐增至+80%并对前方一格内的敌方单位进行切割。技能结束时对附近所有敌人造成此时攻击力400%的物理伤害，自己流失25%的生命值


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `def` | 0.8 |
| `hp_ratio` | 0.25 |
| `damage_by_atk_scale` | 4 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`huang_s_3`** ← 事件 `ON_BUFF_TRIGGER`

- **RemainingRatioToAttributeModifier** 
- **AlwaysNext** 
- **RemainingRatioToAttributeModifier** 

**`huang_s_3`** ← 事件 `ON_SKILL_FINISH`

- **DamageViaMaxHpRatio** `_targetType`="SOURCE"
- **AlwaysNext** 
- **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateBuff** buffKey=`huang_s_3[audio]` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
