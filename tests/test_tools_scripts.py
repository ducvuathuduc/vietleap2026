import json
import subprocess
import sys
from pathlib import Path


def test_llm_smoke_dry_run(kit_root):
    script = kit_root / "tools/llm_smoke.py"
    result = subprocess.run([sys.executable, str(script), "--dry-run"], cwd=kit_root, capture_output=True, text=True, check=True)
    plan = json.loads(result.stdout)
    assert plan["question_ids"] == ["q1-insight", "q2-segment", "q3-whatif", "q4-sql", "q5-pipeline"]
    assert plan["number_guard"] == {"grounded": [], "ungrounded": ["48"]}


def test_chat_stream_records_tool_outputs_without_transcripts():
    import runpy

    script = Path(__file__).resolve().parents[1] / "tools/llm_smoke.py"
    measure = runpy.run_path(str(script))["measure_answer"]
    events = [
        {"type": "tool-input-available", "toolName": "getInsights", "toolCallId": "x"},
        {"type": "tool-output-available", "toolCallId": "x", "output": {"value": 126840491}},
        {"type": "text-delta", "delta": "Giá khoảng 127 triệu đồng."},
    ]
    result = measure(("data: " + json.dumps(event) for event in events), ["getInsights"], elapsed=1)
    assert result["passed"] and result["tools"] == ["getInsights"]
    assert "triệu" not in json.dumps(result, ensure_ascii=False)


def test_python_offline_agent_answers_vietnamese(tmp_path):
    import pandas as pd
    from api.agent.runner import run_fallback
    from vlkit.pipeline import run
    from vlkit.tools import Context

    data = tmp_path / "data.csv"
    pd.DataFrame({"metric": list(range(40)), "group": ["A"] * 20 + ["B"] * 20}).to_csv(data, index=False)
    results = run(data, out_root=tmp_path, name="agent", target="metric", reports=False)
    context = Context(pd.read_parquet(tmp_path / "agent/clean.parquet"), results)
    events = list(run_fallback(context, "Insight hàng đầu là gì?"))
    assert events[-1]["type"] == "done" and "Bằng chứng" in events[-1]["text"]
    assert any(event["type"] == "verification" for event in events)


def test_demo_tools_dry_run(kit_root):
    def run_script(name):
        result = subprocess.run([sys.executable, str(kit_root / f"tools/{name}.py"), "--dry-run"],
                                cwd=kit_root, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    routes = run_script("screenshots")
    assert len(routes) == 14 and routes["/report"].endswith(".png")
    storyboard = run_script("record_demo")
    assert storyboard["duration"] == 90
    assert [step["at"] for step in storyboard["steps"]] == [0, 10, 35, 55, 70, 85]
