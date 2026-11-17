"""Measure the local analyst without persisting prompts, replies, or provider credentials."""
from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "specs/011-real-key-validation/checklists/questions.yaml"
NUMBER = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
DIACRITIC = re.compile(r"[ăâđêôơưàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ]", re.I)


def candidates(token: str) -> set[float]:
    digits = re.sub(r"[.,]", "", token)
    values = {float(digits)}
    split = max(token.rfind("."), token.rfind(","))
    if split > 0:
        values.add(float(re.sub(r"[.,]", "", token[:split]) + "." + token[split + 1:]))
    return values


def ungrounded_numbers(message: str, values: object) -> list[str]:
    truth = {value for token in NUMBER.findall(json.dumps(values, ensure_ascii=False)) for value in candidates(token)}
    scales = (1_000, 1_000_000, 1_000_000_000)
    display = truth | {value / scale for value in truth for scale in scales} | {round(value / scale) for value in truth for scale in scales}
    return [token for token in NUMBER.findall(message) if not any(
        (value.is_integer() and 0 <= value <= 10)
        or any(abs(value - seen) <= max(0.006, max(abs(value), abs(seen)) * 0.006) for seen in display)
        for value in candidates(token)
    )]


def sse(lines: Iterable[str]) -> Iterator[dict]:
    for line in lines:
        if line.startswith("data:") and (data := line[5:].strip()) != "[DONE]":
            event = json.loads(data)
            if isinstance(event, dict):
                yield event


def measure_answer(lines: Iterable[str], expected: list[str], elapsed: float | None = None, *, start: float | None = None) -> dict:
    start = time.monotonic() if start is None else start
    inputs, outputs, text, failures = {}, {}, [], 0
    for event in sse(lines):
        kind = event.get("type")
        if kind == "tool-input-available":
            inputs[event["toolCallId"]] = event["toolName"]
        elif kind == "tool-output-available":
            outputs[event["toolCallId"]] = event.get("output")
        elif kind == "text-delta":
            text.append(event.get("delta", ""))
        elif kind in {"error", "tool-output-error", "tool-input-error"}:
            failures += 1
    latency = time.monotonic() - start if elapsed is None else elapsed
    answer = "".join(text)
    tools = sorted(set(inputs.values()))
    hit = any(inputs.get(call) in expected for call in outputs)
    vietnamese = bool(DIACRITIC.search(answer))
    unmatched = len(ungrounded_numbers(answer, list(outputs.values())))
    return {"tools": tools, "expected_tool_hit": hit, "vietnamese": vietnamese, "ungrounded_count": unmatched,
            "errors": failures, "seconds": round(latency, 2), "passed": hit and vietnamese and not (unmatched or failures) and latency <= 15}


def run(client: httpx.Client, config: dict, dataset: str, offline: bool) -> dict:
    probe = client.get("/api/chat")
    probe.raise_for_status()
    mode = probe.json()["mode"]
    if mode == "offline" and not offline:
        return {"status": "skipped", "reason": "local analyst has no model configured", "dataset": dataset}
    if mode != "offline" and offline:
        raise ValueError("--offline requires the local analyst to be started without a model")
    questions = config["questions"][:1] if offline else config["questions"]
    reports = {}
    for question in questions:
        message = {"role": "user", "parts": [{"type": "text", "text": question["text"]}]}
        start = time.monotonic()
        with client.stream("POST", "/api/chat", json={"datasetId": dataset, "messages": [message]}) as response:
            response.raise_for_status()
            reports[question["id"]] = measure_answer(response.iter_lines(), question["expected_tools"], start=start)
    response = client.post("/api/story", json={"datasetId": dataset})
    response.raise_for_status()
    story = response.json()
    result = {"status": "passed" if all(row["passed"] for row in reports.values()) else "failed",
              "dataset": dataset, "mode": mode, "model": probe.json().get("model"), "questions": reports,
              "story": {"mode": story["mode"], "engine_steps": sum(step["source"] == "engine" for step in story["steps"]),
                        "steps": len(story["steps"]), "has_question": bool(story.get("question")), "limits": len(story.get("limits", []))}}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dataset")
    parser.add_argument("--url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    config = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    if args.dry_run:
        print(json.dumps({"question_ids": [row["id"] for row in config["questions"]], "number_guard": {
            "grounded": ungrounded_numbers("127 triệu; 60,3 triệu; 3 nhóm", [126840491, 60.3]),
            "ungrounded": ungrounded_numbers("48% trong 2 năm", [126840491, 60.3]),
        }}))
        return
    with httpx.Client(base_url=args.url, timeout=65, trust_env=False) as client:
        results = run(client, config, args.dataset or config["dataset"], args.offline)
    folder = ROOT / "out/llm_smoke"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Saigon")).strftime("%Y%m%dT%H%M%S%z")
    summary = json.dumps(results, ensure_ascii=False, indent=2)
    (folder / f"{stamp}.json").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    if results["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
