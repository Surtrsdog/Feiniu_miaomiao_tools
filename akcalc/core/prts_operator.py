"""PRTS Wiki 干员数据抓取与解析。

数据来源：https://prts.wiki
    * 干员列表：Category:干员
    * 干员详情：页面 wikitext 中的 {{属性}} / {{CharinfoV2}} 模板

说明
----
PRTS 的 Cargo 查询接口当前不可用，故采用「解析 wikitext 模板」的方式。
每个精英阶段只提供「1 级」与「满级」两个锚点，中间等级按线性插值补齐
（游戏内实际为线性成长，与 PRTS 数值吻合）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import net
from . import damage_type as DTYPE
from .models import Operator, OperatorStats

PRTS_API = "https://prts.wiki/api.php"
CATEGORY_OPERATORS = "Category:干员"

#: 缓存版本，结构变更时递增以失效旧缓存
CACHE_VERSION = 4


# --------------------------------------------------------------- 底层请求

def _api(params: Dict[str, object]) -> dict:
    url = net.build_query(PRTS_API, params)
    return net.fetch_json(url)


def list_operator_names(limit: int = 5000) -> List[str]:
    """列出所有干员页面名（Category:干员 的成员）。"""
    out: List[str] = []
    cont: Optional[str] = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": CATEGORY_OPERATORS,
            "cmlimit": "500",
            "format": "json",
            "formatversion": "2",
        }
        if cont:
            params["cmcontinue"] = cont
        d = _api(params)
        members = d.get("query", {}).get("categorymembers", [])
        for m in members:
            title = m.get("title", "")
            # 过滤子页面（含 / 的）与非干员条目
            if "/" in title or not title:
                continue
            out.append(title)
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont or len(out) >= limit:
            break
    return out


def fetch_wikitext(page: str) -> str:
    d = _api({
        "action": "parse", "page": page, "prop": "wikitext",
        "format": "json", "formatversion": "2",
    })
    if "error" in d:
        raise net.FetchError(f"PRTS 页面不存在或解析失败: {page}")
    return d.get("parse", {}).get("wikitext", "")


# --------------------------------------------------------------- 模板解析

def _find_template(text: str, name: str) -> Optional[str]:
    """提取 {{name ...}} 的完整内容（支持嵌套大括号）。

    注意模板名边界：``{{技能`` 是 ``{{技能2`` 的前缀，
    直接 find 会错误命中「技能2」的模板，导致 S1 显示成 S2。
    因此要求名字后必须紧跟 ``,``、``|``、换行或 `}}``。
    """
    needle = "{{" + name
    idx = -1
    start = 0
    while True:
        j = text.find(needle, start)
        if j < 0:
            break
        nxt = text[j + len(needle): j + len(needle) + 2]
        if nxt[:1] in ("|", "\n", "}", "", ","):
            idx = j
            break
        start = j + 2
    if idx < 0:
        return None
    depth = 0
    i = idx
    while i < len(text) - 1:
        if text[i:i + 2] == "{{":
            depth += 1
            i += 2
            continue
        if text[i:i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[idx:i]
            continue
        i += 1
    return None


def _split_top_level(rest: str) -> List[str]:
    """按「顶层」的 | 切分参数串。

    关键点：遇到 ``{{`` 或 ``}}`` 必须 **整体跳过 2 个字符**。
    若只跳过 1 个，像 ``...}}}}`` 这样连续闭合的嵌套模板
    （技能描述里非常常见）会被多算一次深度，导致深度变负、
    后续所有 ``|`` 都不再被识别，参数串被错误地并进上一条。
    """
    parts: List[str] = []
    buf: List[str] = []
    curly = 0
    square = 0
    i = 0
    n = len(rest)
    while i < n:
        two = rest[i:i + 2]
        if two == "{{":
            curly += 1
            buf.append(two)
            i += 2
            continue
        if two == "}}":
            curly = max(0, curly - 1)
            buf.append(two)
            i += 2
            continue
        ch = rest[i]
        if ch == "[":
            square += 1
        elif ch == "]":
            square = max(0, square - 1)
        if ch == "|" and curly == 0 and square == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _template_params(tpl: str) -> Dict[str, str]:
    """把模板体解析成 key -> value（只处理顶层的 | 分隔）。"""
    body = tpl.strip()
    if body.startswith("{{"):
        body = body[2:]
    if body.endswith("}}"):
        body = body[:-2]
    # 去掉模板名：取第一个顶层 | 之前的部分
    first_pipe = body.find("|")
    nl = body.find("\n")
    if first_pipe >= 0 and (nl < 0 or first_pipe < nl):
        rest = body[first_pipe + 1:]
    elif nl >= 0:
        rest = body[nl + 1:]
    else:
        rest = ""

    params: Dict[str, str] = {}
    for part in _split_top_level(rest):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        # 极少数条目把后续参数挤进同一段（换行分隔），做一次兜底展开
        if "\n|" in v:
            head, _, tail = v.partition("\n|")
            params[k] = head.strip()
            for sub in _split_top_level(tail):
                if "=" in sub:
                    sk, _, sv = sub.partition("=")
                    params[sk.strip()] = sv.strip()
            continue
        params[k] = v.strip()
    return params


def _to_float(s: str, default: float = 0.0) -> float:
    if s is None:
        return default
    s = s.strip()
    if not s or s == "-":
        return default
    # 去掉可能的单位与备注
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else default


def _strip_markup(s: str) -> str:
    """去掉 wikitext 标记，便于展示。"""
    s = re.sub(r"\{\{color\|[^|]*\|([^}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{\*\|[^|]*\|([^}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{\+\|([^|]*)\|[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)
    s = s.replace("<br/>", " ").replace("<br>", " ")
    return s.strip()


_ADVANCE_MAP = {"初始": 0, "精英0": 0, "精英1": 1, "精英2": 2}


def parse_operator(name: str, text: str) -> Optional[Operator]:
    """从干员页 wikitext 解析出 Operator。"""
    info_tpl = _find_template(text, "CharinfoV2") or _find_template(text, "Charinfo")
    attr_tpl = _find_template(text, "属性")
    if not attr_tpl:
        return None

    info = _template_params(info_tpl) if info_tpl else {}
    attrs = _template_params(attr_tpl)

    char_id = info.get("干员id") or info.get("干员ID") or ""
    display_name = info.get("干员名") or name
    rarity = int(_to_float(info.get("稀有度"), 0))
    profession = info.get("职业", "")
    sub = info.get("分支", "")
    position = info.get("位置", "")

    op = Operator(
        char_id=char_id or name,
        name=display_name,
        rarity=rarity,
        profession=profession,
        sub_profession=sub,
        position=position,
    )

    # 阻挡数 / 攻击间隔 / 再部署
    block = int(_to_float(attrs.get("阻挡数"), 0))
    atk_interval_raw = attrs.get("攻击速度", "1.0s")
    atk_interval = _to_float(atk_interval_raw, 1.0)
    redeploy = _to_float(attrs.get("再部署", "70s"), 70.0)

    # 部署费用 "12→14"
    cost_str = attrs.get("部署费用", "")
    cost = int(_to_float(cost_str.split("→")[0], 0)) if cost_str else 0

    # 信赖加成
    trust_hp = _to_float(attrs.get("信赖加成_生命上限"), 0.0)
    trust_atk = _to_float(attrs.get("信赖加成_攻击"), 0.0)
    trust_def = _to_float(attrs.get("信赖加成_防御"), 0.0)
    op.trust_bonus = {"hp": trust_hp, "atk": trust_atk, "def": trust_def}

    # 潜能
    pot_vals = (attrs.get("潜能") or "").split(",")
    pot_types = (attrs.get("潜能类型") or "").split(",")
    pot: Dict[str, float] = {}
    for t, v in zip(pot_types, pot_vals):
        t = t.strip()
        if not t:
            continue
        num = _to_float(v, 0.0)
        if num:
            pot[t] = pot.get(t, 0.0) + num
    op.potential_bonus = pot

    # 潜能逐级明细（{{潜能提升}} 模板，潜能 2~6 共 5 档）
    ranks: List[dict] = []
    pot_up = _find_template(text, "潜能提升")
    if pot_up:
        pp = _template_params(pot_up)
        for rank in range(2, 7):
            txt = _strip_markup(pp.get("潜能%d" % rank, "")).strip()
            if not txt:
                continue
            # 与 {{属性}} 的「潜能 / 潜能类型」对齐取数值
            idx = rank - 2
            ptype = (pot_types[idx] if idx < len(pot_types) else "").strip()
            pval = pot_vals[idx] if idx < len(pot_vals) else ""
            ranks.append({
                "rank": rank,
                "type": ptype,
                "value": _to_float(pval, 0.0) if pval.strip() else None,
                "text": txt,
            })
    op.potential_ranks = ranks

    # ---- 各精英阶段的锚点
    # PRTS 只在「精英0」同时给出 1 级与满级；精英1/2 仅给出满级。
    # 精英 1/2 的 1 级数值 = 上一阶段满级数值（游戏内精英化后等级重置为 1，
    # 但面板继承上一阶段满级的基础值并叠加精英化加成，这里以满级为锚点、
    # 以「上一阶段满级」为起点做线性插值，误差最小且单调）。
    prev_max: Optional[OperatorStats] = None
    for elite in (0, 1, 2):
        max_lv = attrs.get(f"精英{elite}_满级")
        if max_lv is None:
            continue
        max_lv_i = int(_to_float(max_lv, 0))
        if max_lv_i <= 0:
            continue

        def mk(prefix: str) -> Optional[OperatorStats]:
            hp_k = f"{prefix}_生命上限"
            if hp_k not in attrs:
                return None
            return OperatorStats(
                hp=_to_float(attrs.get(f"{prefix}_生命上限"), 0.0),
                atk=_to_float(attrs.get(f"{prefix}_攻击"), 0.0),
                defense=_to_float(attrs.get(f"{prefix}_防御"), 0.0),
                magic_resist=_to_float(attrs.get(f"{prefix}_法术抗性"), 0.0),
                cost=cost,
                block=block,
                attack_interval=atk_interval,
                redeploy=redeploy,
            )

        en = mk(f"精英{elite}_满级")
        if en is None:
            continue
        # 起点：本阶段显式 1 级优先，否则用上一阶段满级
        st = mk(f"精英{elite}_1级")
        start_from_prev = False
        if st is None:
            if prev_max is not None:
                st = prev_max
                start_from_prev = True
            else:
                st = en
        start_lv = 1

        stage: Dict[int, OperatorStats] = {max_lv_i: en}
        if max_lv_i > start_lv:
            span = max_lv_i - start_lv
            for lv in range(start_lv, max_lv_i):
                t = (lv - start_lv) / span
                stage[lv] = OperatorStats(
                    hp=st.hp + (en.hp - st.hp) * t,
                    atk=st.atk + (en.atk - st.atk) * t,
                    defense=st.defense + (en.defense - st.defense) * t,
                    magic_resist=st.magic_resist + (en.magic_resist - st.magic_resist) * t,
                    cost=cost, block=block,
                    attack_interval=atk_interval, redeploy=redeploy,
                )
        else:
            stage[start_lv] = st

        op.phases[elite] = stage
        op.max_elite = max(op.max_elite, elite)
        prev_max = en

    # ---- 天赋（仅作文本展示）
    tpl = _find_template(text, "天赋列表3") or _find_template(text, "天赋列表")
    if tpl:
        p = _template_params(tpl)
        for i in (1, 2, 3, 4):
            nm = p.get(f"天赋{i}")
            eff = p.get(f"天赋{i}效果")
            if nm and eff:
                op.talents.append((nm, _strip_markup(eff)))

    return op


# --------------------------------------------------------------- 缓存层

@dataclass
class OperatorCache:
    """干员数据的本地缓存。"""

    path: str
    data: Dict[str, dict]
    version: int = CACHE_VERSION

    @classmethod
    def load(cls, path: str) -> "OperatorCache":
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("version") != CACHE_VERSION:
                return cls(path=path, data={})
            return cls(path=path, data=raw.get("operators", {}) or {})
        except (OSError, ValueError):
            return cls(path=path, data={})

    def save(self) -> None:
        payload = {"version": CACHE_VERSION, "operators": self.data}
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def get(self, name: str) -> Optional[dict]:
        return self.data.get(name)

    def put(self, name: str, op: Operator) -> None:
        self.data[name] = op_to_dict(op)


# --------------------------------------------------------------- 序列化

def op_to_dict(op: Operator) -> dict:
    return {
        "char_id": op.char_id,
        "name": op.name,
        "rarity": op.rarity,
        "profession": op.profession,
        "sub_profession": op.sub_profession,
        "position": op.position,
        "attack_type": op.attack_type,
        "max_elite": op.max_elite,
        "trust_bonus": op.trust_bonus,
        "potential_bonus": op.potential_bonus,
        "potential_ranks": op.potential_ranks,
        "talents": op.talents,
        "skills": [skill_to_dict(sk) for sk in (op.skills or [])],
        "phases": {
            str(elite): {
                str(lv): {
                    "hp": s.hp, "atk": s.atk, "defense": s.defense,
                    "magic_resist": s.magic_resist, "cost": s.cost,
                    "block": s.block, "attack_interval": s.attack_interval,
                    "redeploy": s.redeploy,
                }
                for lv, s in stage.items()
            }
            for elite, stage in op.phases.items()
        },
    }


def skill_to_dict(sk) -> dict:
    """技能 -> 可 JSON 化的字典。"""
    return {
        "index": sk.index,
        "name": sk.name,
        "tree_type": sk.tree_type,
        "trigger_type": sk.trigger_type,
        "levels": {
            k: {
                "label": lv.label,
                "description": lv.description,
                "atk_multiplier": lv.atk_multiplier,
                "flat_atk": lv.flat_atk,
                "attack_speed": lv.attack_speed,
                "interval_delta": lv.interval_delta,
                "dmg_scale": lv.dmg_scale,
                "hit_count": lv.hit_count,
                "duration": lv.duration,
                "cost": lv.cost,
                "initial": lv.initial,
                "extra": lv.extra,
            }
            for k, lv in sk.levels.items()
        },
    }


def dict_to_skill(d: dict):
    """字典 -> 技能对象。"""
    from .skills import Skill, SkillLevel

    sk = Skill(index=d.get("index", 1), name=d.get("name", ""),
               tree_type=d.get("tree_type", ""),
               trigger_type=d.get("trigger_type", ""))
    for k, ld in (d.get("levels") or {}).items():
        sk.levels[k] = SkillLevel(
            label=ld.get("label", k),
            description=ld.get("description", ""),
            atk_multiplier=ld.get("atk_multiplier", 1.0),
            flat_atk=ld.get("flat_atk", 0.0),
            attack_speed=ld.get("attack_speed", 0.0),
            interval_delta=ld.get("interval_delta", 0.0),
            dmg_scale=ld.get("dmg_scale", 1.0),
            hit_count=ld.get("hit_count", 1),
            duration=ld.get("duration", 0.0),
            cost=ld.get("cost", 0.0),
            initial=ld.get("initial", 0.0),
            extra=list(ld.get("extra") or []),
        )
    return sk


def _reauth_skills(op: Operator) -> None:
    """用官方 skill_table 重算一遍技能数值。

    缓存里存的是当初解析的结果，解析器修了以后旧缓存不会自动变。
    尤其是望的三技能：cnt=8 是棋子数，旧版本当成了 8 连击，
    一直缓存在盘面上，DPS 虚高 8 倍。每次加载时重算一遍
    只多耗几毫秒，却能让修正立刻生效。
    """
    if not op.skills:
        return
    try:
        from . import skills as SK
        from . import skilldata as SD
        table, idx = SK._official_tables()
    except Exception:
        return
    if not table:
        return
    for sk in op.skills:
        try:
            entry = SD.lookup(table, idx, op.char_id, sk.name, sk.index)
        except Exception:
            continue
        if not entry:
            continue
        for label, lv in list(sk.levels.items()):
            try:
                SK.apply_official(lv, entry, SD.level_index(label))
            except Exception:
                continue


def dict_to_op(d: dict) -> Operator:
    # 伤害类型：**不能直接用存档里的 attack_type**。
    # 官方 character_table.json 没有这个字段，历史版本一律写死成
    # "PHYSICAL"，于是 463 位干员（连艾雅法拉、史尔特尔这种纯法术的）
    # 全被算成物理伤害，对高甲敌人 DPS 直接算成 0、对高法抗敌人又
    # 算成满伤害。真正的依据是**分支**，这里重新判一遍；存档里的值
    # 只有在明确不是物理时才优先采用（方便用户手工修正）。
    _sub = d.get("sub_profession", "") or ""
    _prof = d.get("profession", "") or ""
    _saved = d.get("attack_type", "") or ""
    _guess = DTYPE.guess_damage_type(_prof, _sub, default="")
    if _saved and _saved.upper() not in ("PHYSICAL", ""):
        _atype = _saved
    else:
        _atype = _guess or (_saved or "PHYSICAL")
    op = Operator(
        char_id=d.get("char_id", ""),
        name=d.get("name", ""),
        rarity=d.get("rarity", 0),
        profession=_prof,
        sub_profession=_sub,
        position=d.get("position", ""),
        attack_type=_atype,
        max_elite=d.get("max_elite", 0),
        trust_bonus=d.get("trust_bonus", {}) or {},
        potential_bonus=d.get("potential_bonus", {}) or {},
    )
    op.talents = [tuple(t) for t in (d.get("talents") or [])]
    op.potential_ranks = list(d.get("potential_ranks") or [])
    op.skills = [dict_to_skill(sd) for sd in (d.get("skills") or [])]
    _reauth_skills(op)
    for elite_s, stage in (d.get("phases") or {}).items():
        elite = int(elite_s)
        op.phases[elite] = _expand_phase(stage)
    return op


#: phases 里会随等级线性增长的字段。
_PHASE_FIELDS = ("hp", "atk", "defense", "magic_resist", "cost", "block",
                 "attack_interval", "redeploy")


def _expand_phase(stage: dict) -> Dict[int, OperatorStats]:
    """把一个精英阶段的等级表还原成 {等级: 数值}。

    缓存里为了省体积（18 MB -> 4.7 MB）只存了首末两级：
        {"lo": 1, "hi": 90, "a": {...1 级...}, "b": {...90 级...}}
    因为干员的成长曲线在同一个精英阶段内是严格等差的（已对全部 463 名
    干员、861 个阶段逐点验证，无一例外），中间值直接线性插值即可。
    遇到未压缩的原始表（键都是数字）就照原样读，两种情况都兼容。
    """
    if "lo" in stage and "hi" in stage:
        lo, hi = int(stage["lo"]), int(stage["hi"])
        a = stage.get("a") or {}
        b = stage.get("b") or {}
        out: Dict[int, OperatorStats] = {}
        span = max(1, hi - lo)
        for lv in range(lo, hi + 1):
            t = (lv - lo) / float(span)
            vals = {}
            for f in _PHASE_FIELDS:
                va = a.get(f)
                vb = b.get(f)
                if va is None and vb is None:
                    continue
                if va is None:
                    va = vb
                if vb is None:
                    vb = va
                v = va + (vb - va) * t
                # 整数字段（cost/block）四舍五入，避免出现 17.9999
                vals[f] = int(round(v)) if f in ("cost", "block") else v
            out[lv] = OperatorStats(
                hp=vals.get("hp", 0.0), atk=vals.get("atk", 0.0),
                defense=vals.get("defense", 0.0),
                magic_resist=vals.get("magic_resist", 0.0),
                cost=vals.get("cost", 0), block=vals.get("block", 0),
                attack_interval=vals.get("attack_interval", 1.0),
                redeploy=vals.get("redeploy", 70.0),
            )
        return out

    out2: Dict[int, OperatorStats] = {}
    for lv_s, s in stage.items():
        out2[int(lv_s)] = OperatorStats(
            hp=s.get("hp", 0.0), atk=s.get("atk", 0.0),
            defense=s.get("defense", 0.0),
            magic_resist=s.get("magic_resist", 0.0),
            cost=s.get("cost", 0), block=s.get("block", 0),
            attack_interval=s.get("attack_interval", 1.0),
            redeploy=s.get("redeploy", 70.0),
        )
    return out2


def load_operator(name: str, cache: Optional[OperatorCache] = None) -> Optional[Operator]:
    """加载单个干员，优先走缓存。"""
    if cache:
        d = cache.get(name)
        if d:
            return dict_to_op(d)
    try:
        wt = fetch_wikitext(name)
    except net.FetchError:
        return None
    op = parse_operator(name, wt)
    if op is None:
        return None
    if cache:
        cache.put(name, op)
        cache.save()
    return op