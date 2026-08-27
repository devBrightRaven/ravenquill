# Itoguchi authored scene evidence（選用）

這份文件描述 Itoguchi 故事證據如何單向交給 Ravenquill 的 `scene: fiction`
流程使用。Itoguchi 是 authored story state 的來源；Ravenquill 負責編輯權限、
範圍、原文保護與人類最後決定。兩個 repository 不互相 import，也沒有 shared
package；這個整合不屬於 Ravenquill core。

## 七步流程

每個場景都重新取得 packet。不要把一次查詢的結果當成永久有效的故事狀態。

1. **查詢新 packet。** 向 Itoguchi 查詢 `scene_evidence`，明確提供 intended
   holder、`as_of`、target（對應 packet query 的 `about`）與 persona。

   若 packet 的 warnings 含 `scene_presence_unverified`，packet 仍可供與場景成員
   無關的 evidence 使用；但任何依賴誰在場的假設或生成（包括 new named-character
   dialogue）都保持 unresolved，直到人類或作者確認出場人物。既有對白仍可 review
   或 edit；若沒有符合 query 的 voice constraint，固定回報
   `voice fidelity: unverified`。這個 warning 與 validator 都不證明 presence、語意
   或 voice quality。

2. **驗證版本與 revision。** 使用 [packet contract helper](packet_contract.py)
   驗證 `itoguchi.scene-evidence/v1`。要重用已保存的 packet 時，先重新查詢
   同一場景，再比較兩者的 `story_revision`；不一致就丟棄舊 packet，不得繼續
   使用。`validate_packet` 可用 `expected_revision` 執行這項比對。

   這項驗證只確認 packet contract、來源指標與安全邊界，不證明語意品質或聲音
   品質。

3. **記錄 Ravenquill 場景契約。** 在開始寫作或改稿前記錄：

   ```text
   scene: fiction
   edit_authority: review-only | propose | apply
   surface_scope: <本次檢視或修改的檔案、段落、欄位或輸出>
   source_evidence: <保存的 packet path>
   protected_material: <manifest path | none>
   ```

   packet 只提供故事證據，不授予草稿或 story card 的編輯權限；人類仍決定採用、
   儲存與發布。

4. **先確認 authored voice constraint。** 若要替 named character 寫新的對白，
   只有 Itoguchi 依 holder、`as_of`、target 與 persona 篩選後提供的 constraint
   才算符合；`voice_constraints` 非空本身不代表可套用到其他 query。沒有符合查詢
   條件的 authored voice constraint 就停止，不能從 belief、情緒、既有對白或模型
   熟悉度自行推導。既有對白仍可 review 或 edit，但必須回報
   `voice fidelity: unverified`。

5. **只保護草稿裡確實出現的 authored literal。** 先保存 pre-edit draft，再
   從 packet 選出在該草稿中逐字出現的 authored evidence value 或 voice constraint
   text；`select_protected_items` 會核對實際出現次數。`derived_context` 永遠不
   能成為 protected material。writer-only 的 authored text 若逐字出現在草稿中，
   可以列入 protected material，但不能成為角色知道的內容；用
   `require_character_available` 核對角色可用性。沒有符合項目時記錄
   `protected_material: none`，不要建立空 manifest。

6. **完成改稿後跑 Ravenquill checker。** 只在有非空 manifest 時，對同一份
   pre-edit draft 與 edit 後檔案執行既有 checker：

   ```powershell
   python -X utf8 scripts/protected-material-check.py <manifest.json> <before.md> <after.md>
   ```

   通過 exact literal/count 檢查不代表語意或聲音忠實；S2 仍要由人判斷。

7. **提出 story-card 變更前重新查詢與 audit。** 再向 Itoguchi 查詢同一場景的
   新 packet，並依 Itoguchi 現有 audit 流程檢查。只有在新證據與 audit 結果可追溯
   後，才能提出 story-card 變更；packet 本身不會替任何一方執行變更。

## 公開 helper 與邊界

[packet_contract.py](packet_contract.py) 是這個選用整合的公開 consumer surface：
這個 adapter 只支援在完整 Ravenquill repository 內使用，並依賴 repository 內既有的
`scripts/protected-material-check.py`。單獨複製 `packet_contract.py` 不受支援。

| Helper | 用途 |
|---|---|
| `validate_packet` | 驗證 v1 packet，並可比對 `expected_revision` |
| `select_protected_items` | 從 pre-edit draft 選出確實存在的 authored literal 與 count |
| `require_character_available` | 拒絕 writer-only 或 derived item 作為角色知識 |
| `voice_status` | 沒有 authored voice constraint 時阻擋新對白，或回報既有對白未驗證 |

`derived_context` 是給 writer 的說明，不是 canon、protected material 或 character
knowledge。writer-only authored text 可以因為原文保護需求被保護，但不能被當成
角色知道的事。validator 不評估語意或 voice quality；packet 也不會自動安裝任何
runtime config。Ravenquill core installer 不會安裝本目錄，Itoguchi 仍由自己的
runtime 與 authoring workflow 管理。
