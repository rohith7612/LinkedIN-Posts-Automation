"""Orchestrator CLI.

Usage:
    python src/pipeline.py phase1   # collect -> preprocess -> verify -> prep NotebookLM (scheduled daily)
    python src/pipeline.py phase2   # describe -> post to LinkedIn (run manually after infographics are ready)
    python src/pipeline.py auth     # one-time LinkedIn OAuth setup
"""
import sys

import collect
import describe
import linkedin_auth
import linkedin_post
import notebooklm_prep
import preprocess
import verify


def phase1():
    print("\n=== [1/4] Collecting news ===")
    raw_items = collect.main()
    if not raw_items:
        print("No news items collected in this window. Stopping.")
        return

    print("\n=== [2/4] Preprocessing & deduping ===")
    stories = preprocess.main()
    if not stories:
        print("No stories survived preprocessing. Stopping.")
        return

    print("\n=== [3/4] Verifying ===")
    verify.main()

    print("\n=== [4/4] Preparing NotebookLM handoff ===")
    notebooklm_prep.main()


def phase2():
    print("\n=== [1/2] Generating description ===")
    description = describe.main()
    if not description:
        return

    print("\n=== [2/2] Posting to LinkedIn ===")
    linkedin_post.main()


def auth():
    linkedin_auth.run_auth_flow()


COMMANDS = {"phase1": phase1, "phase2": phase2, "auth": auth}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python {sys.argv[0]} <{'|'.join(COMMANDS)}>")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
