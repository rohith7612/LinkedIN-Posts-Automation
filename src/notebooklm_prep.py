"""Step 4: build the NotebookLM source digest and hand off to you for infographic generation.

NotebookLM has no public API, so this step is intentionally semi-automated:
this script prepares the content and opens the browser tab; a human generates
the actual visual output (Video Overview / Mind Map / slides) and drops the
exported image(s) into the day's infographics folder. Phase 2 (describe +
post to LinkedIn) picks up from there once you run it.

Two files are produced for you to hand to NotebookLM:
  - digest.md            -> paste as a SOURCE (the content to summarize)
  - notebooklm_prompt.txt -> paste into the "Customize" box when generating
                             the Video Overview / infographic (the *style*
                             instructions for how it should look)
"""
import json
import webbrowser
from datetime import date

import pyperclip

from config import today_dir
from llm import ask

NOTEBOOKLM_URL = "https://notebooklm.google.com/"

ENRICH_SYSTEM_PROMPT = (
    "You turn a news blurb into structured fields for an infographic slide. "
    "Respond with EXACTLY four lines, no extra commentary:\n"
    "HEADLINE: <punchy restatement of the story, max 8 words, no ending period>\n"
    "STAT: <the single most attention-grabbing number/fact from the text, e.g. "
    "'$65M raised' or '9M users' -- if genuinely no notable number exists, write "
    "a 2-3 word key fact instead, never leave blank>\n"
    "HOOK: <one sentence, max 16 words, plain language, on why this matters>\n"
    "ICON: <exactly one emoji that best represents the story's category "
    "(funding/money, product launch, research, policy/legal, education, etc.)>"
)

FALLBACK_ICON = "\U0001F4F0"  # newspaper


def _enrich_story(story: dict) -> dict:
    prompt = f"Title: {story['title']}\nSummary: {story['summary']}"
    try:
        raw = ask(prompt, system=ENRICH_SYSTEM_PROMPT, reasoning_effort="low")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] enrichment failed for '{story['title'][:40]}...': {exc}")
        raw = ""

    fields = {"headline": story["title"], "stat": "", "hook": "", "icon": FALLBACK_ICON}
    for line in raw.splitlines():
        if line.upper().startswith("HEADLINE:"):
            fields["headline"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("STAT:"):
            fields["stat"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("HOOK:"):
            fields["hook"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("ICON:"):
            fields["icon"] = line.split(":", 1)[1].strip() or FALLBACK_ICON
    return fields


def enrich_stories(stories: list[dict]) -> list[dict]:
    return [_enrich_story(s) for s in stories]


def build_digest(stories: list[dict], enriched: list[dict], day: date) -> str:
    lines = [f"# AI News Digest -- {day.isoformat()}", ""]

    lines.append("## At a glance")
    for e in enriched:
        lines.append(f"- {e['icon']} {e['headline']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, (story, e) in enumerate(zip(stories, enriched), start=1):
        v = story["verification"]
        lines.append(f"## {e['icon']} Story {i}: {e['headline']}")
        lines.append(f"**Key stat:** {e['stat']}")
        lines.append(f"**Why it matters:** {e['hook']}")
        lines.append("")
        lines.append(f"**Full summary:** {story['summary']}")
        lines.append("")
        lines.append(f"*Sources: {', '.join(story['sources'])} | Verification: {v['tier']} -- {v['note']}*")
        lines.append(f"\nRead more: {story['primary_link']}")
        lines.append("")

    return "\n".join(lines)


NOTEBOOKLM_GENERATION_PROMPT = """\
Create a fast-paced, visually bold Video Overview that works as a daily AI \
news infographic reel for LinkedIn. Follow these rules:

1. One story per scene, in the exact order given in the source ("Story 1", \
"Story 2", etc.) -- do not merge, skip, or reorder them.
2. Open each scene with the story's HEADLINE in large, bold on-screen text, \
paired with its ICON as a recurring visual motif for that story.
3. Immediately show the story's "Key stat" as a big, high-contrast number or \
callout -- this should be the single most eye-catching element in the scene.
4. Follow with the "Why it matters" line as a short supporting caption. Do \
NOT read out or display the full dense paragraph -- keep on-screen text short.
5. Use ONE consistent color palette and typography across every scene (e.g. \
deep blue/purple background with white and one bright accent color) so the \
whole thing reads as one branded daily series, not five unrelated slides.
6. Use simple modern icons/illustrations relevant to each story's topic \
instead of generic stock photography (money/growth for funding, rocket/app \
for product launches, scale or cap for policy/education, etc.).
7. Keep pacing brisk -- a few seconds per story -- built to hook a scrolling \
LinkedIn audience in the first 3 seconds and hold attention throughout.
8. End with one closing card titled "Today's AI Headlines" that recaps all \
the headlines as a short list, plus the line "Follow for daily AI updates."
9. Do not invent facts, numbers, or details that are not present in the source.
"""


def main():
    day_dir = today_dir()
    verified_path = day_dir / "verified_stories.json"
    with open(verified_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    if not stories:
        print("No verified stories today -- nothing to send to NotebookLM. Stopping phase 1.")
        return

    print("Enriching stories for infographic-ready formatting (headline/stat/hook/icon)...")
    enriched = enrich_stories(stories)

    enriched_path = day_dir / "enriched_stories.json"
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(
            [{**story, "enrichment": e} for story, e in zip(stories, enriched)],
            f,
            indent=2,
            ensure_ascii=False,
        )

    digest = build_digest(stories, enriched, date.today())
    digest_path = day_dir / "digest.md"
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(digest)

    prompt_path = day_dir / "notebooklm_prompt.txt"
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(NOTEBOOKLM_GENERATION_PROMPT)

    infographics_dir = day_dir / "infographics"
    infographics_dir.mkdir(exist_ok=True)

    try:
        pyperclip.copy(digest)
        clipboard_msg = "The digest text has been copied to your clipboard -- just paste it in as a source."
    except Exception:
        clipboard_msg = "(Could not access clipboard automatically -- open digest.md and copy it manually.)"

    webbrowser.open(NOTEBOOKLM_URL)

    print("=" * 70)
    print("PHASE 1 COMPLETE -- manual step required")
    print("=" * 70)
    print(f"Digest saved to: {digest_path}")
    print(clipboard_msg)
    print()
    print("Now, in the NotebookLM tab that just opened:")
    print("  1. Create a new notebook (or reuse a daily one).")
    print("  2. Add a source -> 'Paste text' -> paste the digest -> Insert.")
    print("  3. In the Studio panel, click Video Overview (or your preferred")
    print("     visual format) -> click the customize/pencil icon -> paste in")
    print("     the generation prompt below (also saved for you), then Generate.")
    print("  4. Export/download the resulting image(s) or slide frames.")
    print(f"  5. Save them into: {infographics_dir}")
    print()
    print(f"Generation prompt (also saved to {prompt_path}):")
    print("-" * 70)
    print(NOTEBOOKLM_GENERATION_PROMPT)
    print("-" * 70)
    print("When the infographic(s) are in that folder, run phase 2:")
    print("     run_phase2.bat   (or: python src/pipeline.py phase2)")
    print("=" * 70)


if __name__ == "__main__":
    main()
