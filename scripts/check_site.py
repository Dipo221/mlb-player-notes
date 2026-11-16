#!/usr/bin/env python3
"""驗收檢查（CLAUDE.md 第 10 節）。全部通過才算完成；有錯誤時 exit code 為 1。

檢查項目：
  1. 每位球員 raw/players/<slug>.json、<slug>.md、pages/players/<slug>.html 三個檔案齊全
  2. 球員頁沒有殘留 TODO-AI，且 8 個固定段落都在、順序正確
  3. 球員頁的資料區塊和 JSON 重新計算的結果完全一致（數字不可手改）
  4. 首頁每位球員都有卡片、卡片內容和 JSON 一致、每個連結都指到存在的檔案
  5. 首頁分組順序正確、組內依姓氏排序、「共 N 位球員」數字正確
  6. 所有 HTML 在 <head> 載入 theme.js（深色模式），沒有 <style>、沒有非變數的行內 style、沒有本機絕對路徑、沒有外部 script/css
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402

ROOT = blocks.ROOT
SECTIONS = ["card", "bio", "stats", "analysis", "style", "mine", "sources"]
errors, warnings = [], []


def err(msg):
    errors.append(msg)


def check_common(path, html):
    rel = path.relative_to(ROOT)
    if re.search(r"<style", html, re.I):
        err(f"{rel}: 不可使用 <style>，樣式請寫在 assets/css/site.css")
    for m in re.finditer(r'style="([^"]*)"', html):
        decls = [x.strip() for x in m.group(1).split(";") if x.strip()]
        if any(not x.startswith("--") for x in decls):
            err(f"{rel}: 行內 style 只能設定 CSS 變數：{m.group(0)[:60]}")
    if re.search(r"(/home/|file://|\b[A-Za-z]:\\[A-Za-z]|/Users/)", html):
        err(f"{rel}: 出現本機絕對路徑")
    if not re.search(r'<head>.*<script src="[./]*assets/js/theme\.js"></script>.*</head>', html, re.S):
        err(f"{rel}: <head> 裡缺少 assets/js/theme.js（深色模式）")
    for m in re.finditer(r'<(?:script|link)[^>]+(?:src|href)="(https?:)?//', html):
        err(f"{rel}: 不可載入外部資源：{m.group(0)[:60]}")
    for m in re.finditer(r'(?:href|src)="([^"#:]+?)(?:#[^"]*)?"', html):
        target = (path.parent / m.group(1)).resolve()
        if not target.exists():
            err(f"{rel}: 連結指到不存在的檔案 {m.group(1)}")


def check_page(slug, d):
    path = ROOT / "pages" / "players" / f"{slug}.html"
    html = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    check_common(path, html)
    if "TODO-AI" in html:
        err(f"{rel}: 還有 {html.count('TODO-AI')} 處 TODO-AI 沒填")
    pos = [html.find(f'id="{s}"') for s in SECTIONS]
    if -1 in pos:
        err(f"{rel}: 缺少段落 {[s for s, p in zip(SECTIONS, pos) if p == -1]}")
    elif pos != sorted(pos):
        err(f"{rel}: 段落順序不對，應為 {SECTIONS}")
    for name, block in blocks.render_all(d).items():
        m = re.search(rf"<!-- data:{name}:start -->.*?<!-- data:{name}:end -->", html, re.S)
        if not m:
            err(f"{rel}: 缺少資料區塊 {name}")
        elif m.group(0) != block:
            err(f"{rel}: 資料區塊 {name} 和 JSON 不一致（請用 new_page.py --update 重新產生，不要手改）")
    if f"資料截至 {d['fetched_at']}" not in html:
        err(f"{rel}: 「資料截至」日期和 JSON 的 fetched_at 不一致")
    if blocks.team_vars(d) not in html:
        err(f"{rel}: <main> 的球隊色變數和 data/teams.json 不一致")
    name = blocks.esc(d["bio"]["full_name"])
    if f"<h1>{name}</h1>" not in html or f"<title>{name}｜" not in html:
        err(f"{rel}: <title> 與 <h1> 必須是球員英文全名 {d['bio']['full_name']}")
    m = re.search(r'<p class="tagline">(.*?)</p>', html, re.S)
    if m and len(re.sub(r"<[^>]+>", "", m.group(1)).strip()) > 30:
        err(f"{rel}: 一句話定位超過 30 字")
    if 'class="todo">待補' in html:
        warnings.append(f"{rel}: 「我的觀察」待補")
    if "待確認" in html:
        warnings.append(f"{rel}: 有「待確認」項目")


def surname_key(d):
    return (d["bio"].get("last_name") or d["bio"]["full_name"]).lower()


def check_index(players):
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    check_common(path, html)

    m = re.search(r"共 (\d+) 位球員", html)
    if not m or int(m.group(1)) != len(players):
        err(f"index.html: 「共 N 位球員」應為 {len(players)}")

    linked = set(re.findall(r'href="pages/players/([a-z0-9-]+)\.html"', html))
    for slug in players:
        if slug not in linked:
            err(f"index.html: 沒有連到 {slug}")
    for slug in linked - set(players):
        err(f"index.html: 連到不存在的球員 {slug}")

    # 分組順序與組內排序
    groups = re.findall(r'<section class="group" id="g-([a-z-]+)">(.*?)</section>', html, re.S)
    order = [g for g, _ in groups]
    expected_order = [g for g in blocks.GROUP_ORDER if g in order]
    if order != expected_order:
        err(f"index.html: 分組順序應為 {expected_order}，目前為 {order}")
    for g, body in groups:
        slugs = re.findall(r'href="pages/players/([a-z0-9-]+)\.html"', body)
        if not slugs:
            err(f"index.html: 分組 {g} 沒有球員，空分組不應顯示")
        for s in slugs:
            if s in players and players[s]["position_group"] != g:
                err(f"index.html: {s} 應放在分組 {players[s]['position_group']}，目前在 {g}")
        keys = [surname_key(players[s]) for s in slugs if s in players]
        if keys != sorted(keys):
            err(f"index.html: 分組 {g} 沒有依英文姓氏排序")

    # 卡片內容要和 JSON 一致
    for slug, d in players.items():
        card = blocks.index_card(d)
        if card not in html:
            err(f"index.html: {slug} 的卡片和 JSON 不一致（請用 new_page.py {slug} --card 重新產生）")


def main():
    raw = ROOT / "raw" / "players"
    pages = ROOT / "pages" / "players"
    slugs = sorted({p.stem for p in raw.glob("*.json")} | {p.stem for p in raw.glob("*.md")}
                   | {p.stem for p in pages.glob("*.html")})
    players = {}
    for slug in slugs:
        missing = [str(p.relative_to(ROOT)) for p in
                   (raw / f"{slug}.json", raw / f"{slug}.md", pages / f"{slug}.html") if not p.exists()]
        if missing:
            err(f"{slug}: 缺少檔案 {missing}")
            continue
        d = blocks.load(slug)
        if d["slug"] != slug:
            err(f"{slug}: JSON 內的 slug 是 {d['slug']}，檔名不一致")
        check_page(slug, d)
        players[slug] = d

    check_index(players)

    print(f"檢查 {len(players)} 位球員")
    for w in warnings:
        print(f"  提醒：{w}")
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        print(f"未通過：{len(errors)} 個錯誤")
        sys.exit(1)
    print("✓ 全部通過")


if __name__ == "__main__":
    main()
