# ComfyUI OpenCode

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom%20node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

A ComfyUI custom node that runs your prompt through the [opencode](https://opencode.ai) CLI, so
any LLM you have configured there — cloud models, local Ollama models, or your own agent setup —
becomes usable inside a ComfyUI workflow.

Pick the model in the node, write a system prompt, get the assistant's text back as a string you
can wire into any prompt input.

```
prompt ─────────┐
system_prompt ──┤──> OpenCode Prompt ──> text ──> CLIP Text Encode / your next node
model ──────────┘
```

## Why

Prompt inputs in ComfyUI are static text. This node makes them dynamic: rewrite a rough idea into
a detailed image prompt, translate on the fly, expand a concept into variations, generate captions,
or keep style instructions in one place and reuse them across a workflow.

Because it goes through opencode, you are not locked into one provider. Whatever `opencode models`
lists is selectable — including models that are only reachable through a local CLI setup.

## Features

- **Model selection in the UI** — the combo box is populated from `opencode models`, so it always
  matches what you actually have configured (108 models on the reference setup).
- **System prompt as a node input** — the model's role is part of the workflow, not a config file.
- **Any provider** — cloud models, local Ollama, mixed setups. No extra API keys inside ComfyUI.
- **String in, string out** — drops into any existing prompt chain without conversion nodes.
- **Reusable agent workspace** — a prepared opencode workspace persists between runs.
- **No background service required** — each call runs the CLI standalone.

## Node reference

`OpenCode Prompt` (category `opencode`)

| Input | Type | Default | Description |
|---|---|---|---|
| `model` | combo | first available | Populated from `opencode models`, e.g. `deepseek/deepseek-flash`, `ollama/qwen3.5:9b` |
| `prompt` | string (multiline) | empty | The user prompt |
| `system_prompt` | string (multiline) | empty | System prompt / role instruction |
| `timeout` | int | 300 | Seconds before the call is aborted (1–3600) |

| Output | Type | Description |
|---|---|---|
| `text` | string | The assistant's reply |

## Requirements

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (tested with v0.45.4)
- [opencode CLI](https://opencode.ai) — installed and logged in (`opencode auth login`)
- Python 3.10+ (ComfyUI's own environment is fine, no extra packages)

Verify the CLI before installing:

```bash
opencode --version
opencode models | head
```

## Installation

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/Agantila/comfyui-opencode.git
```

Restart ComfyUI. The node appears under category **`opencode`** as **`OpenCode Prompt`**.

From a local checkout, `./install.sh /path/to/ComfyUI` creates the symlink for you.

## Usage

1. Add `OpenCode Prompt` (right-click canvas → Add Node → opencode → OpenCode Prompt).
2. Pick a `model` from the dropdown.
3. Write your `prompt`.
4. Write a `system_prompt`. Example:

   ```
   You are a prompt engineer for image generation. Rewrite the user's idea as one detailed,
   comma-separated English prompt. Output only the prompt, no explanation.
   ```

5. Connect the `text` output to a `CLIP Text Encode` node.

`timeout` defaults to 300 seconds. Calls are blocking — for slow models or long prompts, raise it.

### Example

| | |
|---|---|
| `prompt` | `Ein roter Apfel auf einem Holztisch` |
| `system_prompt` | `Answer with one comma-separated English image prompt, no explanation.` |
| `text` output | `A single glossy red apple with a fresh green leaf resting on a rustic wooden table, rich crimson skin with soft highlights, visible wood grain, warm natural light` |

That output is a real result from this node.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENCODE_BIN` | auto-detected | Absolute path to the opencode binary |
| `OPENCODE_WORKSPACE` | `~/.cache/comfyui-opencode/workspace` | Directory for the reusable agent workspace |

## Troubleshooting

**Node does not appear in the UI.** Search ComfyUI's console output for `comfyui-opencode`. If the
schema cannot be built, the whole node is hidden instead of showing an error in the UI. The most
common cause is that the opencode CLI is missing from the ComfyUI process's `PATH` — ComfyUI is
often started from an environment that never sourced your shell rc files. The node searches the
usual install locations itself (`~/.opencode/bin`, `~/.local/bin`, `~/.bun/bin`, `/usr/local/bin`,
`/usr/bin`); if that fails, set `OPENCODE_BIN`.

**`Agent not found`.** opencode v2 has undocumented behaviour around project-local agents. The node
handles it, but it is worth knowing if you adapt the code — see
[docs/entwicklung.md](docs/entwicklung.md).

**Calls are slow.** Each call starts the CLI fresh; model latency dominates. Use a faster model for
interactive work.

**Ollama models missing from the dropdown.** The list is read once at node-registration time.
Restart ComfyUI after pulling a new model.

## How it works

Each call writes an agent definition into a reusable workspace and runs
`opencode run --agent comfyui-runner --format json`. The JSON event stream is parsed and the
`text` parts are concatenated; reasoning blocks and tool events are ignored.

The workspace is a small git repository with one commit, because opencode v2 only reads
project-local agent configuration from a directory it registers as a project.

### opencode v2 pitfalls this node works around

Undocumented, and each one costs hours if you hit it. Check them in this order after an upgrade.

1. **Agents live under `agents`, not `agent`.** The singular key is accepted without error and its
   entries are silently ignored.
2. **The agent name must not contain underscores.** `comfyui_runner` fails, `comfyui-runner` works.
3. **The workspace must be a git repository with at least one commit.** Without commits opencode
   falls back to the `global` project and never applies the local config.
4. **Call through a login shell.** The identical command through `subprocess` fails 10/10 with
   `Agent not found` while `/bin/bash -lc` succeeds 10/10. Cause not isolated.
5. **`--standalone` is required**, otherwise the call attaches to the background service, which
   ignores `cwd`.

Full detail in [docs/entwicklung.md](docs/entwicklung.md) (German).

### Layout note

The files sit flat in the repository root on purpose. ComfyUI loads a custom node directory under a
module name containing path separators, so relative imports into a sub-package cannot resolve. For
the same reason the node module is `opencode_nodes.py` and not `nodes.py`, which would collide with
ComfyUI's own module.

## Development

```
__init__.py          ComfyUI entrypoint (comfy_entrypoint)
opencode_nodes.py    Node definition (V3 schema)
client.py            opencode CLI wrapper, workspace management
tests/smoke.py       10-run stability test
docs/entwicklung.md  Debug history and architecture decisions (German)
```

Run the smoke test after changes:

```bash
python3 tests/smoke.py                    # default model
python3 tests/smoke.py ollama/qwen3.5:9b  # specific model
```

Expect `result: 10/10`. The test asserts the system prompt is actually applied, so a silently
ignored prompt fails it.

## Compatibility

- ComfyUI v0.45.4 (V3 node schema, `comfy_api.latest`)
- opencode v2.2.7
- Linux (developed and tested on Fedora/Nobara with AMD ROCm)

## License

[MIT](LICENSE)

---

Deutsch: [README.de.md](README.de.md)
