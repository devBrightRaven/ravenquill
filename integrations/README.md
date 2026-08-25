# Optional host adapters

Ravenquill core 是 repository 根目錄的 `SKILL.md`、`methodology/` 與 `scripts/`。先依根目錄 [README](../README.md) 安裝 core；支援 Agent Skills `SKILL.md` 慣例的 runtime 可直接探索，其他環境也能讀 Markdown 並執行 Python stdlib scripts。

本目錄只放選用的 host adapters。它們提供自動提醒或 host-native command，不能定義 core behavior，也不能擴張 `edit_authority`、`surface_scope` 或人類的最終決定權。Core installer 不會安裝這些檔案，也不會修改 host config。

## 共用 core，不接 adapter 也能用

| 元件 | 用法 |
|---|---|
| `../SKILL.md` | 寫作、審查或改稿時先讀取並記錄授權契約 |
| `../methodology/writing-harness.md` | 執行 S0/S1/S2 三道關卡 |
| `../methodology/taiwan-writing-glossary.md` | 處理台灣繁中時按需讀取 |
| `../scripts/taiwan-style-check.py` | `python -X utf8 <script> file.md` |
| `../scripts/protected-material-check.py` | 核對明列的 exact literal/count；`protected_material: none` 時跳過 |

## Adapter 對照

| 能力 | `Claude Code` | `OpenAI Codex CLI` | `NousResearch Hermes` |
|---|---|---|---|
| 寫完提醒三道關卡 | `../hooks/` PostToolUse hook | `codex/` PostToolUse hook | `hermes/` plugin |
| 對外 evidence 提醒 | `../hooks/output-tier-gate.py` | `codex/output-tier-gate.py` | 同一 Hermes plugin |
| legacy tighten | `../skill/tighten/SKILL.md` | `codex/prompts/tighten.md` | 可自行移植 legacy skill |

提醒型 adapter 都是 warn-only。提醒不代表通過檢查，也不授權 adapter 修改內容。

## `OpenAI Codex CLI`（選用）

1. Clone repository，先安裝或直接使用 agent-agnostic core。
2. 檢查 `codex/config.example.toml`，再把需要的 hook 設定手動合併到自己的 config。
3. 把範例裡的 repository path 換成實際 clone path。
4. 如需舊版 `/tighten` 體驗，再自行安裝 `codex/prompts/tighten.md`。

Codex adapter 觀察 `apply_patch` 的 tool input，從 patch header 取得候選路徑，並以非阻擋訊息提醒。它不取代 root `SKILL.md`，也不自動套用 findings。

## NousResearch Hermes（選用）

1. Clone repository，先安裝或直接使用 agent-agnostic core。
2. 依 Hermes plugin 目錄慣例，將 `hermes/writing_harness_plugin.py` 與 `harness_core.py` 放在可互相 import 的位置。
3. 如需 legacy `tighten`，另行移植並自行處理該 subskill 的 host-specific 指令；不要把它當成 core requirement。

Hermes 的 `post_tool_call` 只觀察並暫存提醒；`pre_llm_call` 才把提醒注入下一輪 context。這是 adapter lifecycle，不能改寫 Ravenquill 的授權契約。

## `Claude Code`（選用）

`Claude Code` adapter 位於 repository 根的 `hooks/`。先檢查 `hooks/settings.example.json` 與每支 hook 的 CONFIG，再手動合併需要的設定。Core installer 不會執行這一步。

## 共用 adapter logic

`harness_core.py` 是 Codex 與 Hermes adapter 的 stdlib 決策核心。若要調整偵測路徑，修改其中的 `INCLUDES`、`EXCLUDES` 與 `L3_*` 設定。`Claude Code` 的既有 hooks 保持獨立，避免 adapter 升級改動現有安裝。

這些 adapter 只驗證 repository 內附的具體接線；未列出的 runtime 仍可使用 core `SKILL.md` 與 scripts，但不宣稱已有原生 hook integration。
