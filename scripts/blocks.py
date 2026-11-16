"""把 raw/players/<slug>.json 轉成頁面上的「資料區塊」HTML。

new_page.py 用它產生頁面；check_site.py 用它重新計算並比對頁面內容，
確保頁面上的數字和 JSON 完全一致（CLAUDE.md 第 6 節「數據鐵則」）。

資料區塊在頁面中用註解包起來：
    <!-- data:<name>:start --> ... <!-- data:<name>:end -->
這些區塊只能由腳本產生，AI 不可手改。
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAMS = json.loads((ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]
TEAM_BY_NAME = {t["en"]: t for t in TEAMS.values()}
TEAM_BY_NAME["Oakland Athletics"] = TEAMS["133"]  # 2024 以前的隊名

GROUP_ZH = {
    "two-way": "二刀流", "starter": "先發投手", "reliever": "後援投手", "catcher": "捕手",
    "infield": "內野手", "outfield": "外野手", "dh": "指定打擊", "unknown": "其他",
}
GROUP_ORDER = ["two-way", "starter", "reliever", "catcher", "infield", "outfield", "dh", "unknown"]
POS_ZH = {
    "P": None, "TWP": "二刀流", "C": "捕手", "1B": "一壘手", "2B": "二壘手", "3B": "三壘手",
    "SS": "游擊手", "LF": "左外野手", "CF": "中外野手", "RF": "右外野手", "OF": "外野手", "DH": "指定打擊",
}
HAND_ZH = {"L": "左", "R": "右", "S": "左右開弓"}
PITCH_ZH = {
    "FF": "四縫線速球", "FA": "速球", "SI": "伸卡球", "FT": "二縫線速球", "FC": "卡特球",
    "SL": "滑球", "ST": "橫掃球", "SV": "滑曲球", "CU": "曲球", "KC": "彈指曲球", "CS": "慢速曲球",
    "CH": "變速球", "FS": "指叉球", "FO": "叉球", "SC": "螺旋球", "KN": "蝴蝶球", "EP": "小便球",
}
ABBR = {
    "G": "出賽場次", "PA": "打席", "AVG": "打擊率", "OBP": "上壘率", "SLG": "長打率",
    "OPS": "整體攻擊指數（OBP＋SLG）", "HR": "全壘打", "RBI": "打點", "SB": "盜壘",
    "BB%": "保送率（保送／打席）", "K%": "三振率", "wRC+": "加權得分創造（100＝聯盟平均）",
    "WAR": "勝場貢獻值", "GS": "先發場次", "IP": "投球局數", "W-L": "勝-敗", "ERA": "防禦率",
    "WHIP": "每局被上壘數", "K/9": "每九局三振", "BB/9": "每九局保送", "FIP": "投手獨立防禦率",
    "SV": "救援成功", "HLD": "中繼成功",
}
API_NOTE = "WAR、wRC+、FIP 為 MLB Stats API 版本，與 FanGraphs／B-Ref 數值可能略有差異。"


def load(slug):
    return json.loads((ROOT / "raw" / "players" / f"{slug}.json").read_text(encoding="utf-8"))


def esc(x):
    return html.escape(str(x), quote=True)


def team_vars(d):
    t = d.get("current_team") or {}
    return f"--team-primary:{t.get('primary', '#1f3a5f')}; --team-secondary:{t.get('secondary', '#c8102e')}"


def role_label(d):
    pos = d["bio"]["position"]
    if pos == "P":
        return GROUP_ZH[d["position_group"]]
    return POS_ZH.get(pos) or pos


def hand_label(b):
    return f"{HAND_ZH.get(b['throws'], '?')}投{HAND_ZH.get(b['bats'], '?')}打"


def wrap(name, body):
    return f"<!-- data:{name}:start -->\n{body}\n<!-- data:{name}:end -->"


# ---------- 球員卡 ----------

def jersey(d):
    t = d.get("current_team") or {}
    return wrap("jersey", f'<div class="jersey"><span class="num">{esc(d["bio"]["number"] or "–")}</span>'
                          f'<span class="abbr">{esc(t.get("abbr", "FA"))}</span></div>')


def pos_line(d):
    return wrap("pos", f'<p class="pos">{esc(role_label(d))}・{esc(hand_label(d["bio"]))}</p>')


def facts(d):
    b, t = d["bio"], d.get("current_team")
    team = f"{t['zh']}（{t['abbr']}）" if t else "待確認"
    hw = f"{b['height_cm']} 公分／{b['weight_kg']} 公斤" if b.get("height_cm") and b.get("weight_kg") else "待確認"
    rows = [
        ("球隊", team),
        ("年齡", f"{b['age']} 歲（{b['birth_date']}）" if b.get("age") else "待確認"),
        ("出生地", b.get("birth_place") or "待確認"),
        ("身高體重", hw),
        ("MLB 初登板", b.get("mlb_debut") or "待確認"),
    ]
    inner = "\n".join(f"  <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in rows)
    return wrap("facts", f'<dl class="facts">\n{inner}\n</dl>')


# ---------- 數據表 ----------

def f3(x):
    """.322 這種 API 字串原樣使用"""
    return x if x not in (None, "") else "–"


def num(x, nd):
    return "–" if x is None else f"{x:.{nd}f}"


def team_cell(row):
    if row["team_label"]:
        return row["team_label"]
    if row["teams"]:
        t = TEAM_BY_NAME.get(row["teams"][0])
        return t["abbr"] if t else row["teams"][0]
    return "–"


def multi_team_note(rows):
    notes = [f"{r['season']} {r['team_label']}＝{'、'.join(r['teams'])}" for r in rows if r and r["team_label"]]
    return "；".join(notes)


HIT_COLS = ["季", "隊", "G", "PA", "AVG", "OBP", "SLG", "OPS", "HR", "RBI", "SB", "BB%", "K%", "wRC+", "WAR"]


def hit_row(r):
    s, sm, dv = r["stat"], r["sabermetrics"], r["derived"]
    return [str(r["season"]), team_cell(r), str(s.get("gamesPlayed", "–")), str(s.get("plateAppearances", "–")),
            f3(s.get("avg")), f3(s.get("obp")), f3(s.get("slg")), f3(s.get("ops")),
            str(s.get("homeRuns", "–")), str(s.get("rbi", "–")), str(s.get("stolenBases", "–")),
            num(dv.get("bb_pct"), 1), num(dv.get("k_pct"), 1),
            num(sm.get("wRcPlus"), 0), num(sm.get("war"), 1)]


def pitch_cols(d):
    cols = ["季", "隊", "G", "GS", "IP", "W-L", "ERA", "WHIP", "K/9", "BB/9", "K%", "FIP", "WAR"]
    return cols + ["SV", "HLD"] if d["position_group"] == "reliever" else cols


def pitch_row(r, d):
    s, sm, dv = r["stat"], r["sabermetrics"], r["derived"]
    row = [str(r["season"]), team_cell(r), str(s.get("gamesPitched", "–")), str(s.get("gamesStarted", "–")),
           f3(s.get("inningsPitched")), f"{s.get('wins', 0)}-{s.get('losses', 0)}",
           f3(s.get("era")), f3(s.get("whip")), f3(s.get("strikeoutsPer9Inn")), f3(s.get("walksPer9Inn")),
           num(dv.get("k_pct"), 1), num(sm.get("fip"), 2), num(sm.get("war"), 1)]
    if d["position_group"] == "reliever":
        row += [str(s.get("saves", 0)), str(s.get("holds", 0))]
    return row


def table(cols, rows, seasons, render):
    head = "".join(f'<th><abbr title="{esc(ABBR[c])}">{esc(c)}</abbr></th>' if c in ABBR else f"<th>{esc(c)}</th>"
                   for c in cols)
    body = []
    for y, r in zip(seasons, rows):
        if r is None:
            body.append(f'<tr><td>{y}</td><td>–</td><td class="dnp" colspan="{len(cols) - 2}">未出賽</td></tr>')
        else:
            body.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in render(r)) + "</tr>")
    return (f'<div class="table-wrap"><table class="stats">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
            + "\n".join(body) + "\n</tbody>\n</table></div>")


def stats(d):
    parts = []
    two = d["hitting"] is not None and d["pitching"] is not None
    if d["hitting"] is not None:
        if two:
            parts.append("<h3>打擊</h3>")
        parts.append(table(HIT_COLS, d["hitting"], d["seasons"], hit_row))
    if d["pitching"] is not None:
        if two:
            parts.append("<h3>投球</h3>")
        parts.append(table(pitch_cols(d), d["pitching"], d["seasons"], lambda r: pitch_row(r, d)))
    notes = [n for n in (multi_team_note(d["hitting"] or []), multi_team_note(d["pitching"] or [])) if n]
    notes = list(dict.fromkeys(notes))  # 二刀流兩張表的註解可能重複
    parts.append(f'<p class="note">{esc("；".join(notes) + "。" if notes else "")}{esc(API_NOTE)}</p>')
    return wrap("stats", "\n".join(parts))


# ---------- 球種 ----------

def arsenal(d):
    a = d.get("pitch_arsenal")
    if not a:
        return wrap("arsenal", "")
    rows = []
    for p in a["pitches"]:
        if p["usage_pct"] < 1.0:
            continue
        name = PITCH_ZH.get(p["code"], p["name"])
        rows.append(f'<div class="pitch"><span class="pname">{esc(name)}</span>'
                    f'<span class="bar"><i style="--w:{p["usage_pct"]}%"></i></span>'
                    f'<span class="pval">{p["usage_pct"]:.1f}%・{p["avg_mph"]:.1f} mph</span></div>')
    return wrap("arsenal", f'<p class="sub">{a["season"]} 球種配比與均速（使用率 1% 以上）</p>\n'
                           f'<div class="arsenal">\n' + "\n".join(rows) + "\n</div>")


# ---------- 資料來源 ----------

def sources(d):
    s = d["sources"]
    return wrap("sources", "<ul>\n"
                f'  <li><a href="{esc(s["api"])}">MLB Stats API</a>（查詢日期 {esc(d["fetched_at"])}）</li>\n'
                f'  <li><a href="{esc(s["mlb_com"])}">MLB.com 球員頁</a></li>\n'
                f'  <li><a href="{esc(s["baseball_reference"])}">Baseball-Reference</a></li>\n'
                "</ul>")


DATA_BLOCKS = {"jersey": jersey, "pos": pos_line, "facts": facts, "stats": stats,
               "arsenal": arsenal, "sources": sources}


def render_all(d):
    return {name: fn(d) for name, fn in DATA_BLOCKS.items()}


# ---------- 首頁卡片 ----------

def latest(rows):
    return next((r for r in reversed(rows or []) if r), None)


def key_stat(d):
    parts = []
    h, p = latest(d["hitting"]), latest(d["pitching"])
    if h:
        parts.append(f"OPS {h['stat'].get('ops', '–')}")
    if p:
        parts.append(f"ERA {p['stat'].get('era', '–')}")
    return "・".join(parts) or "–"


def index_card(d):
    t = d.get("current_team") or {}
    b = d["bio"]
    pos = b["position"] if b["position"] != "P" else ("SP" if d["position_group"] == "starter" else "RP")
    search = " ".join([b["full_name"], t.get("abbr", ""), t.get("zh", ""), role_label(d)]).lower()
    return (f'<a class="mini" href="pages/players/{d["slug"]}.html" data-search="{esc(search)}" style="{team_vars(d)}">'
            f'<span class="mnum">{esc(b["number"] or "–")}</span>'
            f'<span><b>{esc(b["full_name"])}</b><br><small>{esc(t.get("abbr", "FA"))} {esc(t.get("zh", ""))}・{esc(pos)}</small></span>'
            f'<span class="key">{esc(key_stat(d))}</span></a>')

