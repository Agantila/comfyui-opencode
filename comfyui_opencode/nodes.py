from . import client as _client


class OpenCodePromptNode:
    """ComfyUI V3 node that runs a prompt through the local opencode CLI."""

    @classmethod
    def define_schema(cls):
        from comfy_api.latest import io

        return io.Schema(
            node_id="OpenCodePrompt",
            display_name="OpenCode Prompt",
            category="opencode",
            description=(
                "Runs a prompt through the local opencode CLI, using a selectable "
                "model and system prompt. Returns the assistant text."
            ),
            inputs=[
                io.Combo.Input("model", options=_client.list_models()),
                io.String.Input("prompt", multiline=True, default=""),
                io.String.Input("system_prompt", multiline=True, default=""),
                io.Int.Input("timeout", default=300, min=1, max=3600),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    def execute(cls, model, prompt, system_prompt, timeout):
        from comfy_api.latest import io

        text = _client.run_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            timeout=timeout,
        )
        return io.NodeOutput(text)
