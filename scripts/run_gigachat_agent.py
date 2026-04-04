#!/usr/bin/env python3
"""
Agentic SWE-bench inference using GigaChat tool calling.

Instead of single-pass patch generation, uses a multi-turn agent loop:
  1. Model reads the issue and the pre-retrieved BM25 code context
  2. Calls view_file() to explore files it needs to understand
  3. Calls str_replace() to make targeted, exact-match edits
  4. Calls finish() when done

The script accumulates str_replace operations and generates a proper unified diff
using Python's difflib - no need for the model to write diff syntax itself.

Key advantage: str_replace is much more reliable than unified diff generation
because the model only needs to reproduce the exact string, not format hunk headers.
"""

import json
import re
import time
import logging
import argparse
import difflib
from pathlib import Path

from datasets import load_dataset
from openai import OpenAI
from tqdm.auto import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MAX_TURNS = 8
MAX_TOKENS_PER_TURN = 2048

SYSTEM_PROMPT = (
    "You are an expert software engineer fixing GitHub issues.\n\n"
    "You have access to tools to explore code and make changes:\n"
    "- view_file(path) - view a file with line numbers\n"
    "- str_replace(path, old_str, new_str) - replace an exact string in a file\n"
    "- finish(summary) - call when all changes are made\n\n"
    "STRATEGY:\n"
    "1. Read the issue carefully to understand what is broken\n"
    "2. Call view_file() on the relevant files shown in the context to see exact content\n"
    "3. Call str_replace() with the EXACT string to replace and the fix\n"
    "   - old_str must match EXACTLY, including whitespace and indentation\n"
    "   - make the change minimal - only touch what is needed\n"
    "4. Call finish() with a summary of what you changed\n\n"
    "Important: use str_replace, not unified diff. The str_replace tool handles formatting for you."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "View the full content of a file with line numbers. Use this to see exact code before making changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file relative to repository root (e.g. 'django/db/models/query.py')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": (
                "Replace an exact string in a file with new content. "
                "old_str must match the file content EXACTLY (same whitespace, indentation). "
                "Use view_file first to see the exact content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "The exact string to replace. Must match file content verbatim.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement string. Can be empty string to delete old_str.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal that all necessary changes have been made. Call this when done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief description of what was changed and why.",
                    }
                },
                "required": ["summary"],
            },
        },
    },
]


def parse_bm25_files(text: str) -> dict[str, str]:
    """Parse [start of path]...[end of path] blocks into a dict of path -> content.

    The BM25 format includes line numbers: '  42 code here'. These are stripped
    when loading into the file state so str_replace works on clean content.
    """
    files = {}
    for m in re.finditer(r"\[start of ([^\]]+)\](.*?)\[end of [^\]]+\]", text, re.DOTALL):
        path = m.group(1).strip()
        raw = m.group(2)
        # Strip leading line numbers: "  42 content" -> "content"
        clean_lines = []
        for line in raw.split("\n"):
            stripped = re.sub(r"^\s*\d+ ?", "", line, count=1) if re.match(r"^\s*\d+ ", line) else line
            clean_lines.append(stripped)
        # Remove first/last blank lines from the block
        content = "\n".join(clean_lines).strip("\n")
        files[path] = content
    return files


def add_line_numbers(content: str) -> str:
    """Add line numbers to content for display in view_file."""
    lines = content.split("\n")
    width = len(str(len(lines)))
    return "\n".join(f"{str(i + 1).rjust(width)} {line}" for i, line in enumerate(lines))


def apply_str_replace(files: dict, path: str, old_str: str, new_str: str) -> tuple[bool, str]:
    """Apply a str_replace operation. Returns (success, message)."""
    content = files.get(path)
    if content is None:
        # Try fuzzy path match (e.g. model omits leading directory)
        matches = [p for p in files if p.endswith(path) or path.endswith(p.split("/")[-1])]
        if len(matches) == 1:
            path = matches[0]
            content = files[path]
        else:
            return False, f"File '{path}' not found in context. Available: {list(files.keys())[:5]}"

    if old_str not in content:
        # Check if it's a whitespace mismatch (common error)
        normalized_content = re.sub(r"\t", "    ", content)
        normalized_old = re.sub(r"\t", "    ", old_str)
        if normalized_old in normalized_content:
            content = normalized_content
            old_str = normalized_old
            files[path] = content
        else:
            return False, (
                f"old_str not found in {path}. "
                f"Make sure it matches exactly (use view_file to check the exact content)."
            )

    if content.count(old_str) > 1:
        return False, f"old_str appears {content.count(old_str)} times in {path}. Make it more specific."

    files[path] = content.replace(old_str, new_str, 1)
    return True, f"Replaced in {path}: {len(old_str)} chars -> {len(new_str)} chars"


