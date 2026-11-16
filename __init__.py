"""ComfyUI entrypoint for the opencode custom node."""

from comfy_api.latest import ComfyExtension, io

from .nodes import OpenCodePromptNode


class OpenCodeExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [OpenCodePromptNode]


async def comfy_entrypoint() -> OpenCodeExtension:
    return OpenCodeExtension()
