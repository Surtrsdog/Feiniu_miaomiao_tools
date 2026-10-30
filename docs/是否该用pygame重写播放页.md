
# 是否该用 pygame 重写播放页 —— 技术评估

> 状态：**仅评估，未实装**。零代码改动。
> 日期：2026-10-28
> 结论先说：**不值得。** 但你直觉指向的问题是真的，只是答案不在引擎。

---

## 零 结论

| 问题 | 答案 |
|---|---|
| 换 pygame 会更流畅吗？ | **不会。** 瓶颈 98.8% 在渲染算法，引擎开销只占 1.2% |
| 需要换引擎吗？ | **不需要。** 原地优化后 **71~122 fps** 就够 |
| 那直觉错了吗？ | **没错。** 你感觉到「卡」是真的，只是病因错了 |
| 该做什么？ | 见 §五 的三件事，**2.5 人天**，收益比换引擎大 |

---

## 一 先把账算清楚：卡在哪

`act1multi_football`（13×9 格，1361 条路线，**1393 只敌人**）用**消融法**实测
（同一段代码，逐个关掉一个环节，所以各项**可加、不重复计**）：

| 配置 | ms/帧 | 该环节贡献 |
|---|---|---|
| 全部开启 | **433.1** | — |
| 关掉「重叠错开」 | 237.1 | **196.0 (45%)** |
| 关掉「名字绘制」 | 233.5 | **199.6 (46%)** |
| **两个都关（只剩合成）** | **43.1** | — |

两个大头各占约一半，加起来 395.6 ms，正好把 433.1 打回 43.1——
**所以这张表是可加的，没有重复计入**。

再单看框架开销：

| 环节 | ms/帧 |
|---|---|
| 纯 sprite 合成（1393 次 `alpha_composite`） | 43.1 |
| `_master_to_frame`（底图裁剪缩放） | 23.35 |
| **`ImageTk.PhotoImage` 上传** | **5.09** |

**关键结论**：整个链路里，真正由 Tkinter 框架产生的开销是 `PhotoImage` 那 **5.09 ms**，
相对 433 ms 只有 **1.2%**。剩下 **98.8% 是 PIL 里的绘图算法**
（重叠错开 O(n²)、逐只渲染文字、逐只合成）——换任何引擎，这段逻辑都要重写一遍，
而**同样的算法问题会原封不动搬过去**。

> 说明：这些数字在不同轮次测量中会在 280~1130 ms 之间波动（Windows 上
> PIL 的内存分配和 GC 抖动很大，且首次 sprite 缓存未热）。**只有同一轮
> 消融法测出的倍数关系是可靠的**，绝对值仅供参考。

### 1.1 为什么 pygame 也救不了

我实测了 pygame 2.6.1（本机已装）的同等工作量：

| 操作 | PIL 现状 | pygame | 结论 |
|---|---|---|---|
| 合成 1393 个 52px 圆点 | 27.89 ms | **4.96 ms** | pygame 快 5.6× |
| 渲染 1 次中文文字 | 0.131 ms（未缓存） | 0.002 ms | — |
| blit 1393 次文字 | 200 ms（直接 draw） | **16.05 ms** | pygame 快 12× |
| 清屏 | 0.915 ms（copy） | 0.262 ms | pygame 快 3.5× |

**pygame 确实更快**——但快的这部分，**PIL 也能拿到**，只要做同样的事：

```
现状 每帧渲染文字 1393 次 = 180.08 ms
预渲染 1 次（含裁剪）      =   0.131 ms   ← 只做一次
缓存后 1393 次合成         =  32.34 ms
提速 5x
```

那个 0.002 ms 不是 pygame 的魔法，是**文字被缓存成了 surface**。
PIL 把文字切成 sprite 缓存后，同样从 180ms 降到 32ms。
**可复制的收益，为什么要换引擎？**

---

## 二 换引擎的真实代价

不只是「重写一个页面」。

### 2.1 嵌进 Tkinter：能做，但很脆

我实测过 `SDL_WINDOWID` 嵌入：

```
frame.winfo_id() = 4994872
pygame 嵌入成功, surface = (320, 240)
flip + update 成功
```

**技术上可行**。但这条路的问题是：

* **窗口层级打架**：SDL 子窗口会盖住 Tk 的所有控件，右键菜单、
  悬停 tooltip、`PlaybackBar` 全部要重做或浮在 SDL 之上；
* **DPI 缩放**：Tk 已处理好的高 DPI，SDL 要重新处理一遍；
  本机 `MapRenderer.fit()` 里 `cell = max(14.0, ...)` 这类下限逻辑要重推；
* **托盘 / 最小化 / 切页**：现在 `PlaybackBar._visible()` 靠
  `winfo_ismapped()` 判断要不要跑，SDL 侧没有对应的可靠信号；
* **打包**：pygame **24.6 MB** + numpy **34.4 MB**（`surfarray` 需要）
  = **≈59 MB**。当前 exe 是 **79.9 MB**，换引擎后**接近翻倍**。

