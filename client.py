"""Thin wrapper around the opencode CLI."""

import json
import os
import shlex
import shutil
import subprocess


WORKSPACE_ENV = "OPENCODE_WORKSPACE"
DEFAULT_WORKSPACE = os.path.join(
    os.path.expanduser("~"), ".cache", "comfyui-opencode", "workspace"
)
DEFAULT_TIMEOUT = 300
AGENT_NAME = "comfyui-runner"

# ComfyUI is usually started from a shell that does not source the user's rc files,
# so ~/.opencode/bin is frequently missing from PATH even though the CLI is installed.
BINARY_CANDIDATES = (
    "~/.opencode/bin/opencode",
    "~/.local/bin/opencode",
    "~/.bun/bin/opencode",
    "/usr/local/bin/opencode",
    "/usr/bin/opencode",
)


def workspace_dir():
    return os.environ.get(WORKSPACE_ENV) or DEFAULT_WORKSPACE


def _binary():
    override = os.environ.get("OPENCODE_BIN")
    if override:
        return override
    found = shutil.which("opencode")
    if found:
        return found
    for candidate in BINARY_CANDIDATES:
        path = os.path.expanduser(candidate)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise RuntimeError(
        "opencode CLI not found. Install it from https://opencode.ai or set OPENCODE_BIN "
        "to its absolute path (e.g. /home/<user>/.opencode/bin/opencode)."
    )


def _run(args, timeout, cwd):
    # Invoking the CLI directly through subprocess makes opencode fail with
    # "Agent not found" even though the identical command works from a shell in
    # the same directory with the same environment. Going through a login shell
    # is the only invocation form that reliably resolves project-local agents,
    # so the command is passed as a single shell string with proper quoting.
    command = " ".join(shlex.quote(part) for part in [_binary(), *args])
    try:
        proc = subprocess.run(
            ["/bin/bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"opencode did not finish within {timeout}s")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no output"
        raise RuntimeError(f"opencode exited with {proc.returncode}: {detail}")
    return proc.stdout


def _split_model_ref(model):
    # opencode accepts "provider/model#variant". The variant selects a preset and
    # is not part of the path to the model entry in the config.
    reference = model.split("#", 1)[0]
    if "/" not in reference:
        raise RuntimeError(
            f"model reference {model!r} is not in provider/model form"
        )
    provider, model_id = reference.split("/", 1)
    return provider, model_id


def _write_agent_config(directory, system_prompt, model=None, seed=None):
    # opencode v2 reads agents from the plural "agents" key. The singular "agent"
    # key is accepted without error but its entries never register.
    config = {
        "$schema": "https://opencode.ai/config.json",
        "agents": {
            AGENT_NAME: {
                "description": "ComfyUI prompt processor",
                "mode": "primary",
                "system": system_prompt.strip(),
            }
        },
    }
    if seed is not None and seed >= 0 and model:
        # opencode does not expose a seed setting of its own. The provider's raw
        # request body is the only supported passthrough, so the seed is injected
        # there. A negative seed means "send nothing" and leaves the provider at
        # its default. Providers that do support the field (OpenAI-compatible
        # endpoints, Ollama) then produce reproducible output; others ignore it.
        provider, model_id = _split_model_ref(model)
        config["providers"] = {
            provider: {"models": {model_id: {"body": {"seed": int(seed)}}}}
        }
    with open(os.path.join(directory, "opencode.json"), "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)


def ensure_workspace(system_prompt, model=None, seed=None):
    """Create the reusable workspace, return its path.

    opencode v2 only reads project-local config from a directory it registers as
    a project. Two conditions must both hold for that registration to carry the
    configured agent:

    * the directory must be a git repository, otherwise opencode falls back to
      the "global" project and the local config is never applied;
    * the repository must contain at least one commit, otherwise the follow-up
      call still resolves to "global" and `run` fails with "Agent not found".

    The workspace is created once and reused so the project registration stays
    valid across executions instead of being rebuilt per run.
    """
    directory = workspace_dir()
    os.makedirs(directory, exist_ok=True)
    _write_agent_config(directory, system_prompt, model=model, seed=seed)
    if not os.path.isdir(os.path.join(directory, ".git")):
        _git(directory, "init", "--quiet")
    if _git(directory, "rev-parse", "--verify", "HEAD", check=False).returncode != 0:
        _git(directory, "add", "-A")
        _git(
            directory,
            "-c", "user.email=comfyui-opencode@localhost",
            "-c", "user.name=comfyui-opencode",
            "commit", "--quiet", "-m", "workspace",
        )
    return directory


def _git(directory, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=directory, capture_output=True, text=True, check=check
    )


def _extract_text(stdout):
    parts = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") or {}
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts).strip()


def list_models():
    output = _run(["models"], timeout=60, cwd=os.path.expanduser("~"))
    return [line.strip() for line in output.splitlines() if line.strip()]


def run_prompt(prompt, system_prompt, model, timeout=DEFAULT_TIMEOUT, seed=None):
    directory = ensure_workspace(system_prompt, model=model, seed=seed)
    args = ["--standalone", "run", "--agent", AGENT_NAME, "--format", "json"]
    if model:
        args += ["-m", model]
    args.append(prompt)
    return _extract_text(_run(args, timeout=int(timeout), cwd=directory))
