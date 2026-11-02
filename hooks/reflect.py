"""Stop: once enough new tokens have passed, ask Claude to record what it learned.

Reads the transcript incrementally, adds up new tokens (input + cache writes +
output of each assistant message), and collects failed tool calls as evidence.
When the total passes the spacing (MONET_REFLECT_EVERY_TOKENS or the plugin's
`reflect_every_tokens` option; off by default), it blocks the
stop once with a reflection prompt, so Claude records learnings in the notebook.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import notebook  # noqa: E402

DEFAULT_SPACING = 0  # off unless the user sets a spacing
MAX_EVIDENCE = 20

QUESTIONS = (
    "Reflect on what you learned since the last reflection. What surprised you? Which failures taught something, "
    "and what worked instead? Did you find how to reach an environment or service, a harness pitfall, or a user "
    'correction worth keeping? Record each learning with `monet-notebook add "<learning>"`, and skip ordinary '
    "failures that taught nothing. If nothing is worth keeping, say so in one line."
)


def reflection_prompt(evidence):
    if not evidence:
        return QUESTIONS
    return QUESTIONS + "\n\nFailed tool calls since the last reflection:\n" + "\n".join(f"- {e}" for e in evidence)


def describe_call(name, tool_input):
    tool_input = tool_input or {}
    for key in ("command", "file_path", "path", "pattern", "url"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return f"{name}: `{value.splitlines()[0][:200]}`"
    return name


def scan(transcript, state):
    """Advance state over transcript lines appended since the last scan."""
    path = Path(transcript)
    size = path.stat().st_size
    offset = state.get("offset", 0)
    if offset > size:  # transcript was rewritten; start over
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    end = data.rfind(b"\n")
    if end < 0:
        return state
    chunk, state["offset"] = data[: end + 1], offset + end + 1
    seen = set(state.get("messages", [])[-200:])
    calls = state.setdefault("calls", {})
    evidence = state.setdefault("evidence", [])
    for raw in chunk.splitlines():
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        message = entry.get("message") or {}
        content = message.get("content")
        if entry.get("type") == "assistant":
            mid = message.get("id")
            usage = message.get("usage") or {}
            if mid and mid not in seen:
                seen.add(mid)
                state["tokens"] = state.get("tokens", 0) + sum(
                    int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "output_tokens")
                )
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_use":
                    calls[block.get("id")] = describe_call(block.get("name", "tool"), block.get("input"))
        elif entry.get("type") == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result" and block.get("is_error"):
                    item = calls.get(block.get("tool_use_id"))
                    if item and item not in evidence and len(evidence) < MAX_EVIDENCE:
                        evidence.append(item)
    state["messages"] = list(seen)[-200:]
    # Keep only calls that may still get a result.
    if len(calls) > 200:
        state["calls"] = dict(list(calls.items())[-100:])
    return state


def decide(event, state, spacing):
    """Return (hook output or None, new state)."""
    transcript = event.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return None, state
    state = scan(transcript, state)
    if spacing <= 0 or state.get("tokens", 0) < spacing or event.get("stop_hook_active"):
        return None, state
    prompt = reflection_prompt(state.get("evidence", []))
    state.update(tokens=0, evidence=[], calls={})
    return {"decision": "block", "reason": prompt}, state


def main():
    event = json.load(sys.stdin)
    sid = event.get("session_id")
    if not sid:
        return
    try:
        spacing = int(notebook.option("reflect_every_tokens", DEFAULT_SPACING))
    except ValueError:
        spacing = DEFAULT_SPACING
    state_file = notebook.notebook_dir() / f"{notebook.session_id(sid)}.reflect.json"
    try:
        state = json.loads(state_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    output, state = decide(event, state, spacing)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))
    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # never trap the session
        print(f"monet reflect: {error}", file=sys.stderr)
