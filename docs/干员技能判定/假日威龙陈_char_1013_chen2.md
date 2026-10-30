# 假日威龙陈 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1013_chen2` |
| 职业 | 狙击 / `reaperrange` |
| 星级 | 6 星 |
| 生命（精二满级） | 2501 |
| 攻击（精二满级） | 773 |
| 防御（精二满级） | 203 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 32 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.3 ÷ 1.00 = 2.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1013_chen2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 21.7%（0.5 秒 / 2.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_1_Loop_Down` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Loop_Down` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_Loop` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_Loop_Down` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 高压冲击　`skchr_chen2_1`

**技能描述（最高级）：**

> 攻击力+100%，攻击时对攻击范围内的所有敌人应用特性加成
> 攻击装有4发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@trigger_time` | 4 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### “堇青之夜”　`skchr_chen2_2`

**技能描述（最高级）：**

> 攻击力+80%，每次攻击在范围内生成持续5秒的粘液，地面敌人经过时移动速度-35%、防御力-170（不叠加），蓄力额外效果：改为20发弹药
> 攻击装有8发弹药，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 12 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `attack@move_speed` | -0.35 |
| `attack@def` | -170 |
| `attack@projectile_life_time` | 5 |
| `attack@trigger_time` | 8 |
| `attack@another_trigger_time` | 20 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`chen2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`chen2_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["chen2_s_2_enhance_mark"] `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`chen2_s_2[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["chen2_s_2_enhance_mark"] `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="chen2_s_2[eff_cond][full]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`chen2_s_2[eff_cond][full]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`chen2_s_2[eff_cond][half]` `lifeTimeType`=INFINITY
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="chen2_s_2[eff_cond][half]"
    - **IfNot** 
    - **FinishDerivedBuff** 
    - **CreateBuff** buffKey=`chen2_s_2[eff_cond][half]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=2 `_targetType`="BUFF_OWNER"
    - **CheckContainsDerviedBuff** `_derviedBuffKey`="chen2_s_2[eff_cond][full]"
- …（共 27 个节点，已截断）

---

### “假日风暴”　`skchr_chen2_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+100%，攻击造成两次伤害，对攻击范围内的所有敌人应用特性加成，每次攻击在范围内生成持续5秒的粘液，地面敌人经过时移动速度-45%、防御力-220（不叠加）
> 攻击装有32发弹药，每次攻击消耗2发，打完后结束（可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@move_speed` | -0.45 |
| `attack@def` | -220 |
| `attack@projectile_life_time` | 5 |
| `attack@trigger_time` | 32 |

#### 攻击范围

`rangeId = 2-6`，9 格（direction=1）

```
· · ■ 
· ■ ■ 
■ ■ ■ 
· ■ ■ 
· · ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
