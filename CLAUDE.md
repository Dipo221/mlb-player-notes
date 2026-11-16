# MLB 球員觀察筆記 — 專案員工手冊

> 每次開新對話，請先完整讀完這份檔案再動手。
> 這份手冊是專案的規則來源；規則改了就改這裡，不要只在對話裡講。
> 做球員頁的細部作法在 `.claude/skills/player-page/SKILL.md`，動手做頁面前也要讀。

## 1. 專案目的

用一頁一位球員的方式，整理我關心的 MLB 球員：基本資料、近三季數據、打法特色，以及我自己的觀察。
使用者之後只要說「新增球員：XXX」（可附一兩句自己的看法），AI 就依本手冊做出新的一頁，並自動更新首頁。

- 範圍：**只收 MLB 球員**，不收中職、日職、韓職或小聯盟球員。
- 語言：繁體中文、台灣用語；數據縮寫保留英文（AVG、ERA…）。
- 網站：純 HTML／CSS／少量原生 JavaScript，放在 GitHub Pages，不使用任何建置工具或外部框架。
- 網址：https://dipo221.github.io/mlb-player-notes/ （repo：github.com/Dipo221/mlb-player-notes）

## 2. 使用者會說的話 → 要做的事

| 使用者說 | 要做的事 |
|---|---|
| 「新增球員：XXX」（可能附上觀察） | 第 4 節「新增流程」全部做完 |
| 「更新球員：XXX」／「更新全部數據」 | 第 4 節「更新流程」，全部數據就每位球員各做一次 |
| 「補觀察：XXX：……」 | 依 skill 第四節，把原話加進頁面與 raw md，附當天日期 |
| 「改風格／改版型」 | 先說明會改哪些檔案、影響哪些頁面，使用者同意後才改 |
| 「推上 GitHub」 | 先列出這次的變更檔案給使用者確認，再 commit 與 push |

## 3. 資料夾結構

```
mlb-player-notes/
├── CLAUDE.md                 ← 本手冊（Claude 自動讀）
├── AGENTS.md                 ← 給其他 AI 工具：請讀 CLAUDE.md
├── README.md                 ← 給人看的專案簡介
├── index.html                ← 首頁：所有球員卡片，依位置分組（AI 每次新增後更新）
├── assets/
│   ├── css/site.css          ← 全站唯一樣式表
│   └── js/search.js          ← 首頁搜尋（新增球員不需修改）
├── data/
│   └── teams.json            ← 30 隊：API ID、縮寫、中文隊名、主色、副色
├── raw/players/
│   ├── <slug>.json           ← fetch 腳本抓下來的原始資料（不可手改）
│   └── <slug>.md             ← 使用者的指令原文、「我的觀察」原話、額外素材
├── pages/players/
│   └── <slug>.html           ← 每位球員一頁
├── scripts/
│   ├── fetch_player.py       ← 從 MLB Stats API 抓資料 → raw/players/<slug>.json
│   ├── blocks.py             ← JSON → 頁面資料區塊 HTML（其他腳本共用）
│   ├── new_page.py           ← 產生頁面骨架／更新資料區塊／印出首頁卡片
│   └── check_site.py         ← 驗收檢查
├── design/style-samples/     ← 定案前比較過的三個風格範例（只供參考，不連到網站）
└── .claude/skills/player-page/
    ├── SKILL.md              ← 「做一頁球員頁」的 SOP 與寫作規則
    └── template.html         ← 球員頁版型骨架
```

腳本只用 Python 3 標準函式庫，不需要安裝套件。

## 4. 命名規則

- **slug**：球員英文全名轉小寫、空白換成 `-`、去掉重音符號與標點（由 `fetch_player.py` 自動產生）。
  例：`Shohei Ohtani` → `shohei-ohtani`；`Bobby Witt Jr.` → `bobby-witt-jr`；`Julio Rodríguez` → `julio-rodriguez`。
- 同名衝突時在後面加 MLBAM ID：`will-smith-669257`。
- 同一位球員的 `raw/players/<slug>.json`、`raw/players/<slug>.md`、`pages/players/<slug>.html` 三個檔案 slug 必須一致。
- 檔名、資料夾名一律英文小寫，不可有空白或中文。

## 5. 流程

### 新增一位球員（一定照順序）

1. **確認是誰**：`python3 scripts/fetch_player.py "英文名"`。腳本若列出多位同名球員（exit code 2），把候選（ID、位置、出生年）給使用者選，再用 `--id` 重跑，不要猜。
2. **存原始資料**：腳本會寫入 `raw/players/<slug>.json`，這個檔案不可手動修改。
3. **存使用者素材**：建立 `raw/players/<slug>.md`（格式見 skill 第五節），記下使用者指令原文與觀察原話。
4. **做頁面**：`python3 scripts/new_page.py <slug>` 產生骨架，再依 skill 第三節把所有 `TODO-AI` 換成內容。
5. **更新首頁**：`python3 scripts/new_page.py <slug> --card` 印出卡片與分組，依第 7 節插入 `index.html`，並更新頁首的球員總數與最後更新日期。
6. **驗收**：`python3 scripts/check_site.py`，必須顯示「全部通過」。
7. **回報**：列出新增／修改的檔案、標「待確認」「待補」的地方。

### 更新既有球員

重跑 `fetch_player.py` → `new_page.py <slug> --update`（只換資料區塊，AI 寫的文字不動）→
檢查「數據解讀」「打法特色」引用的數字是否還對，不對就改寫 → 用 `--card` 重產卡片取代首頁舊卡片 → 更新首頁日期 → `check_site.py`。
「我的觀察」保留舊內容，新觀察依日期往下加，不覆蓋。

