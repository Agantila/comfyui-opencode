# Contributing

Bug reports and pull requests are welcome.

## Before opening an issue

- Check ComfyUI's console output for lines containing `comfyui-opencode`. Import and schema errors
  are reported there, not in the browser UI.
- Confirm the CLI itself works outside ComfyUI:

  ```bash
  opencode --version
  opencode models | head
  ```

- If the node is missing from the UI, include the `comfyui-opencode` lines from the console plus
  the output of `echo $PATH` **as seen by the ComfyUI process** (not your interactive shell).

## Pull requests

- Keep changes small and focused on one behaviour.
- Run the smoke test before submitting: `python3 tests/smoke.py` — expect `result: 10/10`.
- The files must stay flat in the repository root and the node module must keep its
  `opencode_nodes.py` name. Both are required by how ComfyUI loads custom nodes; the reasoning is
  in [docs/entwicklung.md](docs/entwicklung.md).
- Do not add dependencies. The node deliberately uses only the standard library so it runs inside
  ComfyUI's own environment without installing anything.

## Testing the node load path

A plain `import` does not prove the node loads. Use ComfyUI's real loader:

```python
import sys, asyncio
sys.path.insert(0, "/path/to/ComfyUI")
from nodes import init_extra_nodes
asyncio.run(init_extra_nodes())
import nodes as N
assert "OpenCodePrompt" in N.NODE_CLASS_MAPPINGS
```

Run it with ComfyUI's virtualenv Python, and with the same `PATH` the ComfyUI process has.
