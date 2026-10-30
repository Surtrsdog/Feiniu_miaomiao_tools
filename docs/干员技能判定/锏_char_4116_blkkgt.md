# 锏 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4116_blkkgt` |
| 职业 | 近卫 / `sword` |
| 星级 | 6 星 |
| 生命（精二满级） | 2891 |
| 攻击（精二满级） | 635 |
| 防御（精二满级） | 339 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4116_blkkgt_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 30.8%（0.4 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_2_B` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_End` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_Down_2` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_2_B` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 纯粹的武力　`skchr_blkkgt_1`

**技能描述（最高级）：**

> 下次攻击对周围最多6名地面敌人造成两次相当于攻击力220%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale_s1` | 2.2 |
| `max_target` | 6 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`blkkgt_s_1[mode]`** ← 事件 `ON_SKILL_FINISH`

- **FinishBuff** 

**`blkkgt_s_1[mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`blkkgt_s_1[mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 无声的嘲笑　`skchr_blkkgt_2`

**技能描述（最高级）：**

> 对前方范围内最多6名地面敌人发动2次斩击，攻击被阻挡的敌人时改为3次斩击，天赋的发动概率提升至100%，每次斩击造成相当于攻击力310%的物理伤害
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 10 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `dot_scale` | 3.1 |
| `max_target` | 6 |
| `blkkgt_s_2[not_blocked].trig_cnt` | 2 |
| `blkkgt_s_2[blocked].trig_cnt` | 3 |
| `prob` | 1 |

#### 攻击范围

`rangeId = 1-4`，6 格（direction=1）

```
■ ■ 
■ ■ 
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`blkkgt_s_2[add_cnt]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["blkkgt_s_2[shield]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`blkkgt_s_2[shield]` templateKey=`blkkgt_s_2[shield]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["blkkgt_s_2[effect_1]"] `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`blkkgt_s_2[effect_1]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["blkkgt_s_2[effect_1]"] `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["blkkgt_s_2[effect_2]"] `_targetType`="BUFF_OWNER"
- …（共 17 个节点，已截断）

**`blkkgt_s_2[check_block]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`blkkgt_s_2[blocked]` templateKey=`blkkgt_s_2[dot]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`blkkgt_s_2[not_blocked]` templateKey=`blkkgt_s_2[dot]` `lifeTimeType`=INFINITY

**`blkkgt_s_2[dot]`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="TARGET"
- **AlwaysNext** 
- **IfElse** 
  - **CheckTriggerable** 
  - **FinishBuff** 

**`blkkgt_s_2[shield]`** ← 事件 `ON_TAKE_DAMAGE`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **BlockDamage** 
  - **AddBuffBlackboard** `_targetType`="BUFF_OWNER"
  - **AlwaysNext** 
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
    - **FinishBuff** 
    - **AlwaysNext** 
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **AlwaysNext** 
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **FilterByBlackboardValue** `_condType`="LE" `_targetType`="BUFF_OWNER"
      - **IfElse** 
        - **CheckContainsBuff** `_buffKeys`=["blkkgt_s_2[effect_2]"] `_targetType`="BUFF_OWNER"
- …（共 26 个节点，已截断）

**`blkkgt_s_2[shield]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 归于宁静　`skchr_blkkgt_3`

**技能描述（最高级）：**

> 持续发动总计10次斩击，每次斩击对最多6名敌人造成相当于攻击力235%的物理伤害，天赋的发动概率提升至100%，并持续将敌人中等力度地拖拽至自身中心，之后将造成一次相当于攻击力330%的物理伤害并将敌人较大力地拖拽至自身中心


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `prob` | 1 |
| `max_target` | 6 |
| `d_atk_scale` | 2.35 |
| `d_hit_interval` | 0.3 |
| `p_force` | 1 |
| `p_hit_interval` | 1 |
| `e_atk_scale_end` | 3.3 |
| `e_force` | 2 |

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

> 匹配方式：按命名规则匹配（层级 B）

**`blkkgt_s_3[effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **IfTarget** `_targetType`="BUFF_SOURCE"
  - **FinishBuff** 

**`blkkgt_s_3[effect]`** ← 事件 `ON_BUFF_START`

- **AttachAsDerivedBuffById** 

**`blkkgt_s_3[finish_effect]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`blkkgt_s_3[trigger_clear]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