### 2.2 独立的 game 页面 = 两套渲染器

如果做成「单独一个 pygame 窗口/页面」，就要维护**两套地图绘制**：
`map_render.py`（静态图、路线、传送门、机关、buff 弧）和 pygame 版。
这违反当前最重要的一条架构约束：

> `_master_static_key()` 只能保留「沙盘是否激活」这一个布尔量，
> 否则每次放箱子要重烘焙 60ms。

pygame 侧要重新实现 master 缓存、`disp_rc` 翻转、`_master_to_frame` 的
仿射裁剪——**约 2000 行**，且以后每次改地图显示都要改两处。

### 2.3 依赖方向

`akcalc/core/*.py` 现在**不 import tkinter**（headless-safe，MCP 直接复用）。
引入 pygame 若放在 `core/`，就把「渲染」绑进了「计算」；
若放 `ui/`，则 `sandbox_panel` 和 `path_panel` 两个 `MapCanvas` 实例
都要分叉。而且 `build_exe.spec` 的 `hiddenimports` 要加 pygame + SDL 的
一堆二进制，PyInstaller 体积和启动时间都会涨。

---

## 三 你的直觉对在哪：真问题不是引擎

**1393 只敌人画在 117 个格子上——平均每格 11.9 只。**

```
act1multi_football   13x9 = 117 格   敌人 1393   平均每格 11.9 只
act1multi_06         13x9 = 117 格   敌人  955   平均每格  8.2 只
main_08-04           11x8 =  88 格   敌人   57   平均每格  0.6 只
a001_06              11x8 =  88 格   敌人   97   平均每格  1.1 只
```

t=2s 时 **1361 只同时在场，挤在 70 个格子里，最多的一个格子有 254 只**。

**这个画面根本没有信息量。** 254 个圆点叠在一格里，用户看到的就是一坨色块。
换 pygame 把这坨色块画得快 5 倍——**它还是一坨色块**。

所以真正的解法不是「画得更快」，是**「根本不该画 1361 个独立圆点」**。

### 3.1 按格聚合：画 70 个标记而不是 1361 个

```
t=2s 在场 1361 只，占据 70 个格子
每格最多 254 只，中位 7 只

→ 聚合后只需画 70 个标记（而不是 1361 个）
聚合后 70 个标记 render = 13.69 ms
```

聚合标记的画法：一个圆 + 中间写 `254`（或按密度渐变大小）。
用户要的是「这一格压力很大」，不是「这里有 254 个圆点」。

**顺带说明**：这个聚合只影响**显示**，不影响任何计算——
`solve_end()`（见《沙盘画面与结束机制方案》§3）仍然逐只精算。

---

## 四 原地优化的实测结果

我做了一次完整管线验证：**底图缓存 + 分桶重叠 + 按格聚合 + 名字只画悬停**。

| 时刻 | 在场格数 | 全管线 | 理论 fps |
|---|---|---|---|
| t=2s（峰值 1361 只） | 70 | **8.20 ms** | **122** |
| t=40s | 60 | **3.75 ms** | **266** |
| t=120s | 46 | **2.93 ms** | **341** |

再叠加 `PhotoImage` 上传 5.09 ms：

```
实测上限 ≈ 71 fps
```

**71 fps 已经超过 60fps 的显示需求。** 而且这是在**最坏关卡的最坏时刻**测的。

而这条路**不需要引入任何新依赖**，不增加打包体积，不新增第二套渲染器。

| 方案 | 峰值 fps | 新增依赖 | 体积 | 代码量 | 风险 |
|---|---|---|---|---|---|
| **原地优化** | **71~122** | 0 | 0 | ~120 行 | 低 |
| pygame 重写 | 估计 90~150 | pygame+numpy | **+59 MB** | ~2000 行 | **高** |

pygame 也许能到 90~150 fps，但**从 71 提到 120 用户感知不到**，
而代价是体积翻倍、两套渲染器、DPI/控件/打包全面重做。

---

## 五 那该做什么（按优先级）

### P0 · 两行改动，130 倍（0.5 人天）

这两处是**纯 bug 级**的，与渲染无关：

```python
# 1) sandbox.py:335  analysis_for 线性扫描 → 字典
self._by_route = {a.route_index: a for a in self.analyses}

# 2) sandbox.py:498  plan 缓存键与 t 脱钩（实测结果与 t 无关）
if self._plan_cache is not None and self._plan_sig == self._state_sig():
    return self._plan_cache
```

实测 `act1multi_football` 一帧 **142.31 ms → 1.09 ms（130×）**。

### P1 · 渲染三改（1.5 人天）

| 改动 | 现状 | 优化后 | 手法 |
|---|---|---|---|
| 重叠错开 | 196 ms | ~1 ms | 按 `(round(r*2)/2, round(c*2)/2)` 分桶。单独微基准 **118.6 → 0.76 ms（179×）**，且**结果实测完全一致** |
| 名字绘制 | 200 ms | ~0（悬停才画） | 文字预渲染成 sprite 缓存（pygame 那个 0.002ms 的真相）；常显时也只画一份 |
| 底图 | 23 ms | 0.9 ms | `_master_to_frame` 结果缓存，仅视口变化时重算 |
| **合计** | **433.1 ms** | **33.2 ms** | 同一套框架下实测，**13×** |

