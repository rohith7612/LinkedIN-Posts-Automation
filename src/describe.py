"""Step 5: generate the LinkedIn post caption from the verified digest, using GPT-5 nano."""
import json

from config import today_dir
from llm import ask

SYSTEM_PROMPT = (
    "You write LinkedIn posts for a professional sharing daily AI news updates, "
    "designed to be posted alongside infographic images. "
    "\n\n"
    "CRITICAL: LinkedIn does NOT render markdown. Never use **bold**, _italics_, "
    "`code`, or # headers -- asterisks and underscores show up as literal characters. "
    "Use plain text, emojis, and blank lines for structure instead. "
    "\n\n"
    "Use each story's given emoji as its bullet marker (do not invent different ones), "
    "so the post visually matches the accompanying infographic. Do not add extra "
    "decorative emojis beyond what's specified below -- restraint reads as more "
    "professional than an emoji per line. "
    "\n\n"
    "Follow this exact structure, with a blank line between every section so it's "
    "scannable on mobile:\n"
    "1. One-line hook (can start with a single relevant emoji) that makes someone stop "
    "scrolling -- no generic 'Here's today's AI news' openers.\n"
    "2. Blank line.\n"
    "3. One block per story, each formatted as exactly:\n"
    "   <story emoji> <punchy headline>\n"
    "   <key stat, if one is given>\n"
    "   <one-sentence why-it-matters, in your own concise words>\n"
    "   (blank line before the next story)\n"
    "4. Blank line, then a short closing thought or question to drive comments.\n"
    "5. Blank line, then 3-5 relevant hashtags on one line, no more.\n"
    "\n"
    "Keep the whole post under 1300 characters. Use only facts given below -- never "
    "invent details, numbers, or attributions."
)


def _load_stories(day_dir):
    enriched_path = day_dir / "enriched_stories.json"
    if enriched_path.exists():
        with open(enriched_path, "r", encoding="utf-8") as f:
            return json.load(f), True

    verified_path = day_dir / "verified_stories.json"
    with open(verified_path, "r", encoding="utf-8") as f:
        return json.load(f), False


def build_prompt(stories: list[dict], has_enrichment: bool) -> str:
    lines = ["Write today's LinkedIn post from these verified AI news stories:\n"]
    for s in stories:
        if has_enrichment:
            e = s["enrichment"]
            lines.append(
                f"- Emoji: {e['icon']} | Headline: {e['headline']} | Stat: {e['stat']} | "
                f"Why it matters: {e['hook']} | Full detail: {s['summary']}"
            )
        else:
            lines.append(f"- {s['title']}: {s['summary']}")
    return "\n".join(lines)


def generate_description(stories: list[dict], has_enrichment: bool) -> str:
    prompt = build_prompt(stories, has_enrichment)
    return ask(prompt, system=SYSTEM_PROMPT, reasoning_effort="low")


def main():
    day_dir = today_dir()
    stories, has_enrichment = _load_stories(day_dir)

    if not stories:
        print("No verified stories -- nothing to describe.")
        return None

    description = generate_description(stories, has_enrichment)

    out_path = day_dir / "description.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(description)

    print(f"Description generated -> {out_path}\n")
    print(description)
    return description


if __name__ == "__main__":
    main()
