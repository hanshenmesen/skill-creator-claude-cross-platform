#!/usr/bin/env python3
"""OpenClaw-compatible trigger evaluation for skill descriptions.

Replaces run_eval.py's dependency on `claude -p` by writing a test script
that can be executed via OpenClaw's sessions_spawn. The script generates
a batch of test prompts and a shell coordinator that writes results to JSON.

Usage:
    python -m scripts.openclaw_run_eval \
        --eval-set evals/trigger_eval.json \
        --skill-path /path/to/skill \
        --output /path/to/eval_results.json

The actual trigger testing is done by spawning subagents through OpenClaw.
This script prepares the inputs and aggregates the outputs.

Design:
    Instead of calling `claude -p`, we simulate the trigger decision by
    spawning a subagent with the same available_skills list that OpenClaw
    uses, and asking it: "Given this query, would you use this skill?"
    The subagent writes a simple JSON verdict file.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from scripts.utils import parse_skill_md


def generate_trigger_test_prompt(
    query: str,
    skill_name: str,
    skill_description: str,
    test_id: str,
    output_path: str,
) -> str:
    """Generate a prompt that tests whether a skill would be triggered.

    The subagent is asked to role-play as a skill router: given a user query
    and a list of available skills (containing only the target skill),
    decide whether to invoke it.
    """
    return f"""You are a skill routing evaluator. Your ONLY job is to decide whether a given skill should be triggered for a user query.

## Available Skill

```
name: {skill_name}
description: {skill_description}
```

## User Query

"{query}"

## Your Task

Decide: if you were an AI assistant and this skill was available, would you read/invoke this skill to help answer the user's query?

Think about it carefully:
- Does the query's intent match what this skill does?
- Would this skill genuinely help with the query?
- Or can you handle it without any skill?

## Output

Write your verdict as a JSON file to: {output_path}

The JSON must be exactly:
```json
{{
    "test_id": "{test_id}",
    "query": "<the query>",
    "triggered": true or false,
    "reasoning": "brief explanation"
}}
```

Write ONLY the JSON file. No other output needed.
IMPORTANT: `triggered` should be `true` if you WOULD invoke/read this skill, `false` if you would NOT."""


def prepare_eval_batch(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    output_dir: Path,
    runs_per_query: int = 1,
) -> list[dict]:
    """Prepare a batch of trigger test tasks for subagent execution.

    Returns a list of task dicts, each containing:
    - task_id: unique identifier
    - query: the user query
    - should_trigger: expected result
    - prompt: the subagent prompt
    - output_path: where the verdict JSON should be written
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    for item in eval_set:
        for run_idx in range(runs_per_query):
            task_id = f"{uuid.uuid4().hex[:8]}"
            verdict_path = output_dir / f"verdict_{task_id}.json"

            prompt = generate_trigger_test_prompt(
                query=item["query"],
                skill_name=skill_name,
                skill_description=description,
                test_id=task_id,
                output_path=str(verdict_path),
            )

            tasks.append({
                "task_id": task_id,
                "query": item["query"],
                "should_trigger": item["should_trigger"],
                "run_index": run_idx,
                "prompt": prompt,
                "output_path": str(verdict_path),
            })

    return tasks


def aggregate_verdicts(
    tasks: list[dict],
    trigger_threshold: float = 0.5,
) -> dict:
    """Read verdict files and aggregate into eval results.

    Same output format as run_eval.py's run_eval() function.
    """
    # Group by query
    query_data: dict[str, dict] = {}
    for task in tasks:
        q = task["query"]
        if q not in query_data:
            query_data[q] = {
                "should_trigger": task["should_trigger"],
                "triggers": [],
            }

        verdict_path = Path(task["output_path"])
        triggered = False
        if verdict_path.exists():
            try:
                verdict = json.loads(verdict_path.read_text())
                triggered = bool(verdict.get("triggered", False))
            except (json.JSONDecodeError, OSError):
                pass
        query_data[q]["triggers"].append(triggered)

    results = []
    for query, data in query_data.items():
        triggers = data["triggers"]
        trigger_count = sum(triggers)
        total_runs = len(triggers)
        trigger_rate = trigger_count / total_runs if total_runs > 0 else 0.0

        should_trigger = data["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold

        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": trigger_count,
            "runs": total_runs,
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Prepare trigger evaluation tasks for OpenClaw subagents"
    )
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--output-dir", default=None, help="Directory for verdict files")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")

    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: prepare — generate task prompts
    prep = subparsers.add_parser("prepare", help="Generate subagent task prompts")
    prep.add_argument("--tasks-output", required=True, help="Path to write tasks JSON")

    # Subcommand: aggregate — read verdicts and produce results
    agg = subparsers.add_parser("aggregate", help="Aggregate verdict files into results")
    agg.add_argument("--tasks-input", required=True, help="Path to tasks JSON from prepare step")
    agg.add_argument("--results-output", default=None, help="Path to write results JSON (default: stdout)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    output_dir = Path(args.output_dir) if args.output_dir else Path("trigger_verdicts")

    if args.command == "prepare":
        tasks = prepare_eval_batch(
            eval_set=eval_set,
            skill_name=name,
            description=description,
            output_dir=output_dir,
            runs_per_query=args.runs_per_query,
        )

        tasks_path = Path(args.tasks_output)
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text(json.dumps({
            "skill_name": name,
            "description": description,
            "tasks": tasks,
        }, indent=2))

        print(f"Prepared {len(tasks)} trigger test tasks", file=sys.stderr)
        print(f"Tasks written to: {tasks_path}", file=sys.stderr)
        print(f"Verdict files will be at: {output_dir}/", file=sys.stderr)
        print(f"\nNext: spawn a subagent for each task's 'prompt' field,", file=sys.stderr)
        print(f"then run: python -m scripts.openclaw_run_eval aggregate ...", file=sys.stderr)

    elif args.command == "aggregate":
        tasks_data = json.loads(Path(args.tasks_input).read_text())
        tasks = tasks_data["tasks"]

        output = aggregate_verdicts(
            tasks=tasks,
            trigger_threshold=args.trigger_threshold,
        )
        output["skill_name"] = tasks_data["skill_name"]
        output["description"] = tasks_data["description"]

        json_output = json.dumps(output, indent=2)
        if args.results_output:
            Path(args.results_output).write_text(json_output)
            print(f"Results written to: {args.results_output}", file=sys.stderr)
        else:
            print(json_output)

        summary = output["summary"]
        print(f"\nResults: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)


if __name__ == "__main__":
    main()
