"""Thin Anthropic wrapper: deterministic calls (temperature=0), bounded retries,
robust JSON extraction. All CGM model calls go through call_llm."""
import json
import re
import time

import anthropic

MAX_RETRIES = 3
RETRY_SLEEP_S = 5


def call_llm(model, system, user, max_tokens=2000):
    client = anthropic.Anthropic()
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            if resp.stop_reason == "max_tokens":
                raise RuntimeError(
                    f"LLM output truncated at max_tokens={max_tokens}"
                )
            return resp.content[0].text
        except Exception as err:  # noqa: BLE001 - retry then surface
            last_err = err
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_SLEEP_S * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_err}")


def extract_json(text):
    candidates = []
    # Fenced ```json ... ``` block: capture the WHOLE inner body greedily.
    # (The previous \{.*?\} was non-greedy and stopped at the first nested
    # closing brace, mangling any object containing arrays/sub-objects.)
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    # Greedy outermost braces, then the raw text as a last resort.
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    candidates.append(text.strip())
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no parseable JSON object in LLM output: {text[:200]!r}")
