#!/usr/bin/env python3
"""Smoke test for the opencode client. Requires a working opencode CLI login.

Usage: python3 tests/smoke.py [model]
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import client  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek/deepseek-flash"
SYSTEM = "Antworte ausschliesslich in GROSSBUCHSTABEN und beende mit ZEBRA."


def main():
    models = client.list_models()
    print(f"models: {len(models)}")
    assert MODEL in models, f"{MODEL} not in model list"

    print(f"workspace: {client.workspace_dir()}")
    path = client.ensure_workspace(SYSTEM)
    print(f"prepared: {path}")

    failures = 0
    start = time.time()
    for i in range(10):
        try:
            text = client.run_prompt(f"Sag Test{i}", SYSTEM, MODEL, timeout=120)
        except RuntimeError as exc:
            failures += 1
            print(f"  {i}: ERROR {str(exc)[-60:]}")
            continue
        ok = "ZEBRA" in text and text.upper() == text
        failures += not ok
        print(f"  {i}: {'ok' if ok else 'FAIL'} {text[:40]!r}")

    print(f"result: {10 - failures}/10 in {time.time() - start:.0f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
