"""Step 1: pull raw entries from curated RSS feeds published within the lookback window."""
import json
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser

from config import FEEDS, SETTINGS, today_dir


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            return datetime.fromtimestamp(mktime(struct), tz=timezone.utc)
    return None


def collect_raw_news() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SETTINGS["lookback_hours"])
    items = []

    for feed_conf in FEEDS:
        name, url = feed_conf["name"], feed_conf["url"]
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # noqa: BLE001 - a single bad feed shouldn't kill the run
            print(f"  [warn] failed to fetch '{name}': {exc}")
            continue

        if parsed.bozo and not parsed.entries:
            print(f"  [warn] '{name}' returned no usable entries ({parsed.bozo_exception})")
            continue

        kept = 0
        for entry in parsed.entries:
            published = _entry_datetime(entry)
            if published is None or published < cutoff:
                continue
            items.append(
                {
                    "source": name,
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "published": published.isoformat(),
                }
            )
            kept += 1
        print(f"  [ok] {name}: {kept} item(s) within lookback window")

    return items


def main():
    print(f"Collecting AI news from {len(FEEDS)} feeds (lookback {SETTINGS['lookback_hours']}h)...")
    items = collect_raw_news()
    out_dir = today_dir()
    out_path = out_dir / "raw_news.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Collected {len(items)} raw item(s) -> {out_path}")
    return items


if __name__ == "__main__":
    main()
