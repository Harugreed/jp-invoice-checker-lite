# JP Qualified Invoice Checker — Lite

A free Claude skill that checks a Japanese qualified invoice (適格請求書 / インボイス)
before you send it or book it — the 6 mandatory fields, the T+13-digit
registration number, the 8%/10% split, and whether the tax and totals add up.

日本の適格請求書を、送る前・経理に入れる前にチェックするClaudeスキル（無料lite版）。
国税庁の必須6項目、登録番号（T+13桁）の形式、8%・10%の税率別区分、消費税額と
合計の計算が合っているかを判定します。

## What's in this lite version (free, MIT)

- `SKILL.md` — the skill, with 3 worked examples (valid / missing T-number / tax-math error)
- `scripts/check_invoice.py` — the full deterministic checker (Python 3, no dependencies, no network, no API key)
- `examples/` — 3 example invoices

```bash
python3 scripts/check_invoice.py examples/ex1-valid-10pct.txt
# VERDICT: PASS

python3 scripts/check_invoice.py examples/ex3-missing-tnumber.txt
# [FAIL] Q2: 登録番号（T + 13桁）が見つかりません
```

## Full version — $15 on Agensi

The full version adds 5 more worked examples, the full edge-case guide
(handwritten invoices, receipts, correction invoices, tax-exempt suppliers,
1-yen rounding) and a 10-case test report (10/10 pass).

- Agensi (review in progress — public link coming soon): https://www.agensi.io/creator/harugreed
- Price: $15 one-time. You keep the skill forever; no API key, no subscription.

## Install (Claude Code)

```bash
cp -r jp-invoice-checker-lite ~/.claude/skills/
```

## What it does NOT do

- It does **not** verify that a T-number is actually registered with the
  National Tax Agency (check the NTA public site for that). It checks format only.
- It is **not** tax or legal advice.
- It does not fix or reissue invoices, and it never sends data anywhere.

## License

MIT — see `LICENSE`.
