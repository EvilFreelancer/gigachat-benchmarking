# GigaChat 3.1 10B - SWE-bench Lite Evaluation

**Model:** `ai-sage/GigaChat3.1-10B-A1.8B` (10B total params, 1.8B active, MoE architecture)
**Benchmark:** [SWE-bench Lite](https://github.com/SWE-bench/SWE-bench) - 300 real-world GitHub issues
**Method:** Single-pass prompting, no agent loop
**Date:** April 4, 2026

---

## Final Results

Two runs were conducted to investigate and partially fix a diff format problem.

### Run 2 - Few-shot Prompt (final)

| Metric | Value |
|---|---|
| **Score (resolved, tests passed)** | **0 / 300 (0.00%)** |
| Patch applied successfully | 24 / 300 (8.00%) |
| Patch apply error | 276 / 300 (92.00%) |
| Valid `@@ -N,M +N,M @@` header | 297 / 300 (99.00%) |
| Empty patch | 0 / 300 (0.00%) |
| Inference time | 101.9 min total, median 9.7s/instance |

**Predictions:** `results/gigachat31_10b__swe-bench_lite__fewshot.jsonl`
**Evaluation report:** `results/ai-sage__GigaChat3.1-10B-A1.8B.gigachat31-10b-fewshot2.json`

### Run 1 - Baseline

| Metric | Value |
|---|---|
| **Score (resolved, tests passed)** | **0 / 300 (0.00%)** |
| Patch applied successfully | 14 / 300 (4.67%) |
| Patch apply error | 286 / 300 (95.33%) |
| Empty patch | 0 / 300 (0.00%) |
| Inference time | 81.7 min total, median 7.0s/instance |

**Predictions:** `results/gigachat31_10b__swe-bench_lite__test.jsonl`
**Evaluation report:** `results/ai-sage__GigaChat3.1-10B-A1.8B.gigachat31-10b.json`

### Comparison

| Metric | Run 1 (baseline) | Run 2 (few-shot) | Delta |
|---|---|---|---|
| Score | 0% | 0% | - |
| Patch applied | 14 (4.7%) | 24 (8.0%) | +10 (+71%) |
| Patch error | 286 (95.3%) | 276 (92.0%) | -10 |
| Valid `@@` header | ~0% | 99% | +99pp |

### Why Score Is 0%

The model's failure has two independent layers:

**Layer 1 - Format (fixed by few-shot):** Without a concrete example, the model writes
human-readable descriptions in hunk headers instead of the required numeric format:

```diff
# Generated (invalid - git apply rejects this):
@@ at the end of the file, after the _operators dictionary

# Required (valid):
@@ -242,7 +242,7 @@
```

A single few-shot example in the system prompt fixed this: valid headers went from ~0% to 99%.

**Layer 2 - Semantics (not fixable by prompting):** Even with correct format, the model
targets the wrong functions and invents context lines that do not match the actual file.

Example - `astropy__astropy-12907`:
- Gold patch: 1-line change in `_cstack()` at line 242: `= 1` → `= right`
- Model patch: targets `_separable()` at line 290 with invented context that does not exist in the file

This requires an agent loop (read file, locate the bug, write the fix) rather than single-pass inference.

---

## Tool Calling Verification

Verified before running the benchmark:

```bash
curl http://gpu02:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ai-sage/GigaChat3.1-10B-A1.8B",
    "temperature": 0,
    "messages": [{"role": "user", "content": "What is the weather in Moscow?"}],
    "tools": [{"type": "function", "function": {
      "name": "get_weather",
      "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
    }}]
  }'
```

Result: `finish_reason: "tool_calls"`, correctly calls `get_weather({"city": "Москва"})`. Tool calling works.

---

## Comparison with Known Baselines (SWE-bench Lite)

| Model | Approach | Score |
|---|---|---|
| Claude 3.5 Sonnet | SWE-agent (agentic + tools) | ~49% |
| GPT-4o | SWE-agent (agentic + tools) | ~30% |
| GPT-4 | Single-pass prompting | ~4-5% |
| **GigaChat 3.1 10B** | **Single-pass prompting** | **0%** |

The agentic approach (tool calling loop) outperforms single-pass by 5-10x across all models.
GigaChat 3.1 tool calling is functional - an agentic setup is the natural next step.

---

## Repository Structure

```
gigachat-bench/
  README.md
  requirements.txt
  results/
    gigachat31_10b__swe-bench_lite__test.jsonl          - Run 1 predictions (300 instances)
    gigachat31_10b__swe-bench_lite__fewshot.jsonl       - Run 2 predictions (300 instances)
    ai-sage__GigaChat3.1-10B-A1.8B.gigachat31-10b.json            - Run 1 evaluation report
    ai-sage__GigaChat3.1-10B-A1.8B.gigachat31-10b-fewshot2.json   - Run 2 evaluation report
  scripts/
    run_gigachat_inference.py   - inference script (use this)
    run_evaluation.sh           - evaluation wrapper
  patches/
    run_api_openai_compat.patch - optional patch to swebench/inference/run_api.py
```

---

## Reproduction Guide

### Prerequisites

**Inference machine:** GPU server, 1x GPU (tested on A100/H100), vLLM serving the model.

**Evaluation machine:** x86_64, 16+ GB RAM, 120+ GB free disk, Docker.

Inference and evaluation can run on separate machines.

### 1. Start the Model Server

```yaml
# docker-compose.yaml
gigachat31-10b:
  image: vllm/vllm-openai:v0.19.0
  command: >
    serve ai-sage/GigaChat3.1-10B-A1.8B
    --served-model-name ai-sage/GigaChat3.1-10B-A1.8B
    --trust-remote-code
    --dtype auto
    --gpu-memory-utilization 0.95
    --max-num-seqs 1
    --max-model-len 60000
    --max-num-batched-tokens 60000
    --kv-cache-dtype fp8
    --no-enable-prefix-caching
    --enable-auto-tool-choice
    --tool-call-parser gigachat3
  ports:
    - 8083:8000
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ["1"]
            capabilities: [gpu]
```

```bash
docker compose up -d
curl http://gpu02:8083/v1/models  # verify
```

### 2. Clone SWE-bench

```bash
git clone https://github.com/SWE-bench/SWE-bench.git
cd SWE-bench
```

### 3. Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate

# Do NOT use pip install -e ".[inference]" - it requires flash_attn + CUDA build tools
pip install -e . openai datasets tenacity tqdm python-dotenv
```

### 4. (Optional) Patch run_api.py for Custom Endpoints

Skip this if you use our custom script (recommended).

Apply `patches/run_api_openai_compat.patch` to add `OPENAI_API_BASE` support to the built-in
`swebench/inference/run_api.py`, which only supports GPT/Claude by default:

```bash
patch -p1 < /path/to/gigachat-bench/patches/run_api_openai_compat.patch
```

After patching:

```bash
OPENAI_API_BASE=http://gpu02:8083/v1 \
OPENAI_API_KEY=none \
python -m swebench.inference.run_api \
  --dataset_name_or_path princeton-nlp/SWE-bench_bm25_13K \
  --model_name_or_path ai-sage/GigaChat3.1-10B-A1.8B \
  --output_dir predictions/
```

### 5. Run Inference

Copy `scripts/run_gigachat_inference.py` to the SWE-bench root, then:

```bash
# Full run - all 300 SWE-bench Lite instances (~100 min)
python3 run_gigachat_inference.py \
  --api-base http://gpu02:8083/v1 \
  --model-name ai-sage/GigaChat3.1-10B-A1.8B \
  --output-file predictions/gigachat31_10b__swe-bench_lite__fewshot.jsonl \
  --max-tokens 4096

# Quick test - 5 instances
python3 run_gigachat_inference.py --max-instances 5
```

**All flags:**

| Flag | Default | Description |
|---|---|---|
| `--api-base` | `http://gpu02:8083/v1` | OpenAI-compatible API base URL |
| `--model-name` | `ai-sage/GigaChat3.1-10B-A1.8B` | Model name in vLLM |
| `--output-file` | `predictions/gigachat31_10b__swe-bench_lite__fewshot.jsonl` | Output JSONL path |
| `--max-tokens` | `4096` | Max tokens per generation |
| `--max-instances` | None | Limit instances (for testing) |
| `--resume` | True | Skip already-done instances |

**What the script does:**
1. Loads 300 instance IDs from `princeton-nlp/SWE-bench_Lite`
2. Streams `princeton-nlp/SWE-bench_bm25_13K` - code context pre-retrieved via BM25 (top 13K tokens)
3. Sends `system prompt + issue + code` to the model (temperature=0)
4. Extracts the diff patch from `<patch>...</patch>` tags or raw diff blocks
5. Ensures patch ends with `\n` (required by `git apply`)
6. Writes JSONL output, one record per line

**Output JSONL format:**
```json
{
  "instance_id": "django__django-12907",
  "model_name_or_path": "ai-sage/GigaChat3.1-10B-A1.8B",
  "model_patch": "diff --git a/...\n--- a/...\n+++ b/...\n@@ -N,M +N,M @@\n ...",
  "full_output": "<patch>...</patch>"
}
```

### 6. Run Evaluation

Requires Docker and 120+ GB free disk.

```bash
# Verify harness works first (gold patch, 1 instance, ~2 min)
python3 -m swebench.harness.run_evaluation \
  --predictions_path gold \
  --max_workers 1 \
  --instance_ids astropy__astropy-12907 \
  --run_id validate-gold
# Expected: resolved_instances: 1

# Full evaluation - all 300 instances (~90 min with 4 workers)
python3 -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite \
  --predictions_path predictions/gigachat31_10b__swe-bench_lite__fewshot.jsonl \
  --max_workers 4 \
  --run_id gigachat31-10b-fewshot \
  --cache_level env
```

**Key flags:**

| Flag | Value | Notes |
|---|---|---|
| `--max_workers` | 4 | Use `min(0.75 * nproc, 24)` |
| `--cache_level env` | recommended | Caches env images (~30-50 GB), discards per-instance images |
| `--cache_level none` | minimal disk | Slowest, rebuilds everything |
| `--cache_level instance` | fastest | Needs ~300+ GB disk |

**Note on urllib3 warning at exit:** The harness prints `ValueError: I/O operation on closed file`
when shutting down Docker connections. This is harmless - the report is written before this error appears.

**Output:**
- `<model>.<run_id>.json` - summary with resolved/applied/error counts
- `logs/run_evaluation/<run_id>/` - per-instance `patch.diff` + `run_instance.log`

---

## System Prompt Details

### Run 2 (current) - with few-shot example

```
You are an expert software engineer. Fix GitHub issues by generating unified diff patches.

RULES:
1. The code blocks show line numbers - use them for the @@ header
2. @@ header format is EXACTLY: @@ -OLD_LINE,OLD_COUNT +NEW_LINE,NEW_COUNT @@
3. Context lines (unchanged) start with a single space
4. Removed lines start with -
5. Added lines start with +
6. Wrap the entire patch in <patch>...</patch>

EXAMPLE:
[start of utils.py]
10 def greet(name):
11     msg = 'Hello ' + nam
12     return msg
[end of utils.py]

Correct patch:
<patch>
diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -10,3 +10,3 @@
 def greet(name):
-    msg = 'Hello ' + nam
+    msg = 'Hello ' + name
     return msg
</patch>
```

### Run 1 (baseline) - no example

```
You are an expert software engineer tasked with resolving GitHub issues.
Generate a unified diff patch in the EXACT standard git diff format.
CRITICAL: @@ line format is EXACTLY: @@ -LINE,COUNT +LINE,COUNT @@ (numeric only!)
Wrap the entire patch in <patch> and </patch> tags.
```

Despite explicitly stating the format, the baseline prompt produced nearly 0% valid `@@` headers.
The model needs to see a concrete example, not just a description.

---

## Recommendations

### 1. Agentic approach (highest impact)

GigaChat 3.1 tool calling is verified working. Implement an agent loop:
- `read_file(path)` - read the file content at the right commit
- `search_code(query)` - find relevant code locations
- `edit_file(path, old, new)` - make the actual change
- `run_tests()` - verify the fix

This is how SWE-agent achieves 30-49% on this benchmark.

### 2. Oracle retrieval (upper bound estimate)

Replace the BM25 dataset with oracle-retrieved files (exact files touched by the gold patch).
This gives the model the correct files to edit and estimates the ceiling of single-pass performance.

### 3. Fine-tuning on diff format

Use [SWE-smith](https://github.com/SWE-bench/SWE-smith) to generate training data with correct
unified diff format. Even a small fine-tuning run should stabilize the output format.

---

## Dependencies

```
datasets>=2.14.0
openai>=1.3.0
tqdm>=4.65.0
tenacity>=8.2.0
python-dotenv>=1.0.0
docker  # evaluation harness only
```

```bash
pip install -r requirements.txt
```
