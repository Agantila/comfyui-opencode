#!/usr/bin/env python3
"""Verify that the seed actually reaches the model and changes sampling.

The seed is passed to the provider's raw request body, so it only has an effect
on providers that support it. Ollama does; many cloud models silently ignore it
(DeepSeek was tested and ignores it). Defaults to a local Ollama model because
it is free and fast enough for repeated calls.

Usage: python3 tests/seed.py [provider/model]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import client  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "ollama/qwen3.5:4b"
PROMPT = "Erfinde einen Fantasienamen. Antworte mit genau einem Wort."
SYSTEM = "Antworte mit genau einem Wort."


def ask(seed):
    return client.run_prompt(PROMPT, SYSTEM, MODEL, timeout=200, seed=seed)


def main():
    provider, model_id = client._split_model_ref(MODEL)
    print(f"{MODEL} -> provider {provider!r}, model {model_id!r}")

    config_path = os.path.join(client.workspace_dir(), "opencode.json")
    client.ensure_workspace(SYSTEM, model=MODEL, seed=1)
    with open(config_path, encoding="utf-8") as handle:
        config = handle.read()
    assert '"seed"' in config, f"seed missing from {config_path}"
    print(f"workspace config carries the seed: {config_path}")

    a1 = ask(42)
    a2 = ask(42)
    b1 = ask(7)
    print(f"seed 42: {a1!r} / {a2!r}")
    print(f"seed  7: {b1!r}")

    if a1 != a2:
        print("FAIL: identical seed produced different output — this provider ignores the seed")
        return 1
    if a1 == b1:
        print("INCONCLUSIVE: different seeds produced identical output")
        return 1
    print("result: seed is honoured (same seed identical, different seed differs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
