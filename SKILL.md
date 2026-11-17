---
name: jp-qualified-invoice-checker
description: Check a Japanese qualified invoice (適格請求書, インボイス) before you send it or book it — verifies the 6 mandatory fields, the T+13-digit registration number format, the 8%/10% split, and that the tax and totals actually add up. Use when a user pastes or attaches a Japanese invoice/receipt and asks "is this a valid invoice?", "check this invoice", "インボイスを確認して", or "請求書に不備はないか".
license: MIT
compatibility: Claude Code, Codex CLI, Cursor, VS Code Copilot, Gemini CLI
version: 1.0.0-lite
---

# JP Qualified Invoice Checker — Lite（適格請求書チェッカー）

Check one Japanese qualified invoice (適格請求書) at a time. Do not guess, do not
fix the document silently, and do not give tax advice. Report what is missing or
wrong, with the exact field and the exact numbers, so a human can fix and reissue it.

> **Lite version (free):** this repo has the full checker script and 3 worked
> examples. The full version (8 examples + edge-case guide + 10-case test
> report) is $15 on Agensi — see the link in the README.

## What a qualified invoice must contain (National Tax Agency)

A buyer can only claim input tax credit if the invoice shows all of these. If
even one is missing, the invoice is not a qualified invoice — however clean it looks.

1. **発行事業者の氏名・名称** — issuer name (company or trade name)
2. **登録番号** — `T` + 13 digits, e.g. `T1234567890123`. No `T`, or 12/14 digits, is invalid.
3. **取引年月日** — transaction date (a real calendar date)
4. **取引内容** — what was sold; reduced-rate (8%) items must be marked `※`
5. **税率ごとに区分した対価の額** — amounts split by rate (8% and 10% shown separately)
6. **税率ごとに区分した消費税額** — consumption tax split by rate
7. **請求先（受領者）の氏名・名称** — recipient name (base invoice requirement)

Plus arithmetic: for each rate, `消費税額 = 税抜金額 × 税率` (rounded once per rate,
usually floor/切り捨て), and `合計 = 小計の合計 + 消費税の合計`.

## Procedure

1. **Read the invoice text exactly as given.** If it is a PDF/image, extract the
   text first and say so. Never invent a field that is not on the document.
2. **Run the deterministic checker first** (it catches format and arithmetic
   errors a language model will miss):
   `python3 scripts/check_invoice.py <invoice.txt>`
   Keep its `[FAIL]` / `[WARN]` lines as the backbone of the report.
3. **Re-read the document yourself** for the things the script cannot judge:
   - Does the issuer name match the name on the contract / vendor master?
   - Is the transaction date plausible (not in the future, not a different month)?
   - Are the item names specific enough ("コンサルティング料" is fine; "諸経費" alone is vague)?
   - Is a `※` present on every 8% item, and absent from 10% items?
   - Is the rounding method stated anywhere? If not, a 1-yen difference is a
     warning, not a failure.
4. **Report in this format** (Japanese, because the buyer and the issuer are Japanese):

   ```
   判定： PASS / PASS_WITH_WARNINGS / FAIL
   不備（FAIL）：
   - [Q2] 登録番号がありません …
   確認事項（WARN）：
   - [Q4] 8%の品目に※印がありません …
   修正方法：
   1. 登録番号「T1234567890123」を発行者名の近くに追加してください
   ```
   Always quote the wrong value and the correct value side by side.
5. **Never** reissue the invoice yourself, change amounts, or claim the
   T-number is registered. Registration can only be confirmed on the National
   Tax Agency's public site (適格請求書発行事業者公表サイト) — tell the user
   to check there, with the exact number to look up.

## Examples

### Ex. 1 — Valid, 10% only → PASS
Input:
```
発行者：株式会社サンプル商事
登録番号：T1234567890123
請求先：株式会社テスト商事 御中
取引年月日：2026年11月17日
取引内容：コンサルティング料
10% 小計：100,000円
10% 消費税額：10,000円
合計：110,000円
```
Output: `VERDICT: PASS` — no findings.

### Ex. 3 — Missing registration number → FAIL
Input: Ex. 1 without the 登録番号 line.
Output: `[FAIL] Q2: 登録番号（T + 13桁）が見つかりません。適格請求書として認められません`
→ 修正：発行者に登録番号を記載してもらう。登録していない事業者は適格請求書を発行できない。

### Ex. 7 — Tax arithmetic wrong → FAIL
Input: 10% 小計 100,000円なのに消費税額 9,000円、合計 109,000円。
Output: `[FAIL] Q6: 10%の消費税額が合いません（記載 9,000円 / 計算 10,000円、差 -1,000円）`
→ 修正：消費税額を 10,000円、合計を 110,000円に直す。

## Edge cases (summary)

- **免税事業者からの請求書**：登録番号がないのは「不備」ではなく「適格請求書ではない」という事実。FAILとして報告し、「この請求書では仕入税額控除を受けられない」と添える。
- **1円の差**：端数処理の方法が書かれていない場合、1円の差は WARN にとどめる。2円以上は FAIL。
- **海外の請求書**：このスキルは日本の適格請求書専用。海外発行の請求書には適用しない。

Full edge-case guide (handwritten invoices, receipts, correction invoices, tax-exempt suppliers) is in the paid full version.

## What NOT to do

- 登録番号を「推測」で補わない。分からなければ「不明」と書く。
- 金額を勝手に直して「修正済み請求書」を作らない。指摘だけする。
- 「この請求書で控除できます」と断定しない。最終判断は税理士・税務署。
- 取引先の登録状況をAPIや外部サイトで勝手に照会しない（このスキルはオフラインで動く）。
- 個人情報（住所・口座番号・氏名）を含む請求書を外部に送信・保存しない。

## Files in this pack

- `scripts/check_invoice.py` — deterministic checker (Python 3, no dependencies)
- `examples/` — 3 example invoices (Ex. 1, 3, 7)
