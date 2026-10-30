# 岳羽由加莉 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4219_yukari` |
| 职业 | 辅助 / `supportiveranger` |
| 星级 | 5 星 |
| 生命（精二满级） | 1510 |
| 攻击（精二满级） | 775 |
| 防御（精二满级） | 200 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.1 ÷ 1.00 = 2.100 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4219_yukari_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.033333 秒** | 1 帧 |

> 占攻击间隔 1.6%（0.033333 秒 / 2.1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 1.53333 秒 | 46 帧 |
| 技能动画 | `Skill_2` | 2.4 秒 | 72 帧 |


## 三、技能逐层拆解

---

### 龙卷箭　`skchr_yukari_1`

**技能描述（最高级）：**

> 立即发射三发箭矢，每发对目标造成相当于80%攻击力的法术伤害，随后追加一次相当于攻击力400%的范围法术伤害并浮空所有目标1.5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `multi_atk_scale` | 0.8 |
| `final_atk_scale` | 4 |
| `levitate` | 1.5 |

#### 攻击范围

`rangeId = 3-18`，14 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`yukari_s_1[audio]`** ← 事件 `ON_BUFF_TRIGGER`

- **PlayAudio** `_target`="BUFF_OWNER"
- **FinishBuff** 

---

### 明镜止水　`skchr_yukari_2`

**技能描述（最高级）：**

> 为范围内最多4名我方干员（优先选择结城理、术师干员）施加触发型效果：
> 干员施放技能后，自身在15秒内获得30%术法充盈


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target` | 4 |
| `duration` | 15 |
| `damage_up` | 0.3 |

#### 攻击范围

`rangeId = 3-18`，14 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`yukari_s_2`** ← 事件 `ON_SKILL_START`

- **CreateBuff** buffKey=`yukari_s_2[damage_scale]` templateKey=`damage_scale[out_mag]` `lifeTimeType`=LIMITED
- **FinishBuff** 

**`yukari_s_2[audio]`** ← 事件 `ON_BUFF_TRIGGER`

- **PlayAudio** `_target`="BUFF_OWNER"
- **FinishBuff** 

**`yukari_s_2[ball]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckUnitAlive** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`yukari_s_2[check]`** ← 事件 `ON_BUFF_START`

- **CalculateBlackboardValueViaParams** 
- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["yukari_s_2"] `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **FilterByExecuteBlackboardValue** `_condType`="GE"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`yukari_s_2` templateKey=`yukari_s_2` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`yukari_s_2` templateKey=`yukari_s_2` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
