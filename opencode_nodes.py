from comfy_api.latest import io

import client


class OpenCodePromptNode(io.ComfyNode):
    """ComfyUI V3 node that runs a prompt through the local opencode CLI."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="OpenCodePrompt",
            display_name="OpenCode Prompt",
            category="opencode",
            description=(
                "Runs a prompt through the local opencode CLI, using a selectable "
                "model, system prompt and seed. Returns the assistant text."
            ),
            inputs=[
                io.Combo.Input("model", options=client.list_models()),
                io.String.Input("prompt", multiline=True, default=""),
                io.String.Input("system_prompt", multiline=True, default=""),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=-1,
                    max=0xFFFFFFFF,
                    control_after_generate=True,
                ),
                io.Int.Input("timeout", default=300, min=1, max=3600),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    def execute(cls, model, prompt, system_prompt, seed, timeout) -> io.NodeOutput:
        text = client.run_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            timeout=timeout,
            seed=seed,
        )
        return io.NodeOutput(text)
