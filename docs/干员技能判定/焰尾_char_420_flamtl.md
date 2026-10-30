# 焰尾 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_420_flamtl` |
| 职业 | 先锋 / `pioneer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2138 |
| 攻击（精二满级） | 526 |
| 防御（精二满级） | 392 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_420_flamtl_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.6 秒** | 18 帧 |

> 占攻击间隔 57.1%（0.6 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Attack_2` | 0.2 秒 | 6 帧 |
| 技能动画 | `Skill_2_Loop` | 0.2 秒 | 6 帧 |


## 三、技能逐层拆解

---

### 迅敏直觉　`skchr_flamtl_1`

**技能描述（最高级）：**

> 立即获得6点部署费用，并闪避下次物理攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 9 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 6 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`flamtl_s_1`** ← 事件 `ON_TAKE_DAMAGE`

- **Evade** 
- **FinishBuff** 

**`flamtl_s_1`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`flamtl_s_1[effect]` `lifeTimeType`=INFINITY

---

### “红松林”　`skchr_flamtl_2`

**技能描述（最高级）：**

> 立即获得13点部署费用；对周围最多6名敌人造成两次相当于攻击力240%的物理伤害，并令击中目标晕眩0.5秒；范围内友方单位获得50%的物理闪避，持续10秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 13 |
| `atk_scale` | 2.4 |
| `stun` | 0.5 |
| `max_target` | 6 |
| `flamtl_s_2.prob` | 0.5 |
| `flamtl_s_2.duration` | 10 |

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

**`flamtl_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ALLY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

---

### 焰心　`skchr_flamtl_3`

**技能描述（最高级）：**

> 技能持续时间内逐渐获得8点部署费用，攻击间隔缩短，攻击力+90%，阻挡数+1，获得80%的物理和法术闪避


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 6 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 8 秒 |
| duration / durationType | 8 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.9 |
| `cost` | 1 |
| `prob` | 0.8 |
| `base_attack_time` | 0.7 |
| `block_cnt` | 1 |
| `value` | 8 |

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

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
