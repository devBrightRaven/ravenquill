# 寫作 Harness（中文對外／知識資產長文）

> 這份檔是三道核心關卡的權威定義：S0 輸入、S1 機械、S2 人類判斷。所有面向人眼閱讀的中文長文都必須通過這三道關卡。
> 社群圖卡／輪播／貼文文案亦屬對外中文內容。文案嵌在 HTML／JSON 裡不豁免，先抽成 .md 檢查再嵌回。對外 CTA／slogan／品牌語句和掛名觀點不自創：先用已有素材，查無就問需求方。
> 不適用：表格、yaml、程式碼、清單頭尾、純機械骨架（標 `draft-skeleton`）。

先講清楚兩個詞。**AI slop** 指 AI 寫出來那種空泛、堆砌、套模板，一看就知道不是人寫的味道。**閘**(gate) 指一個沒通過就不放行的檢查點。

這套系統把「會不會寫成 AI slop」從事後憑感覺修，前移成動筆前和草稿後的固定檢查點：

- **S0 輸入閘**：動筆前擋掉「沒素材就硬編」。
- **S1 機械閘**：草稿後用腳本掃機械錯誤（標點、用字、句型）。
- **條件式 perspective review**：高風險對外說服或作者不易自審時，可加做「替讀者下判斷」的獨立視角審查；不是每篇必跑的第四道關卡。
- **S2 判斷閘**：草稿後靠人判斷腳本抓不到的問題（結構、聲音、有沒有編造）。

---

## S0 輸入閘（動筆前，最高槓桿）

寫之前先記錄：

- `scene`：`social`／`newsletter`／`sales`／`customer-service`／`office-report`／`general`
- `edit_authority`：`review-only`／`propose`／`apply`
- `surface_scope`：本次允許檢視或修改的檔案、段落、欄位或輸出面
- `protected_material`：`<manifest.json>`／`none`

`review-only` 禁止寫入；`propose` 只能提供候選修改；`apply` 只能在 `surface_scope` 內寫入。人類保留最終採用、拒絕與發布決定。

接著問：這篇要不要**真實場景／案例／引述對白／數字**？

- 要 → 有沒有可用的真實（可匿名）素材？
  - 有 → 進 S1 區的撰寫
  - **沒有 → STOP。跟需求方要最小素材（對方真的說／問了什麼、出什麼錯、後果）。禁止自行編造再標「示意／假設／placeholder」蒙混。**
- 不要（純框架／觀點文）→ 仍禁止虛構案例當佐證；無真例就不寫那個例子。

被打回「這是編的」時：不要再生一個更好的編造，停止產出，把缺口當輸入需求丟回需求方。

> **為什麼這站最重要**：AI slop 最致命的不是用詞，是「煞有介事地編一個看似具體的例子」。一旦容許編造，後面幾站再嚴也只是把假內容磨得更光滑。S0 是唯一能擋掉這個的點。

---

## S1 機械閘（草稿後，純腳本 0 LLM）

```
python -X utf8 scripts/taiwan-style-check.py <file.md> [--public]
```

exit 0 才算過（exit 0 是程式回報「全部通過」的慣例，非 0 代表有命中）。它掃這幾類：

- 破折號、半形標點夾在中文裡
- 大陸用語、把 API 術語直接丟給讀者
- 開場推銷詞、「不是 X 是 Y」這種對比句型在同一篇用超過 2 次
- **AI 工具殘留**：追蹤參數與內部 citation 殘碼；引用原話、inline code 與 code fence 內容放行

**對外文字**：寫給一般讀者的內容加 `--public`，多擋低誤報的工程黑話，例如「機械可檢」、`false positive`、`verbatim`。具有普通用法的「固化」、成語和「X 感」留給 S2 按語境判斷，不做無條件黑名單。

另外，frontmatter 標 `audience: external` + `type: client-message` 的對外短訊，會再多一道全形分號檢查：訊息用句號斷句更像真人，分號是書面腔（glossary §1.1.1）。

