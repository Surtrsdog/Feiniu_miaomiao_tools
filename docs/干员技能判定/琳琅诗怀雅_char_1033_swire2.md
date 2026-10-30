# 琳琅诗怀雅 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1033_swire2` |
| 职业 | 特种 / `merchant` |
| 星级 | 6 星 |
| 生命（精二满级） | 2360 |
| 攻击（精二满级） | 810 |
| 防御（精二满级） | 457 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 9 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1033_swire2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.2 秒** | 6 帧 |

> 占攻击间隔 20.0%（0.2 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.2 秒 | 6 帧 |
| 技能动画 | `Skill_2` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_End` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.233333 秒 | 7 帧 |


## 三、技能逐层拆解

---

### 仗义疏财　`skchr_swire2_1`

**技能描述（最高级）：**

> 消耗一枚金币，下一次攻击会为周围八格内血量不足70%的一名友方单位恢复相当于攻击力80%的生命
> 携带此技能时金币上限为3


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@heal_scale` | 0.8 |
| `sp` | 3 |
| `attack@sp` | -1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### “见面礼”　`skchr_swire2_2`

**技能描述（最高级）：**

> 消耗一枚金币在范围内一个可放置且可通行的地面放置香槟炸弹，香槟炸弹会对触碰到的首个敌人造成相当于攻击力200%的物理伤害，并使目标停顿2秒
> 香槟炸弹在场3秒后可额外造成一次伤害；携带此技能时金币上限为5


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `sp` | 5 |
| `atk_scale` | 2 |
| `sluggish` | 2 |
| `attack@sp` | -1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 千金一掷　`skchr_swire2_3`

**技能描述（最高级）：**

> 攻击变为二连击，击倒敌人时获得一枚金币；主动关闭技能时消耗所有金币对前方范围内敌人随机攻击，每消耗一枚金币造成一次相当于攻击力150%的物理伤害，并将目标中等力度地向前推开
> 持续时间无限，可随时主动关闭技能；携带此技能时金币上限为10


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.5 |
| `force` | 1 |
| `sp` | 10 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`swire2_s_3[end]`** ← 事件 `ON_BUFF_START`

- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=WALK_ONLY, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **AlwaysNext** 
- **CreateBuffToBlockee** buffKey=`swire2_s_3[mark_to_enemy]` `lifeTimeType`=INFINITY
- **AlwaysNext** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`swire2_s_3[end]`** ← 事件 `ON_BUFF_FINISH`

- **ClearCharacterSp** `_forceFlag`=True `_charFrom`="BUFF_OWNER"
- **InterruptAbility** 
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`swire2_s_3[end_passive]`** ← 事件 `ON_ABNORMAL_FLAG_DIRTY`

- **CheckCanUseAtkOrCbt** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **InterruptAbility** 
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
