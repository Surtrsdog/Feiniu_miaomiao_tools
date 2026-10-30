# 吽 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_226_hmau` |
| 职业 | 重装 / `guardian` |
| 星级 | 5 星 |
| 生命（精二满级） | 2823 |
| 攻击（精二满级） | 442 |
| 防御（精二满级） | 585 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_226_hmau_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.3 秒** | 9 帧 |

> 占攻击间隔 25.0%（0.3 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 反制治疗　`skchr_hmau_1`

**技能描述（最高级）：**

> 下一次攻击改为周围的一名友方单位恢复相当于攻击力170%的生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 4 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 1.7 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hmau_s_1`** ← 事件 `ON_OUTPUT_MODIFIER`

- **IsHeal** 
- **ModifySp** `_targetType`="MODIFIER_TARGET" `_forceFlag`=False

---

### 反制医疗模式　`skchr_hmau_2`

**技能描述（最高级）：**

> 攻击力和防御力+80%，停止攻击并专心对周围友方单位进行治疗，并在治疗时为其恢复1点技力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 18 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `def` | 0.8 |
| `base_attack_time` | 1.3 |
| `sp` | 1 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
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