命中即修，修完重跑，不得跳過。Edit 後重讀該行驗證。

> 機械閘只收低誤報規則。每條新 regex 必須同時有 `should flag` 和 `should allow` 行為測試；無法寫出有意義反例邊界時，留給 S2 判斷。

---

## 條件式 perspective review（選用）

高風險對外說服、政策／法遵主張，或作者不易自審時，可用 `methodology/帶風向審查員.md` 做獨立 perspective review。審查可由人、現有 council 或另一個 agent 執行，Ravenquill 不強制特定編排系統。

選擇執行時，審查結果要列出問題、理由與修正方向。不要預設有罪；沒有證據就回報 clean。

---

## S2 判斷閘（草稿後，強制自審＋留證）

腳本抓不到的問題（文章結構、作者聲音、敘事姿態、台灣語感、有沒有編造）只能靠人判斷。**逐項自答，並把結果貼進回覆**，才能宣告完成。把答案貼出來就是「留證」：留下一份事後能回頭檢查的證據，而不是一句「我檢查過了」就算數。

> 這裡的「敘事姿態」指作者在文章裡站的位置：是把場景擺出來讓讀者自己下判斷，還是急著用形容詞替讀者定性。前者像人寫的，後者是 AI 的慣性。下面 2b 會展開怎麼自查。

### 2a 結構／聲音 5 問
1. 開場有具體場景／時間／人，還是全景泛論？
2. 有一個「我自己的」、會被反駁的主張當主軸？
3. 段落詳略刻意不平均（重點停留、其餘掃過），還是 N 段等長罐頭？
4. 收尾是具體斷言，還是空心金句（刪掉看內容掉不掉血）？
5. 全篇有至少一個只有當事人講得出的真實（可匿名）例子／數字？

任一答不出 → 還是 AI 文，**重寫骨架不是潤稿**。

### 2b 敘事姿態
- 評價詞前置自查：每個「很／最／真正／幾乎／太＋評價詞」「理由很 X」「問題出在 Y」，問「刪掉它，讀者靠前文推得出來嗎？」推得出 → 刪（讀者自己得出＝敘事成功）；推不出 → 補場景不是補形容詞。
- 句首語氣詞由人工依語境判斷：「其實／老實說／我記得」可能是填充，也可能承載態度或不確定性；不可只憑詞面硬刪。
- 定調位置（結構面）：不可在文章前段用強形容詞／評價宣稱替後文預設角度。前段一定調，讀者就帶著那個定見讀後面的理由與證據——這是帶風向，會把讀者推進刻板印象、讀者也察覺得到而反感，論點不增反減。先擺事實與論述，判斷讓讀者讀完自己形成；命名／定性只能在事情發生後，不可在它之前（收尾句亦然）。

### 2c 台灣在地語感
- 有對白或口語的地方，唸出來，辨認得出是台灣人在講話才留。以中小企業老闆的口吻為例：問他真的會問的問題（「到底可以幫我們在哪邊加分」）、把成本焦慮講得口語（「有沒有更省錢的作法」）、省掉主詞的口語強調（「不然請大會計師事務所超級貴」）。四平八穩的書面普通話就是 AI 預設腔，要重寫。

### 2d 場景邊界

- `social`：保留口頭禪、碎句與刻意斷行；輸出到純文字平台時清除 Markdown 標記。
- `newsletter`：保留故事節奏、岔題與留白；不強迫補公式化結尾。
- `sales`：去掉浮誇形容詞，但不得削弱 CTA、價格、期限、名額或退費承諾。
- `customer-service`：先回答再說明；金流、條款與責任措辭保持精確。
- `office-report`：結論先行並維持正式語域；不為了「人味」加入口語碎片。
- `general`：只執行跨場景都安全的判斷；不確定時標示場景缺口。

### 2e 句子層 9 類人眼語病（默讀掃）
斷句不清／修飾鏈繞口／缺動詞／缺受詞／語序怪／指代不清／詞性誤認／口語縮寫不當／擬人化過度。

