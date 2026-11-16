# comfyui-opencode

ComfyUI custom node that pipes a prompt through the local [opencode](https://opencode.ai) CLI.
You pick the model in ComfyUI, define a system prompt, and get the assistant text back as a
string you can wire into any prompt input.

Useful for prompt rewriting, translation, caption expansion, or any text transformation you
want a configured LLM (including local Ollama models) to perform inside a workflow.

## Node

`OpenCode Prompt` (category `opencode`)

| Input | Type | Description |
|---|---|---|
| `model` | combo | Populated from `opencode models`, e.g. `deepseek/deepseek-flash`, `ollama/qwen3.5:9b` |
| `prompt` | string (multiline) | The user prompt |
| `system_prompt` | string (multiline) | System prompt / role instruction |
| `timeout` | int | Seconds before the call is aborted, default 300 |

| Output | Type |
|---|---|
| `text` | string |

## Install

```bash
./install.sh /home/deniz/ComfyUI
```

Symlinks this repository into `custom_nodes/comfyui-opencode`. Restart ComfyUI afterwards.

Prerequisites: the `opencode` CLI in `PATH` and a logged-in provider (`opencode auth login`).

## How it works

Each call writes an agent definition into a reusable workspace and runs
`opencode run --agent comfyui-runner --format json`. The JSON event stream is parsed and the
`text` parts are concatenated; reasoning blocks and tool events are ignored.

Workspace: `~/.cache/comfyui-opencode/workspace` (override with `OPENCODE_WORKSPACE`).
Binary override: `OPENCODE_BIN`.

## opencode v2 pitfalls this node works around

These are not documented and cost significant debugging time. If the integration ever
breaks after an opencode upgrade, check them in this order.

### 1. Agents live under `agents`, not `agent`

```json
{"agents": {"comfyui-runner": {"mode": "primary", "system": "..."}}}
```

The singular `agent` key is accepted without any error and its entries are silently ignored.

### 2. The agent name must not contain underscores

`comfyui_runner` fails with `Agent not found`. `comfyui-runner` works.

### 3. The workspace must be a git repository **with at least one commit**

opencode resolves the directory to a project. Without git — and, importantly, with a git
repository that has no commits — it falls back to the `global` project ID and the
project-local `opencode.json` is never applied. `git init` alone is not enough; a commit is
required. `ensure_workspace()` handles both.

### 4. Call through a login shell, not directly via `subprocess`

This is the subtle one. With identical arguments, identical `cwd` and an identical environment:

```
subprocess.run(['opencode', '--standalone', 'run', ...])            # -> "Agent not found"
subprocess.run(['/bin/bash', '-lc', 'opencode --standalone run ...']) # -> works
```

The direct invocation failed 10/10, the shell invocation succeeded 10/10, over repeated
runs. Individual environment variables (`SHELL`, `TERM`, `USER`, `PATH`), a PTY,
`start_new_session`, cleaned `OPENCODE_PASSWORD` and passing the shell's full environment
were all ruled out. The cause is not isolated; `_run()` therefore invokes through
`/bin/bash -lc`.

### 5. `--standalone` is required

Without it the call attaches to the background service, which keeps whatever directory it
was first started in and ignores `cwd` entirely.

## Tests

```bash
python3 tests/smoke.py                       # default model
python3 tests/smoke.py ollama/qwen3.5:9b     # specific model
```

`smoke.py` runs 10 consecutive prompts against a fresh workspace and asserts the system
prompt was actually applied. A pass looks like `result: 10/10`.

## Environment note

On this machine `comfy_api.latest` fails to import inside a bare `python3` process because
`comfy/storage.py` needs `comfy_aimdo.storage`, which is missing from the installed
`comfy_aimdo` package. That is unrelated to this node — it affects ComfyUI globally. Node
tests above stub that one module to exercise the node in isolation.