### P2 · 按格聚合（0.5 人天）

```python
# 伪代码：显示层聚合，不影响计算
cells = Counter((round(p.row), round(p.col)) for p in positions)
for (r, c), n in cells.items():
    draw_dot(r, c, size=lerp(8, cell*0.4, min(n/50, 1)), label=str(n) if n>3 else "")
```

### P3 · 什么时候才该考虑 pygame

只有同时满足以下**全部**条件：

1. 地图要**逐帧动画**（地块流光、技能范围波动、粒子）；
2. 敌人要**连续补间**（不做格聚合，坚持画 1361 个独立单位）；
3. 需要 **GPU shader**（动态光照、水面反射）；
4. 已经接受了「体积 +59MB」和「两套渲染器」。

**当前一条都不满足。** 沙盘是要「看清结果」，不是要「看得爽」。

---

## 六 一个反直觉的建议

既然 `act1multi_football` 这种关（1393 只、117 格）本身就没有逐只显示的意义，
**更好的方向不是优化渲染，是给它一个「压力图」模式**：

* 按格着色，颜色 = 该格累计经过的敌人数（预计算一次，静态）；
* 播放时只动一个「当前时刻」的游标，**不重画敌人**；
* 需要看细节时，放大到某格再切换成「逐只显示」（此时格数少，自然不快）。

这样这类关卡的播放开销**接近零**，而且比「一坨圆点」有用得多。
这个模式大约 **1 人天**，比换引擎划算得多。

---

## 附录 A 复现命令

```powershell
# 渲染分解（280ms 怎么来的）
py -c "import sys;sys.path.insert(0,'F:\mini api');
import json,time;from akcalc.core import maps as M;from akcalc.ui import map_render as MR;
raw=json.load(open(r'F:\mini api\akcalc\data\cache\levels\act1multi_football.json',encoding='utf-8'));
gm=M.parse_level(raw,'x');r=MR.MapRenderer();r.game_map=gm;r.fit(1400,900);
r.frame_enemies=[{'row':float(i%gm.height),'col':float((i*3)%gm.width),'color':'e%d'%(i%35),'enemy_name':'x'} for i in range(1393)];
r.render();t0=time.perf_counter()
for _ in range(5): r.render()
print((time.perf_counter()-t0)/5*1000,'ms')"
```

```powershell
# 证明 98.8% 不是 Tk 的锅：PhotoImage 只要 5.09ms
py -c "import tkinter as tk;from PIL import Image,ImageTk;import time;
root=tk.Tk();root.withdraw();im=Image.new('RGBA',(1400,900),(30,34,40,255));
ImageTk.PhotoImage(im);t0=time.perf_counter()
for _ in range(30): ImageTk.PhotoImage(im)
print((time.perf_counter()-t0)/30*1000,'ms');root.destroy()"
```

```powershell
# pygame blit 对比（确认它快，但快在缓存不在引擎）
$env:PYGAME_HIDE_SUPPORT_PROMPT=1
py -c "import pygame,time,random;pygame.init();s=pygame.Surface((1400,900));
d=pygame.Surface((52,52),pygame.SRCALPHA);pygame.draw.circle(d,(200,100,90,255),(26,26),22);
p=[(random.randint(0,1300),random.randint(0,820)) for _ in range(1393)];
t0=time.perf_counter()
for _ in range(20): [s.blit(d,q) for q in p]
print((time.perf_counter()-t0)/20*1000,'ms');pygame.quit()"
```

---

## 附录 B 关键数据位置

| 项 | 位置 / 值 |
|---|---|
| 渲染消融实测 | `act1multi_football` 1393 只：433.1 ms → 关两项后 43.1 ms |
| `PhotoImage` 上传 | **5.09 ms**（占 433 ms 的 1.2%） |
| pygame 目录 | **24.6 MB**；numpy **34.4 MB** |
| 当前 exe | **79.9 MB** |
| `_draw_enemies` | `akcalc/ui/map_render.py:1460` |
| 重叠错开 O(n²) | `map_render.py:1473-1481`（`same = [...]` 列表推导） |
| 名字绘制 | `map_render.py:1512`（`if self.cell >= 30 or hov or hit`） |
| `_master_to_frame` | `map_render.py:664` |
| `analysis_for` | `akcalc/core/sandbox.py:335` |
| `_blocking_plan` 缓存 | `akcalc/core/sandbox.py:498` |
| `FRAME_MS` | `akcalc/ui/playback.py:42`（16ms ≈ 60fps 目标） |
| 关卡敌人密度 | `act1multi_football` 1393 只 / 117 格 = **11.9 只/格** |
| 峰值同屏 | t=2s，**1361 只挤在 70 格**，单格最多 **254 只** |
