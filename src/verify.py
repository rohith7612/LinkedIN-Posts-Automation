"""Step 3: verify selected stories before they go any further.

IMPORTANT LIMITATION: this is NOT a full fact-checking system. It combines two
cheap, honest signals:
  1. Corroboration -- how many independent outlets in our feed list ran a
     matching headline (computed already in preprocess.py).
  2. An LLM plausibility pass -- GPT-5 nano reads the summary and flags internal
     inconsistencies, extraordinary/unsourced claims, or clickbait phrasing it
     would expect a careful editor to double-check.

Nothing here confirms a story is objectively true. Stories flagged "caution"
are kept (not silently dropped) so you can eyeball them before they reach
NotebookLM / LinkedIn.
"""
import json

from config import today_dir
from llm import ask

OFFICIAL_SOURCES = {"OpenAI Blog", "Google AI Blog"}

SYSTEM_PROMPT = (
    "You are a careful news editor doing a quick plausibility check on an AI news "
    "blurb before publication. You are NOT verifying facts against the live internet "
    "(you have no browsing access) -- you are only checking internal consistency, "
    "whether claims are properly attributed (e.g. 'according to X' vs stated as bare "
    "fact), and whether the tone is measured rather than sensational. "
    "Respond with exactly two lines:\n"
    "VERDICT: <one of VERIFIED, CAUTION>\n"
    "NOTE: <one short sentence explaining why>"
)


def _llm_sanity_check(story: dict) -> tuple[str, str]:
    prompt = f"Title: {story['title']}\nSummary: {story['summary']}\nSources: {', '.join(story['sources'])}"
    try:
        raw = ask(prompt, system=SYSTEM_PROMPT)
    except Exception as exc:  # noqa: BLE001
        return "CAUTION", f"LLM check unavailable ({exc})"

    verdict, note = "CAUTION", "Could not parse LLM response."
    for line in raw.splitlines():
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("NOTE:"):
            note = line.split(":", 1)[1].strip()
    return verdict, note


def verify_stories(stories: list[dict]) -> list[dict]:
    verified = []
    for story in stories:
        if story["corroboration_count"] >= 2:
            story["verification"] = {
                "tier": "VERIFIED",
                "note": f"Corroborated by {story['corroboration_count']} independent sources.",
            }
        elif any(s in OFFICIAL_SOURCES for s in story["sources"]):
            story["verification"] = {
                "tier": "VERIFIED",
                "note": "Published directly by the primary/official source blog.",
            }
        else:
            verdict, note = _llm_sanity_check(story)
            story["verification"] = {"tier": verdict, "note": note}
        verified.append(story)
    return verified


def main():
    day_dir = today_dir()
    stories_path = day_dir / "stories.json"
    with open(stories_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    verified = verify_stories(stories)

    out_path = day_dir / "verified_stories.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(verified, f, indent=2, ensure_ascii=False)

    print(f"Verified {len(verified)} storie(s) -> {out_path}")
    for s in verified:
        v = s["verification"]
        print(f"  - [{v['tier']}] {s['title']} -- {v['note']}")
    return verified


if __name__ == "__main__":
    main()
