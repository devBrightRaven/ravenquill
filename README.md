# Ravenquill

> 保留作者決定權與原始素材的寫作品質閘。

Ravenquill 是一個 agent-agnostic Agent Skill。Repository 根目錄就是可探索的 skill folder：`SKILL.md` 定義寫作契約，`methodology/` 放人工判斷方法，`scripts/` 提供 Python stdlib 機械檢查。支援 `SKILL.md` 慣例的 agent 可以直接載入；其他環境也能讀 Markdown 並自行執行腳本。

這個 core 不依賴特定模型、subagent 或 council，也不會修改任何 agent 設定。`Claude Code`、`OpenAI Codex CLI` 與 `NousResearch Hermes` 的 hook／command 接線只是選用 adapter，放在 `hooks/` 與 `integrations/`。

Ravenquill fork 自 [scandnavik/writing-harness](https://github.com/scandnavik/writing-harness)，保留上游 MIT 授權與 commit history，並加入明確的素材保護與規則證據治理。

## 安裝 agent-agnostic core

```bash
git clone https://github.com/devBrightRaven/ravenquill.git
cd ravenquill

# macOS / Linux；預設安裝到 ~/.agents/skills/ravenquill
bash ./install.sh

# 自訂 skill root
bash ./install.sh /path/to/skills
```

```powershell
# Windows PowerShell；預設安裝到 ~/.agents/skills/ravenquill
.\install.ps1

# 自訂 skill root
.\install.ps1 -SkillRoot C:\path\to\skills
```

Installer 只複製 root `SKILL.md`、`methodology/*.md` 與 `scripts/*.py`。它不安裝 hooks、integrations、examples 或 legacy `tighten`，也不改任何 host config。若目的地已存在，installer 會拒絕覆寫；要更新時，請先自行檢查、移走舊目錄，或改用另一個 skill root。

## 使用方式

請 agent 讀取安裝後的 `ravenquill/SKILL.md`，並依文件先記錄：

```text
scene: <scene>
edit_authority: review-only | propose | apply
surface_scope: <本次範圍>
protected_material: <manifest.json | none>
```

人類保留採用、儲存與發布的最終決定。Adapter 只能提醒或回報，不能擴張 `edit_authority` 或 `surface_scope`。

如果本次確實沒有 protected material，明記 `protected_material: none`，不要虛構一個 literal，也不要建立空 manifest。若有姓名、數字、日期、承諾、引述或 URL 需要逐字保留，先建立含 exact literal 與 count 的 manifest，再於修改後執行：

```bash
python -X utf8 scripts/protected-material-check.py manifest.json before.md after.md
```

自動 tracking cleanup 只接受 manifest 明示放行的三個小寫 raw segment：`utm_source=chatgpt.com`、`utm_source=openai`、`referrer=grok.com`。大小寫變體、encoding、參數順序與其他 URL 差異都不自動正規化。

## 三道核心關卡

| 關卡 | 做什麼 | 主要檔案 |
|---|---|---|
| S0 輸入閘 | 確認 scene、授權、範圍與真實素材；素材不足就停下來問 | `SKILL.md`、`methodology/writing-harness.md` |
| S1 機械閘 | 掃台灣用字、標點、低誤報句型與 AI residue | `scripts/taiwan-style-check.py` |
| S2 判斷閘 | 人工檢查結構、聲音、敘事姿態、語感與 protected material | `methodology/*.md`、`scripts/protected-material-check.py` |

S1 基本用法：

```bash
python -X utf8 scripts/taiwan-style-check.py 文章.md
python -X utf8 scripts/taiwan-style-check.py 文章.md --public
```

Exit `0` 代表機械檢查通過；exit `10` 會列出 findings。具有語意脈絡或高誤報風險的詞仍由 S2 判斷，不因單一 token 自動刪改。

其他 portable scripts：

- `scripts/verbosity-check.py`：找出十類冗贅 pattern，只做偵測。
- `scripts/rewrite-diff.py`：比較草稿與真人改稿，找出可回饋到 glossary 的規則。

## 選用 adapters

Core skill 可以獨立運作。若還需要「寫完後自動提醒」，再依 host 選擇 adapter：

- `Claude Code`：repository 的 `hooks/` 與 `hooks/settings.example.json`。
- `OpenAI Codex CLI`：`integrations/codex/`。
- `NousResearch Hermes`：`integrations/hermes/`。

各 adapter 的安裝方式、能力差異與限制：[`integrations/README.md`](integrations/README.md)

它們不由 core installer 安裝，也不代表 Ravenquill 對所有 agent runtime 的通用相容性承諾。

`skill/tighten/` 是舊版 Claude-specific rewrite subskill，只供既有使用者選用；它不是 Ravenquill core，也不會由 installer 安裝。

## 客製到其他語境

- 替換 `methodology/taiwan-writing-glossary.md` 的地區用語判準；三道關卡不必跟著改。
- 修改 `scripts/taiwan-style-check.py` 的規則時，每條 regex 都要有 `should flag` 與 `should allow` 行為測試。
- 作者自己的口吻可從 `examples/content-voice-prompt.template.md` 建立；core installer 不會自動複製範本。

## Repository 結構

```text
ravenquill/
├─ SKILL.md                 agent-agnostic skill entrypoint
├─ methodology/            三道關卡與繁中 glossary
├─ scripts/                Python stdlib 檢查工具
├─ hooks/                  選用 Claude Code adapter
├─ integrations/           選用 Codex／Hermes adapters
├─ skill/tighten/          選用 legacy Claude-specific subskill
├─ examples/               範本與樣本
├─ tests/                  stdlib 測試
├─ install.sh
└─ install.ps1
```

## 驗證

```bash
python -X utf8 tests/test_skill_package.py
python -X utf8 tests/test_integrations.py
python -X utf8 tests/test_harness.py
```

## Contributing

新規則必須同時保留會命中的正例與不該命中的反例。規則可以因反證收窄，已知風險的 regression evidence 不能消失。

詳見：[CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT 授權文件：[LICENSE](LICENSE)
