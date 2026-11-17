#!/usr/bin/env python3
"""jp-qualified-invoice-checker: deterministic check of a Japanese qualified
invoice (適格請求書) supplied as plain text.

Usage:
  python3 check_invoice.py <invoice.txt>
  cat invoice.txt | python3 check_invoice.py

Rules checked (National Tax Agency, 適格請求書等保存方式):
  Q1 issuer name present (発行者 / 発行事業者 / 請求者)
  Q2 registration number T + 13 digits present and well-formed
  Q3 transaction date present and a valid calendar date
  Q4 line items present (取引内容), with ※ on 8% (reduced-rate) items
  Q5 amounts split by tax rate (8% and 10% shown separately when both used)
  Q6 consumption tax shown split by rate, and arithmetic recomputes
  Q7 recipient name present (請求先 / 宛名)
  Q8 stated total equals sum of rate subtotals + tax

Output: one line per finding (code, severity, message) then a verdict line:
  PASS / PASS_WITH_WARNINGS / FAIL
Exit code: 0 = PASS or PASS_WITH_WARNINGS, 1 = FAIL, 2 = usage error.

This is a pre-send / pre-booking check, NOT tax or legal advice. It cannot
verify that a T-number is actually registered with the National Tax Agency
(that needs the NTA public site); it only checks format. Arithmetic uses
floor (切り捨て) per rate, the most common convention; if the issuer uses
round-half-up, a 1-yen difference is reported as a warning, not a failure.
"""
import re
import sys
from datetime import date

T_RE = re.compile(r"T(\d{13})")
T_LOOSE = re.compile(r"T\s*(\d[\d\s\-]{10,16})")
DATE_RE = re.compile(r"(20\d{2})[年/\-](\d{1,2})[月/\-](\d{1,2})")
AMT_RE = re.compile(r"([0-9,]+)\s*円")
RATE_RE = re.compile(r"(8|10)\s*%")


def yen(s):
    return int(s.replace(",", "").replace("円", ""))


def find_amounts(text, keywords):
    """Return list of (rate, amount) found on lines mentioning a keyword."""
    out = []
    for line in text.splitlines():
        if any(k in line for k in keywords):
            m = RATE_RE.search(line)
            a = AMT_RE.search(line)
            if m and a:
                out.append((int(m.group(1)), yen(a.group(1)), line.strip()))
    return out


def check(text):
    findings = []  # (code, severity, message)

    def add(code, sev, msg):
        findings.append((code, sev, msg))

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Q1 issuer
    if not re.search(r"(発行者|発行事業者|請求者|発行元)", text):
        add("Q1", "FAIL", "発行事業者の氏名・名称が見つかりません（「発行者：」のように明記してください）")
    # Q7 recipient
    if not re.search(r"(請求先|宛名|御中|様\s*$)", text):
        add("Q7", "FAIL", "請求先（受領者）の氏名・名称が見つかりません")

    # Q2 T-number
    m = T_RE.search(text)
    if not m:
        loose = T_LOOSE.search(text)
        if loose:
            add("Q2", "FAIL", f"登録番号の形式が不正です: {loose.group(0).strip()!r} — T + 13桁の数字で記載してください")
        else:
            add("Q2", "FAIL", "登録番号（T + 13桁）が見つかりません。適格請求書として認められません")
    else:
        num = m.group(1)
        if num.startswith("0"):
            add("Q2", "WARN", "登録番号が0で始まっています。個人事業主の番号は0で始まらないのが通常です。桁の写し間違いがないか確認してください")

    # Q3 date
    dm = DATE_RE.search(text)
    if not dm:
        add("Q3", "FAIL", "取引年月日が見つかりません（例：2026年11月17日）")
    else:
        try:
            date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
        except ValueError:
            add("Q3", "FAIL", f"取引年月日が存在しない日付です: {dm.group(0)}")

    # Q4 line items
    item_lines = [ln for ln in lines if re.search(r"(品目|内容|摘要|項目)", ln)]
    body_lines = [ln for ln in lines if re.search(r"[※\*]", ln)]
    if not item_lines and not re.search(r"(商品|サービス|作業|宿泊|利用料|料金)", text):
        add("Q4", "FAIL", "取引内容（品目・サービス名）が見つかりません")
    # reduced-rate marking: an 8% line should carry ※ somewhere in the document
    # (in real invoices the ※ is on the item line, not the subtotal line)
    eight_lines = [ln for ln in lines if "8%" in ln and AMT_RE.search(ln)]
    if eight_lines and "※" not in text:
        add("Q4", "WARN", "8%（軽減税率）の品目に※印がありません。軽減税率対象である旨の明記が必要です")

    # Q5/Q6 amounts by rate
    subtotals = find_amounts(text, ["小計", "本体", "税抜", "対価"])
    taxes = find_amounts(text, ["消費税", "税額"])
    rates_seen = set(r for r, _, _ in subtotals) | set(r for r, _, _ in taxes)
    if not subtotals:
        add("Q5", "FAIL", "税率ごとに区分した対価の額が見つかりません（「10% 小計：…円」のように税率別に記載してください）")
    if not taxes:
        add("Q6", "FAIL", "税率ごとに区分した消費税額が見つかりません")
    if len(rates_seen) > 1 and (len(set(r for r, _, _ in subtotals)) < 2 or len(set(r for r, _, _ in taxes)) < 2):
        add("Q5", "FAIL", "8%と10%の両方があるのに、金額が税率別に分かれていません。合算での記載は適格請求書として認められません")

    # Arithmetic: tax per rate = floor(subtotal * rate / 100)
    sub = {r: a for r, a, _ in subtotals}
    tax = {r: a for r, a, _ in taxes}
    for r in sorted(set(sub) & set(tax)):
        expected = sub[r] * r // 100
        if tax[r] != expected:
            diff = tax[r] - expected
            if abs(diff) == 1:
                add("Q6", "WARN", f"{r}%の消費税額が計算値と1円違います（記載 {tax[r]:,}円 / 計算 {expected:,}円）。端数処理の方法が違う可能性があります")
            else:
                add("Q6", "FAIL", f"{r}%の消費税額が合いません（記載 {tax[r]:,}円 / 計算 {expected:,}円、差 {diff:+,}円）")

    # Q8 total
    total_m = None
    for ln in lines:
        if re.search(r"(合計|請求金額|お支払金額)", ln):
            a = AMT_RE.search(ln)
            if a:
                total_m = yen(a.group(1))
    if total_m is not None and sub and tax:
        expected_total = sum(sub.values()) + sum(tax.values())
        if total_m != expected_total:
            add("Q8", "FAIL", f"合計金額が合いません（記載 {total_m:,}円 / 計算 {expected_total:,}円、差 {total_m - expected_total:+,}円）")
    elif total_m is None:
        add("Q8", "FAIL", "合計金額が見つかりません")

    return findings


def main(argv):
    if len(argv) > 1:
        with open(argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("usage: check_invoice.py <invoice.txt>", file=sys.stderr)
        return 2
    findings = check(text)
    for code, sev, msg in findings:
        print(f"[{sev}] {code}: {msg}")
    fails = [f for f in findings if f[1] == "FAIL"]
    warns = [f for f in findings if f[1] == "WARN"]
    if fails:
        print(f"VERDICT: FAIL — {len(fails)}件の不備があります。修正して再発行してください。")
        return 1
    if warns:
        print(f"VERDICT: PASS_WITH_WARNINGS — 必須項目は揃っていますが、{len(warns)}件の確認事項があります。")
        return 0
    print("VERDICT: PASS — 必須項目・金額ともに問題ありません。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
