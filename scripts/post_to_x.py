#!/usr/bin/env python3
"""drafts/x_draft_YYYY-MM-DD.md の「パターンA」をXに投稿する。

- 重み付き文字数が280を超える場合は投稿しない（エラー終了）
- 認証情報(X_API_KEY等)が無い場合はドライラン（投稿せず内容表示）
- 同じ日付は二重投稿しない（drafts/posted/YYYY-MM-DD.txt を目印にする）
"""
import os, re, sys, datetime, pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERN = os.environ.get("X_PATTERN", "A")  # A / B / C


def weight(t: str) -> int:
    t = re.sub(r"https?://\S+", "x" * 23, t)
    w = 0
    for ch in t:
        cp = ord(ch)
        wide = (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0xA4CF or 0xAC00 <= cp <= 0xD7A3
                or 0xF900 <= cp <= 0xFAFF or 0xFE30 <= cp <= 0xFE4F or 0xFF00 <= cp <= 0xFF60
                or 0xFFE0 <= cp <= 0xFFE6)
        w += 2 if wide else 1
    return w


def extract(md: str, pattern: str) -> str:
    m = re.search(rf"^## パターン{pattern}.*?\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    if not m:
        raise SystemExit(f"パターン{pattern}が見つかりません")
    lines = []
    for line in m.group(1).splitlines():
        if line.startswith(("▶", "本文：", "---", "✅")):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main() -> int:
    today = os.environ.get("X_DATE") or datetime.datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
    draft = ROOT / "drafts" / f"x_draft_{today}.md"
    marker = ROOT / "drafts" / "posted" / f"{today}.txt"
    if marker.exists():
        print(f"{today} は投稿済み。スキップ"); return 0
    if not draft.exists():
        print(f"ドラフトなし: {draft.name}", file=sys.stderr); return 1

    text = extract(draft.read_text(encoding="utf-8"), PATTERN)
    w = weight(text)
    print(f"--- 投稿内容（重み {w}/280）---\n{text}\n------------------------")
    if not text or w > 280:
        print("空、または280超のため中止", file=sys.stderr); return 1

    keys = [os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
    if not all(keys) or os.environ.get("DRY_RUN") == "1":
        print("ドライラン（投稿していません）"); return 0

    from requests_oauthlib import OAuth1Session
    s = OAuth1Session(*keys)
    r = s.post("https://api.twitter.com/2/tweets", json={"text": text}, timeout=30)
    print(r.status_code, r.text)
    if r.status_code != 201:
        return 1
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(r.text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
