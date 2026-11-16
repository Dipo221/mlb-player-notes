# MLB 球員觀察筆記（MLB Player Notes）

一頁一位 MLB 球員：基本資料、近三季數據、打法特色，以及我自己的觀察。

- 網站：https://dipo221.github.io/mlb-player-notes/
- AI 專案規則（員工手冊）：[CLAUDE.md](CLAUDE.md)（其他 AI 工具請看 [AGENTS.md](AGENTS.md)）
- 做球員頁的 SOP（skill）：[.claude/skills/player-page/SKILL.md](.claude/skills/player-page/SKILL.md)

## 這個專案怎麼長大

對 AI 說一句「新增球員：XXX」，AI 會依 CLAUDE.md：

1. `scripts/fetch_player.py` 從 MLB Stats API 抓資料，存到 `raw/players/<slug>.json`
2. `scripts/new_page.py` 用 skill 的版型產生頁面，數據表由腳本填入（避免手抄錯誤）
3. AI 依 skill 的寫作規則補上定位、生涯簡介、數據解讀、打法特色
4. 把新卡片放進首頁對應的位置分組，更新球員總數與日期
5. `scripts/check_site.py` 驗收：數字和 JSON 逐字比對、連結、分組排序、風格規則

## 本機預覽

```bash
python3 -m http.server 8000   # 然後打開 http://localhost:8000
python3 scripts/check_site.py # 驗收檢查
```

## 資料與版權

數據來自 MLB Stats API（© MLB Advanced Media），僅作個人學習筆記使用。
網站不使用官方球員照片與球隊 logo，球員卡以球隊代表色＋背號呈現。
