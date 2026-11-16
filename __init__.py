"""ComfyUI entrypoint for the opencode custom node.

ComfyUI loads this file as a single module whose generated name embeds the path
(``custom_nodes/comfyui-opencode``), so relative imports into a sub-package
cannot be resolved. Everything therefore lives flat next to this file.

The node module must not be called ``nodes.py``: ComfyUI puts its own ``nodes``
module on sys.path, and the flat import would resolve to that instead.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import opencode_nodes  # noqa: E402
from comfy_api.latest import ComfyExtension, io  # noqa: E402


class OpenCodeExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [opencode_nodes.OpenCodePromptNode]


async def comfy_entrypoint() -> OpenCodeExtension:
    return OpenCodeExtension()
