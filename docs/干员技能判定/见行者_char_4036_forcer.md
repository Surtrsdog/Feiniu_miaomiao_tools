# 见行者 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4036_forcer` |
| 职业 | 特种 / `pusher` |
| 星级 | 5 星 |
| 生命（精二满级） | 1937 |
| 攻击（精二满级） | 653 |
| 防御（精二满级） | 381 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 22 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4036_forcer_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 27.8%（0.333333 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 护身射击　`skchr_forcer_1`

**技能描述（最高级）：**

> 下次攻击会把目标往攻击方向较大力地推开，目标撞到高台时晕眩2秒。


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
| `force` | 2 |
| `stun` | 2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`forcer_s_1[against_wall]`** ← 事件 `ON_COLLIDE_WITH_HIGHLAND`

- **CheckEnemyUnbalanced** `_targetType`="BUFF_OWNER"
- **CreateBuffById** 
- **FinishBuff** 

**`forcer_s_1[against_wall]`** ← 事件 `ON_BEFORE_EXIT_UNBALANCED_STATE`

- **FinishBuff** 

**`forcer_s_1[against_wall]`** ← 事件 `ON_BUFF_START`

- **CheckEnemyUnbalanced** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

---

### 惊爆射击　`skchr_forcer_2`

**技能描述（最高级）：**

> 立即将范围内所有敌人往身前方向大力地推开并晕眩2.5秒（撞到高台时晕眩时间延长为4秒）。若目标碰撞其他敌人，使其晕眩2.5秒。


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 17 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `force` | 3 |
| `stun` | 4 |
| `forcer_s_2[brush].stun` | 2.5 |
| `forcer_s_2[hit_directly].stun` | 2.5 |
| `projectile_range` | 0.33 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`forcer_s_2[brush]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 

**`forcer_s_2[hit_directly]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 
- **CheckEnemyUnbalanced** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`forcer_s_2[hit_directly]`** ← 事件 `ON_BEFORE_EXIT_UNBALANCED_STATE`

- **FinishBuff** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
