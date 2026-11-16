#!/usr/bin/env python3
"""用 skill 的版型產生球員頁骨架，或更新既有頁面的資料區塊。

用法：
    python3 scripts/new_page.py tarik-skubal            # 新頁：資料區塊填好，文字段落留 TODO-AI
    python3 scripts/new_page.py tarik-skubal --update   # 既有頁：只替換資料區塊，AI 寫的文字不動
    python3 scripts/new_page.py tarik-skubal --card     # 只印出首頁卡片 HTML 與應放的分組

做完新頁之後，AI 要把頁面裡所有 TODO-AI 換成內容（規則見 SKILL.md），
再把 --card 印出的卡片貼進 index.html 對應分組。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402

ROOT = blocks.ROOT
TEMPLATE = ROOT / ".claude" / "skills" / "player-page" / "template.html"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--update", action="store_true", help="只更新既有頁面的資料區塊")
    g.add_argument("--card", action="store_true", help="印出首頁卡片 HTML")
    args = ap.parse_args()

    d = blocks.load(args.slug)
    page = ROOT / "pages" / "players" / f"{args.slug}.html"
    data = blocks.render_all(d)

    if args.card:
        print(f"分組：{d['position_group']}（{blocks.GROUP_ZH[d['position_group']]}）")
        print(blocks.index_card(d))
        return

    if args.update:
        if not page.exists():
            sys.exit(f"找不到 {page.relative_to(ROOT)}，新頁請不要加 --update。")
        html = page.read_text(encoding="utf-8")
        for name, block in data.items():
            pat = re.compile(rf"<!-- data:{name}:start -->.*?<!-- data:{name}:end -->", re.S)
            if not pat.search(html):
                sys.exit(f"頁面缺少資料區塊 {name}，請檢查。")
            html = pat.sub(lambda _: block, html)
        html = re.sub(r"資料截至 \d{4}-\d{2}-\d{2}", f"資料截至 {d['fetched_at']}", html)
        html = re.sub(r'(<main class="page player" style=")[^"]*(")', rf"\g<1>{blocks.team_vars(d)}\g<2>", html)
        page.write_text(html, encoding="utf-8")
        print(f"已更新資料區塊：{page.relative_to(ROOT)}（文字段落未變動，請檢查數據解讀是否需要改寫）")
        return

    if page.exists():
        sys.exit(f"{page.relative_to(ROOT)} 已存在。更新數據請加 --update；不可覆蓋既有頁面。")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = (html.replace("{{FULL_NAME}}", blocks.esc(d["bio"]["full_name"]))
                .replace("{{FETCHED_AT}}", d["fetched_at"])
                .replace("{{TEAM_VARS}}", blocks.team_vars(d)))
    for name, block in data.items():
        html = html.replace("{{" + name + "}}", block)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")
    n = html.count("TODO-AI")
    print(f"已建立 {page.relative_to(ROOT)}，還有 {n} 處 TODO-AI 要依 SKILL.md 填寫。")


if __name__ == "__main__":
    main()
