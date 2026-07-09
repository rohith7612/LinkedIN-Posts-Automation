"""Step 2: clean raw RSS entries, cluster duplicate stories across sources, rank, and select top N."""
import json
import re

from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from config import SETTINGS, today_dir


def clean_html(raw: str) -> str:
    text = BeautifulSoup(raw or "", "html.parser").get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    # feedparser occasionally mis-decodes numeric entities like &#8217; into the
    # unicode replacement char instead of a curly apostrophe -- patch that up.
    text = text.replace("", "'")
    return text


def cluster_stories(items: list[dict]) -> list[dict]:
    """Group near-duplicate headlines (same underlying story from different outlets)."""
    threshold = SETTINGS["dedupe_similarity_threshold"]
    clusters: list[dict] = []

    for item in items:
        title = item["title"]
        best_cluster = None
        best_score = 0
        for cluster in clusters:
            score = fuzz.token_set_ratio(title, cluster["title"])
            if score > best_score:
                best_score, best_cluster = score, cluster

        if best_cluster is not None and best_score >= threshold:
            best_cluster["members"].append(item)
        else:
            clusters.append({"title": title, "members": [item]})

    return clusters


def clean_and_select(raw_items: list[dict]) -> list[dict]:
    for item in raw_items:
        item["title"] = clean_html(item["title"])
        item["summary"] = clean_html(item["summary"])

    # drop items with empty title/summary (broken feed entries)
    raw_items = [i for i in raw_items if i["title"] and i["summary"]]

    clusters = cluster_stories(raw_items)

    stories = []
    for cluster in clusters:
        members = sorted(cluster["members"], key=lambda m: len(m["summary"]), reverse=True)
        best = members[0]
        sources = sorted({m["source"] for m in members})
        stories.append(
            {
                "title": best["title"],
                "summary": best["summary"],
                "primary_link": best["link"],
                "all_links": [m["link"] for m in members],
                "sources": sources,
                "corroboration_count": len(sources),
                "published": best["published"],
            }
        )

    # Rank: more independent sources reporting it first, then most recent.
    stories.sort(key=lambda s: (s["corroboration_count"], s["published"]), reverse=True)
    top_n = SETTINGS["top_n_stories"]
    return stories[:top_n]


def main():
    day_dir = today_dir()
    raw_path = day_dir / "raw_news.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    stories = clean_and_select(raw_items)

    out_path = day_dir / "stories.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)

    print(f"Selected {len(stories)} top storie(s) from {len(raw_items)} raw item(s) -> {out_path}")
    for s in stories:
        print(f"  - [{s['corroboration_count']} source(s)] {s['title']}")
    return stories


if __name__ == "__main__":
    main()