def generate_patch(original_files: dict, modified_files: dict) -> str:
    """Generate unified diff from file state changes."""
    parts = []
    for path in modified_files:
        orig = original_files.get(path, "")
        modified = modified_files[path]
        if orig == modified:
            continue
        orig_lines = orig.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        # Ensure files end with newline for clean diffs
        if orig_lines and not orig_lines[-1].endswith("\n"):
            orig_lines[-1] += "\n"
        if mod_lines and not mod_lines[-1].endswith("\n"):
            mod_lines[-1] += "\n"
        diff = list(
            difflib.unified_diff(
                orig_lines,
                mod_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        if diff:
            parts.append(f"diff --git a/{path} b/{path}")
            parts.extend(diff)
            parts.append("")
    return "\n".join(parts)


def run_agent(client: OpenAI, model_name: str, instance_id: str, text: str) -> dict:
    """Run the agentic loop for one SWE-bench instance."""
    # Strip BM25 preamble
    lines = text.split("\n", 1)
    user_content = lines[1] if len(lines) == 2 else text

    # Parse file state from BM25 context
    original_files = parse_bm25_files(user_content)
    current_files = {k: v for k, v in original_files.items()}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    turns = 0
    tool_calls_log = []
    finish_called = False
    finish_summary = ""

    while turns < MAX_TURNS:
        turns += 1
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0,
                max_tokens=MAX_TOKENS_PER_TURN,
            )
        except Exception as e:
            logger.error(f"[{instance_id}] API error on turn {turns}: {e}")
            break

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Append assistant message
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls or []})

        if not msg.tool_calls:
            # No tool calls - model finished without calling finish()
            logger.info(f"[{instance_id}] Turn {turns}: no tool calls, stopping (finish_reason={finish_reason})")
            break

        # Process tool calls
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            tool_calls_log.append({"turn": turns, "function": fn_name, "args": args})

            if fn_name == "view_file":
                path = args.get("path", "")
                content = current_files.get(path)
                if content is None:
                    # Try suffix match
                    matches = [p for p in current_files if p.endswith(path) or path.endswith(p.split("/")[-1])]
                    if matches:
                        path = matches[0]
                        content = current_files[path]
                if content is not None:
                    result = f"[File: {path}]\n{add_line_numbers(content)}"
                else:
                    result = f"File '{path}' not in context. Available files: {list(current_files.keys())}"

            elif fn_name == "str_replace":
                path = args.get("path", "")
                old_str = args.get("old_str", "")
                new_str = args.get("new_str", "")
                success, msg_text = apply_str_replace(current_files, path, old_str, new_str)
                result = msg_text

            elif fn_name == "finish":
                finish_called = True
                finish_summary = args.get("summary", "")
                result = "Done. Changes recorded."

            else:
                result = f"Unknown tool: {fn_name}"

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        if finish_called:
            logger.info(f"[{instance_id}] Turn {turns}: finish() called")
            break

    patch = generate_patch(original_files, current_files)
    if patch and not patch.endswith("\n"):
        patch += "\n"

    return {
        "patch": patch,
        "turns": turns,
        "tool_calls": tool_calls_log,
        "finish_called": finish_called,
        "finish_summary": finish_summary,
        "files_modified": [p for p in current_files if current_files[p] != original_files.get(p, "")],
    }


def load_lite_instance_ids() -> set:
    """Load instance IDs from SWE-bench Lite."""
    logger.info("Loading SWE-bench Lite instance IDs...")
    lite_ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    ids = {item["instance_id"] for item in lite_ds}
    logger.info(f"Loaded {len(ids)} Lite instance IDs")
    return ids


def main(
    api_base: str,
    model_name: str,
    output_file: str,
    max_instances: int | None,
    resume: bool,
):
    client = OpenAI(api_key="none", base_url=api_base)

    existing_ids: set = set()
    if resume and Path(output_file).exists():
        with open(output_file) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    existing_ids.add(obj["instance_id"])
                except Exception:
                    pass
        logger.info(f"Resuming: {len(existing_ids)} already done")

    lite_ids = load_lite_instance_ids()

    logger.info("Loading BM25 13K dataset (streaming)...")
    bm25_ds = load_dataset("princeton-nlp/SWE-bench_bm25_13K", split="test", streaming=True)

    logger.info("Filtering to SWE-bench Lite instances...")
    instances = []
    for item in bm25_ds:
        if item["instance_id"] in lite_ids:
            instances.append(item)
        if len(instances) == len(lite_ids):
            break

    logger.info(f"Found {len(instances)} instances")

    if max_instances is not None:
        instances = instances[:max_instances]

    instances.sort(key=lambda x: x["instance_id"])
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    processed = skipped = 0

    with open(output_file, "a") as f:
        for item in tqdm(instances, desc="Agent inference"):
            instance_id = item["instance_id"]
            if instance_id in existing_ids:
                skipped += 1
                continue

            start = time.time()
            agent_result = run_agent(client, model_name, instance_id, item["text"])
            elapsed = time.time() - start

            record = {
                "instance_id": instance_id,
                "model_name_or_path": model_name,
                "model_patch": agent_result["patch"],
                "agent_turns": agent_result["turns"],
                "agent_tool_calls": agent_result["tool_calls"],
                "files_modified": agent_result["files_modified"],
                "finish_called": agent_result["finish_called"],
            }
            print(json.dumps(record), file=f, flush=True)
            processed += 1

            logger.info(
                f"[{processed}] {instance_id} - turns={agent_result['turns']}, "
                f"modified={agent_result['files_modified']}, "
                f"patch_len={len(agent_result['patch'])}, elapsed={elapsed:.1f}s"
            )

    logger.info(f"Done! Processed={processed}, skipped={skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic GigaChat inference on SWE-bench Lite")
    parser.add_argument("--api-base", default="http://gpu02:8083/v1")
    parser.add_argument("--model-name", default="ai-sage/GigaChat3.1-10B-A1.8B")
    parser.add_argument(
        "--output-file",
        default="predictions/gigachat31_10b__swe-bench_lite__agent.jsonl",
    )
    parser.add_argument("--max-instances", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    args = parser.parse_args()
    main(
        api_base=args.api_base,
        model_name=args.model_name,
        output_file=args.output_file,
        max_instances=args.max_instances,
        resume=args.resume,
    )