### 2f 保護內容與作者聲音

如果本次確實沒有需要逐字保護的內容，明記 `protected_material: none`，跳過 protected checker。不要為了跑流程虛構 literal，也不要建立空 manifest。

若有需要保護的內容，修改前先保留原稿，並用非空 JSON manifest 明列 exact literal 和出現次數。只要原稿含 URL，且需求要求保留事實或來源素材，預設 protected literal 就是完整 supplied URL，不是拆開後挑其中幾個元件保留。然後執行：

```
python -X utf8 scripts/protected-material-check.py <manifest.json> <before.md> <after.md>
```

```json
{
  "items": [
    {"value": "8/30", "count": 1},
    {"value": "「原話」", "count": 1},
    {"value": "https://example.com/?x=1&utm_source=ChatGPT.com", "count": 1}
  ]
}
```

完整 protected URL 的結果只能是三種之一：整條 URL 原樣保留；manifest 明示授權後，只移除 raw query 中完全相同的小寫 segment `utm_source=chatgpt.com`、`utm_source=openai` 或 `referrer=grok.com`；使用者明確授權更改或移除那一條完整 URL。一般性的「移除 AI 痕跡」不會自動選中後兩種結果。`utm_source=ChatGPT.com`、encoded variants 等未符合 exact lowercase cleanup 的項目保持原樣，並列為 unresolved URL decision 交人類決定。未列入 manifest 的新增主張、supplied voice constraints 與高誤報語意詞仍需人工依上下文核對。

改完後對照你的**人味保護清單**過一遍：那是一份作者自建的清單，收錄自己行文的人味特徵（慣用口頭語、標誌性句式、特定領域的講法）。目的是確認去 AI 味的過程沒有把作者本人的味道一起誤刪——判準是聚集不是單點：一兩處被改掉無妨，同一類特徵被系統性抹平才算失真。

---

## 留證格式（宣告完成時貼這個）

```
S0 輸入閘：scene=<scene>；edit_authority=<review-only|propose|apply>；surface_scope=<scope>；真實素材=有／無
Authority 驗證：未超出 surface_scope；review-only 無寫入；人類保留最終決定
S1 機械閘：taiwan-style-check exit 0 ✅（或列已修項）
Perspective review：未觸發／已執行（列 findings 與處理）
S2 判斷閘：
  2a 5 問：①… ②… ③… ④… ⑤…（逐題一句話佐證）
  2b 評價詞／雜訊詞：已掃，列刪改處或「無」
  2c 台灣語感：對白唸過／無對白
  2d 場景邊界：已依 <scene> 檢查
  2e 9 類語病：默讀過，列修處或「無」
  2f 保護內容：protected_material=<manifest.json|none>
    checker=<executed|not executed>
    artifacts=<實際 manifest/before/after 路徑|none>
    result=<實際 exit code|manual exact-literal comparison>
    unresolved URL decisions=<保持原樣、待人類決定的 variants|none>
```

Exit code 只能來自實際以這三份 artifacts 執行過的 command。純聊天或模擬改寫要寫 `checker=not executed`，改報 manual exact-literal comparison。三道核心關卡任一未過或留證缺項＝未完成。條件式 review 若觸發，其 findings 也必須處理。

---

## 為什麼是「Harness」而不是「prompt 裡寫幾條規則」

把規則塞進 prompt 有兩個失效模式：模型會選擇性遵守（純文字描述的規則最容易被跳過），而且事後沒有任何證據能證明它真的做了。Harness 的差別是：

1. **機械閘是程式，不是承諾**：exit code 不會說謊。
2. **判斷閘要留證**：逐題自答貼回覆，比一句「我檢查過了」更能事後查核。
3. **coverage ratchet**：新規則留 SF，誤殺留 SNF。已知風險的測試覆蓋只升不降，regex 可以因反證收窄或撤換。