## 6. 球員頁內容規則

段落順序固定，版型在 `template.html`，寫作細則在 skill：

1. **球員卡**（`#card`）：球員英文全名、背號、球隊、位置、投打、年齡、出生地、身高體重（公分／公斤）、MLB 初登板日期。
2. **一句話定位**：30 字以內。
3. **生涯簡介**（`#bio`）：3～5 句，只寫可查證的事實（選秀、初登板、主要獎項、轉隊），獎項以 JSON 的 awards 為準。
4. **近三季數據**（`#stats`）：最近三個「已結束」的例行賽季（目前為 2024–2026，由腳本自動判斷）。
   - 打者：G、PA、AVG、OBP、SLG、OPS、HR、RBI、SB、BB%、K%、wRC+、WAR
   - 投手：G、GS、IP、W-L、ERA、WHIP、K/9、BB/9、K%、FIP、WAR（後援投手加 SV、HLD）
   - 二刀流球員打擊、投球兩張表都要放；某季沒出賽顯示「未出賽」。
   - 一季待過多隊時用整季合計，球隊欄寫 `2TM`，表格下方註明隊名。
5. **數據解讀**（`#analysis`）：固定 3 點，每一點都要引用表格裡的具體數字。
6. **打法特色**（`#style`）：打者寫力量、選球、速度、守備；投手有球種長條圖（腳本產生）＋控球、角色。
7. **我的觀察**（`#mine`）：使用者原話，只能補標點，不可改寫或擴寫；沒提供就寫「待補」。
8. **資料來源**（`#sources`）：MLB Stats API（附查詢日期）、MLB.com 球員頁、Baseball-Reference（腳本產生）。

### 數據與事實的鐵則

- **所有數字只能來自 `raw/players/<slug>.json`**，不可憑記憶填寫，也不可自己估算。
- 數據表、球員基本資料、球種、資料來源一律由腳本產生（`<!-- data:xxx -->` 區塊），不可手改；`check_site.py` 會逐字比對。
- JSON 裡沒有的資料寫「待確認」，不要編；也不要寫傷勢、交易細節、合約等 JSON 沒有的推測。
- 球隊以 API 的 currentTeam 為準（球員可能已轉隊，不要用印象）。
- wRC+、WAR、FIP 為 MLB Stats API 提供的版本，頁面已自動註明「與 FanGraphs／B-Ref 數值可能略有差異」。
- **球員名字一律用英文全名**（與 API 的 fullName 相同，由腳本帶入），網站任何地方都不使用中文譯名；隊名、位置等其他內容仍用中文。

## 7. 首頁（index.html）規則

- 分組順序固定：二刀流 → 先發投手 → 後援投手 → 捕手 → 內野手 → 外野手 → 指定打擊。
  - 每組是 `<section class="group" id="g-<分組>">`，分組代號：`two-way`、`starter`、`reliever`、`catcher`、`infield`、`outfield`、`dh`。
  - 球員屬於哪一組由腳本判斷（JSON 的 `position_group`，`--card` 會印出來），不要自己判斷。
  - 沒有球員的分組整段不放；第一次有該分組的球員時，依上面順序插入新的 section。
- 組內依**英文姓氏**字母排序（例如 Judge 在 Soto 前面）。
- 卡片一律用 `new_page.py <slug> --card` 產生的 HTML，不要手寫；卡片顯示球員英文名、球隊縮寫與中文隊名、位置、最近一季代表數據（打者 OPS、投手 ERA、二刀流兩者都有）。
- 頁首 `共 N 位球員・最後更新 YYYY-MM-DD` 每次新增或更新都要改。
- 搜尋框由 `assets/js/search.js` 處理，依卡片的 `data-search` 篩選，不需每次修改。

## 8. 風格規則（已定案：C 數據雜誌＋依球隊配色）

- 白底、細線、系統字型，重點色跟著球員所屬球隊變化（顏色來自 `data/teams.json`）。
- 全站只用 `assets/css/site.css`；頁面裡不寫 `<style>`，行內 style **只能設定 CSS 變數**
  （`--team-primary`、`--team-secondary`、球種長條的 `--w`），這些都由腳本自動帶入。
- 要改風格時先改 skill 與 site.css，並請使用者確認是否套用到所有既有頁面。
- 手機優先：寬度 375px 時頁面不可橫向捲動；數據表放在 `.table-wrap` 裡，小螢幕可以在表格內左右滑動。

## 9. 禁止事項

- 不使用官方球員照片、球隊 logo 或 MLB 商標圖檔（版權問題）；球員卡用球隊色＋背號＋縮寫呈現。
- 不載入外部 CDN、字型或追蹤碼。
- 連結一律用相對路徑，不可出現 `/home/...`、`C:\...` 等本機路徑。
- 不刪除任何檔案；要刪或改名先問使用者。
- 不手改 `raw/players/*.json` 與頁面中的資料區塊。
- 不擅自 git push；使用者說要推才推，推之前列出變更檔案。

## 10. 驗收清單（每次完成前自我檢查）

- [ ] `python3 scripts/check_site.py` 顯示「全部通過」（它會檢查：三檔齊全、沒有 TODO-AI、段落齊全且順序正確、資料區塊和 JSON 一致、首頁連結／分組／排序／總數正確、沒有 `<style>`／非變數行內 style／本機路徑／外部資源）
- [ ] 文字段落引用的數字都能在數據表或 JSON 找到
- [ ] 首頁球員總數與最後更新日期已更新
- [ ] 回報中列出新增／修改的檔案與「待確認」「待補」項目
