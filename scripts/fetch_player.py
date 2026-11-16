#!/usr/bin/env python3
"""從 MLB Stats API 抓一位球員的資料，存成 raw/players/<slug>.json。

用法：
    python3 scripts/fetch_player.py "Tarik Skubal"
    python3 scripts/fetch_player.py --id 669373        # 同名時用 ID 指定

規則（見 CLAUDE.md 第 5、6 節）：
- 這支腳本是球員數字的唯一來源，頁面上的數字都要能在輸出的 JSON 找到。
- 產生的 JSON 不可手改；要更新就重跑腳本。
- 只用 Python 標準函式庫，不需安裝任何套件。
"""
import argparse
import datetime as dt
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://statsapi.mlb.com/api/v1"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw" / "players"
TEAMS = json.loads((ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]

INFIELD = {"1B", "2B", "3B", "SS"}
OUTFIELD = {"LF", "CF", "RF", "OF"}


def get(path, **params):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "mlb-player-notes/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return "-".join(s.split())


def completed_seasons(n=3):
    """最近 n 個「已結束」的例行賽季。"""
    today = dt.date.today()
    info = get(f"/seasons/{today.year}", sportId=1)["seasons"][0]
    end = dt.date.fromisoformat(info["regularSeasonEndDate"])
    last = today.year if today > end else today.year - 1
    return [last - i for i in range(n - 1, -1, -1)]


def search(name):
    people = get("/people/search", names=name).get("people", [])
    active = [p for p in people if p.get("active")]
    return active or people


def ft_in_to_cm(h):
    # API 格式：6' 3"
    try:
        ft, inch = h.replace('"', "").split("'")
        return round((int(ft) * 12 + int(inch.strip() or 0)) * 2.54)
    except (ValueError, AttributeError):
        return None


def pick_total(splits):
    """一季待過多隊時，API 會給各隊的 split；有無隊名的合計 split 就用它，否則只有一隊。"""
    if not splits:
        return None, []
    teams = [s["team"]["name"] for s in splits if "team" in s]
    total = [s for s in splits if "team" not in s]
    chosen = total[0] if total else splits[0]
    return chosen, teams


def pct(a, b):
    return round(a / b * 100, 1) if b else None


def season_stats(pid, group, season):
    data = get(f"/people/{pid}/stats", stats="season,sabermetrics", group=group, season=season)
    out = {}
    for block in data.get("stats", []):
        kind = block["type"]["displayName"]
        split, teams = pick_total(block.get("splits", []))
        if split is None:
            continue
        out[kind] = split["stat"]
        if kind == "season":
            out["teams"] = teams
    if "season" not in out:
        return None  # 該季未出賽
    s = out["season"]
    row = {
        "season": season,
        "teams": out.get("teams", []),
        "team_label": "2TM" if len(out.get("teams", [])) == 2 else
                      (f"{len(out['teams'])}TM" if len(out.get("teams", [])) > 2 else None),
        "stat": s,
        "sabermetrics": out.get("sabermetrics", {}),
    }
    if group == "hitting":
        row["derived"] = {
            "bb_pct": pct(s.get("baseOnBalls", 0), s.get("plateAppearances", 0)),
            "k_pct": pct(s.get("strikeOuts", 0), s.get("plateAppearances", 0)),
        }
    else:
        row["derived"] = {
            "k_pct": pct(s.get("strikeOuts", 0), s.get("battersFaced", 0)),
            "bb_pct": pct(s.get("baseOnBalls", 0), s.get("battersFaced", 0)),
            "gs_ratio": round(s.get("gamesStarted", 0) / s["gamesPitched"], 2) if s.get("gamesPitched") else None,
        }
    # 只保留有意義的 sabermetrics 欄位，數值四捨五入
    keep = ["war", "wRcPlus", "woba", "fip", "xfip", "fipMinus", "eraMinus"]
    row["sabermetrics"] = {k: round(v, 3 if k == "woba" else 2) for k, v in row["sabermetrics"].items()
                           if k in keep and isinstance(v, (int, float))}
    return row


def pitch_arsenal(pid, season):
    data = get(f"/people/{pid}/stats", stats="pitchArsenal", group="pitching", season=season)
    pitches = []
    for block in data.get("stats", []):
        for sp in block.get("splits", []):
            st = sp["stat"]
            pitches.append({
                "code": st["type"]["code"],
                "name": st["type"]["description"],
                "usage_pct": round(st["percentage"] * 100, 1),
                "avg_mph": round(st["averageSpeed"], 1),
                "count": st["count"],
            })
    pitches.sort(key=lambda p: -p["usage_pct"])
    return {"season": season, "pitches": pitches} if pitches else None


def position_group(pos_abbr, pitching):
    """依 CLAUDE.md 第 7 節的規則決定首頁分組。"""
    if pos_abbr == "TWP":
        return "two-way"
    if pos_abbr == "P":
        latest = next((r for r in reversed(pitching) if r), None) if pitching else None
        ratio = latest["derived"]["gs_ratio"] if latest else None
        return "starter" if ratio is not None and ratio > 0.5 else "reliever"
    if pos_abbr == "C":
        return "catcher"
    if pos_abbr in INFIELD:
        return "infield"
    if pos_abbr in OUTFIELD:
        return "outfield"
    if pos_abbr == "DH":
        return "dh"
    return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?", help="球員英文名")
    ap.add_argument("--id", type=int, help="MLBAM 球員 ID（同名時使用）")
    args = ap.parse_args()

    if args.id:
        pid = args.id
    elif args.name:
        cands = search(args.name)
        if not cands:
            sys.exit(f"找不到球員：{args.name}")
        if len(cands) > 1:
            print("找到多位符合的球員，請用 --id 指定：", file=sys.stderr)
            for p in cands:
                print(f"  --id {p['id']}  {p['fullName']}  {p.get('primaryPosition', {}).get('abbreviation', '?')}"
                      f"  生於 {p.get('birthDate', '?')}  {'現役' if p.get('active') else '非現役'}", file=sys.stderr)
            sys.exit(2)
        pid = cands[0]["id"]
    else:
        ap.error("請提供球員英文名或 --id")

    p = get(f"/people/{pid}", hydrate="awards,draft,currentTeam")["people"][0]
    pos = p.get("primaryPosition", {}).get("abbreviation")
    seasons = completed_seasons()

    want_hit = pos != "P"
    want_pitch = pos in ("P", "TWP")
    hitting = [season_stats(pid, "hitting", y) for y in seasons] if want_hit else None
    pitching = [season_stats(pid, "pitching", y) for y in seasons] if want_pitch else None
    arsenal = None
    if want_pitch:
        for y in reversed(seasons):
            arsenal = pitch_arsenal(pid, y)
            if arsenal:
                break

    team_id = str(p.get("currentTeam", {}).get("id", ""))
    team = TEAMS.get(team_id)

    slug = slugify(p["fullName"])
    existing = RAW_DIR / f"{slug}.json"
    if existing.exists() and json.loads(existing.read_text(encoding="utf-8"))["mlbam_id"] != pid:
        slug = f"{slug}-{pid}"

    weight = p.get("weight")
    record = {
        "_note": "由 scripts/fetch_player.py 自動產生，請勿手改。要更新請重跑腳本。",
        "slug": slug,
        "mlbam_id": pid,
        "fetched_at": dt.date.today().isoformat(),
        "seasons": seasons,
        "sources": {
            "api": f"{API}/people/{pid}",
            "mlb_com": f"https://www.mlb.com/player/{p.get('nameSlug', pid)}",
            "baseball_reference": "https://www.baseball-reference.com/search/search.fcgi?search="
                                  + urllib.parse.quote(p["fullName"]),
        },
        "bio": {
            "full_name": p["fullName"],
            "first_name": p.get("useName") or p.get("firstName"),
            "last_name": p.get("lastName"),
            "number": p.get("primaryNumber"),
            "position": pos,
            "position_name": p.get("primaryPosition", {}).get("name"),
            "bats": p.get("batSide", {}).get("code"),
            "throws": p.get("pitchHand", {}).get("code"),
            "birth_date": p.get("birthDate"),
            "age": p.get("currentAge"),
            "birth_place": ", ".join(x for x in [p.get("birthCity"), p.get("birthStateProvince"),
                                                  p.get("birthCountry")] if x),
            "height": p.get("height"),
            "height_cm": ft_in_to_cm(p.get("height")),
            "weight_lb": weight,
            "weight_kg": round(weight * 0.4536) if weight else None,
            "mlb_debut": p.get("mlbDebutDate"),
        },
        "current_team": {"id": int(team_id), **team} if team else None,
        "position_group": position_group(pos, pitching),
        "awards": [{"name": a["name"], "season": a["season"]} for a in p.get("awards", [])],
        "draft": [{"year": d["year"], "round": d["pickRound"], "pick": d["pickNumber"],
                   "team": d["team"]["name"], "school": d.get("school", {}).get("name")}
                  for d in p.get("drafts", [])],
        "hitting": hitting,
        "pitching": pitching,
        "pitch_arsenal": arsenal,
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{slug}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    team_txt = f"{team['abbr']} {team['zh']}" if team else "無現役球隊（待確認）"
    print(f"已寫入 {out.relative_to(ROOT)}")
    print(f"  {p['fullName']}  #{p.get('primaryNumber', '?')}  {pos}  {team_txt}  分組={record['position_group']}")
    for label, rows in (("打擊", hitting), ("投球", pitching)):
        if rows is None:
            continue
        for y, r in zip(seasons, rows):
            print(f"  {label} {y}: {'未出賽' if r is None else f'G={r['stat'].get('gamesPlayed')}'}")


if __name__ == "__main__":
    main()
