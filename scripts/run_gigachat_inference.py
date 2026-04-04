#!/usr/bin/env python3
"""
Custom inference script for GigaChat 3.1 10B on SWE-bench Lite.
Uses BM25 13K dataset for code context and calls a custom OpenAI-compatible endpoint.

v4: improved system prompt (explicit line number anchoring) + modified DEVSYSTEM in chat_template.
    CoT was removed - it triggered "euclidean function" hallucinations on 57% of instances.
"""

import json
import os
import re
import time
import logging
import argparse
from pathlib import Path

from datasets import load_dataset
from openai import OpenAI
from tqdm.auto import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PATCH_PATTERN = re.compile(
    r"(?:diff[\w\_\.\ \/\-]+\n)?\-\-\-\s+[ab]\/(?:.*?)\n\+\+\+\s+[ab]\/(?:.*?)(?=diff\ |\-\-\-\ [ab]\/|\Z)",
    re.DOTALL,
)

# System prompt: highest-level instructions for the model.
# The DEVSYSTEM in the chat template already embeds diff format rules,
# this system prompt reinforces them at the `system` role level.
SYSTEM_PROMPT = (
    "You are an expert software engineer. Your task is to fix GitHub issues by generating unified diff patches.\n\n"
    "The code context shows files with LINE NUMBERS (e.g. '42 def foo():'). "
    "Use EXACTLY those line numbers in the @@ header. Copy context lines VERBATIM (without the number prefix).\n\n"
    "PROCESS:\n"
    "1. Read the issue and identify what is broken\n"
    "2. Find the exact lines in the file context that need to change\n"
    "3. Write a brief analysis (1-2 sentences)\n"
    "4. Generate the unified diff patch\n\n"
    "PATCH FORMAT:\n"
    "  diff --git a/FILE b/FILE\n"
    "  --- a/FILE\n"
    "  +++ b/FILE\n"
    "  @@ -START,COUNT +START,COUNT @@\n"
    "   <context line copied verbatim from file>\n"
    "  -<removed line copied verbatim from file>\n"
    "  +<added line with the fix>\n"
    "  Wrap in <patch>...</patch>\n\n"
    "EXAMPLE:\n"
    "[start of src/utils.py]\n"
    "10 def greet(name):\n"
    "11     msg = 'Hello ' + nam\n"
    "12     return msg\n"
    "[end of src/utils.py]\n\n"
    "Issue: NameError - 'nam' should be 'name'\n\n"
    "Analysis: The typo is on line 11 in src/utils.py: 'nam' should be 'name'.\n\n"
    "<patch>\n"
    "diff --git a/src/utils.py b/src/utils.py\n"
    "--- a/src/utils.py\n"
    "+++ b/src/utils.py\n"
    "@@ -10,3 +10,3 @@\n"
    " def greet(name):\n"
    "-    msg = 'Hello ' + nam\n"
    "+    msg = 'Hello ' + name\n"
    "     return msg\n"
    "</patch>"
)



def extract_patch(text: str) -> str:
    """Extract unified diff patch from model output."""
    candidate = ""

    # Try to find patch between <patch> tags (with or without closing tag)
    tag_match = re.search(r"<patch>(.*?)(?:</patch>|$)", text, re.DOTALL)
    if tag_match:
        candidate = tag_match.group(1).strip()

    # Try to find raw diff blocks
    if not candidate:
        patches = PATCH_PATTERN.findall(text)
        if patches:
            candidate = "".join(patches).strip()

    # Return full text if it looks like a patch
    if not candidate:
        stripped = text.strip()
        if stripped.startswith("diff ") or stripped.startswith("---"):
            candidate = stripped

    # Always ensure patch ends with newline (required by patch/git apply)
    if candidate and not candidate.endswith("\n"):
        candidate += "\n"

    return candidate


def call_model(client: OpenAI, model_name: str, text: str, max_tokens: int = 4096) -> str:
    """Call the OpenAI-compatible API with the given prompt."""
    # First line is the BM25 dataset preamble - strip it, we have our own system prompt
    lines = text.split("\n", 1)
    user_content = lines[1] if len(lines) == 2 else text

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"API error: {e}")
        return ""


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
    max_tokens: int,
    max_instances: int | None,
    resume: bool,
):
    client = OpenAI(api_key="none", base_url=api_base)

    # Load already processed IDs for resume
    existing_ids: set = set()
    if resume and Path(output_file).exists():
        with open(output_file) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    existing_ids.add(obj["instance_id"])
                except Exception:
                    pass
        logger.info(f"Resuming: found {len(existing_ids)} already processed instances")

    # Get Lite instance IDs to filter BM25 dataset
    lite_ids = load_lite_instance_ids()

    logger.info("Loading BM25 13K dataset (streaming)...")
    bm25_ds = load_dataset("princeton-nlp/SWE-bench_bm25_13K", split="test", streaming=True)

    # Filter and collect matching instances
    logger.info("Filtering BM25 instances to SWE-bench Lite...")
    instances = []
    for item in bm25_ds:
        if item["instance_id"] in lite_ids:
            instances.append(item)
        if len(instances) == len(lite_ids):
            break

    logger.info(f"Found {len(instances)} matching instances in BM25 dataset")

    if max_instances is not None:
        instances = instances[:max_instances]
        logger.info(f"Limited to {max_instances} instances")

    # Sort by instance_id for reproducibility
    instances.sort(key=lambda x: x["instance_id"])

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0

    with open(output_file, "a") as f:
        for item in tqdm(instances, desc="Running inference"):
            instance_id = item["instance_id"]

            if instance_id in existing_ids:
                skipped += 1
                continue

            text = item["text"]
            start_time = time.time()
            raw_output = call_model(client, model_name, text, max_tokens=max_tokens)
            elapsed = time.time() - start_time

            patch = extract_patch(raw_output)

            result = {
                "instance_id": instance_id,
                "model_name_or_path": model_name,
                "model_patch": patch,
                "full_output": raw_output,
            }
            print(json.dumps(result), file=f, flush=True)
            processed += 1

            logger.info(
                f"[{processed}/{len(instances) - skipped}] {instance_id} - "
                f"patch_len={len(patch)}, elapsed={elapsed:.1f}s"
            )

    logger.info(
        f"Done! Processed {processed} instances, skipped {skipped} (already done). "
        f"Results saved to {output_file}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GigaChat inference on SWE-bench Lite")
    parser.add_argument(
        "--api-base",
        type=str,
        default="http://gpu02:8083/v1",
        help="OpenAI-compatible API base URL",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="ai-sage/GigaChat3.1-10B-A1.8B",
        help="Model name to use",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="predictions/gigachat31_10b__swe-bench_lite__test.jsonl",
        help="Path to output JSONL file",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum tokens to generate per instance",
    )
    parser.add_argument(
        "--max-instances",
        type=int,
        default=None,
        help="Limit number of instances to process (for testing)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from existing output file",
    )
    args = parser.parse_args()
    main(
        api_base=args.api_base,
        model_name=args.model_name,
        output_file=args.output_file,
        max_tokens=args.max_tokens,
        max_instances=args.max_instances,
        resume=args.resume,
    )
