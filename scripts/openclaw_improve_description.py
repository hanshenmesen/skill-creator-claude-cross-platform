#!/usr/bin/env python3
"""OpenClaw-compatible description improver.

Replaces improve_description.py's dependency on the `anthropic` SDK by
generating a prompt file that can be executed via OpenClaw's sessions_spawn.

Usage — two-step process:

  Step 1: Generate the improvement prompt
    python -m scripts.openclaw_improve_description generate \
        --eval-results eval_results.json \
        --skill-path /path/to/skill \
        --output-dir /path/to/improve_workspace

  Step 2: After the subagent writes the response, parse it
    python -m scripts.openclaw_improve_description parse \
        --response-file /path/to/improve_workspace/response.md \
        --output /path/to/improved_description.json

Design:
    The original improve_description.py calls anthropic.Anthropic().messages.create()
    with extended thinking. We replicate the same prompt but output it as a file
    that can be fed to any LLM via sessions_spawn. The response parsing extracts
    the <new_description> tag the same way the original does.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.utils import parse_skill_md


def build_improvement_prompt(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict] | None = None,
    test_results: dict | None = None,
) -> str:
    """Build the exact same prompt that improve_description.py uses.

    Returns the prompt string ready to be sent to any LLM.
    """
    failed_triggers = [
        r for r in eval_results["results"]
        if r["should_trigger"] and not r["pass"]
    ]
    false_triggers = [
        r for r in eval_results["results"]
        if not r["should_trigger"] and not r["pass"]
    ]

    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    if test_results:
        test_score = f"{test_results['summary']['passed']}/{test_results['summary']['total']}"
        scores_summary = f"Train: {train_score}, Test: {test_score}"
    else:
        scores_summary = f"Train: {train_score}"

    prompt = f"""You are optimizing a skill description for a skill called "{skill_name}". A "skill" is sort of like a prompt, but with progressive disclosure -- there's a title and description that the AI sees when deciding whether to use the skill, and then if it does use the skill, it reads the .md file which has lots more details and potentially links to other resources in the skill folder like helper files and scripts and additional documentation or examples.

The description appears in the AI's "available_skills" list. When a user sends a query, the AI decides whether to invoke the skill based solely on the title and on this description. Your goal is to write a description that triggers for relevant queries, and doesn't trigger for irrelevant ones.

Here's the current description:
<current_description>
"{current_description}"
</current_description>

Current scores ({scores_summary}):
<scores_summary>
"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            test_s = f"{h.get('test_passed', '?')}/{h.get('test_total', '?')}" if h.get('test_passed') is not None else None
            score_str = f"train={train_s}" + (f", test={test_s}" if test_s else "")
            prompt += f'<attempt {score_str}>\n'
            prompt += f'Description: "{h["description"]}"\n'
            if "results" in h:
                prompt += "Train results:\n"
                for r in h["results"]:
                    status = "PASS" if r["pass"] else "FAIL"
                    prompt += f'  [{status}] "{r["query"][:80]}" (triggered {r["triggers"]}/{r["runs"]})\n'
            if h.get("note"):
                prompt += f'Note: {h["note"]}\n'
            prompt += "</attempt>\n\n"

    prompt += f"""</scores_summary>

Skill content (for context on what the skill does):
<skill_content>
{skill_content}
</skill_content>

Based on the failures, write a new and improved description that is more likely to trigger correctly. When I say "based on the failures", it's a bit of a tricky line to walk because we don't want to overfit to the specific cases you're seeing. So what I DON'T want you to do is produce an ever-expanding list of specific queries that this skill should or shouldn't trigger for. Instead, try to generalize from the failures to broader categories of user intent and situations where this skill would be useful or not useful. The reason for this is twofold:

1. Avoid overfitting
2. The list might get loooong and it's injected into ALL queries and there might be a lot of skills, so we don't want to blow too much space on any given description.

Concretely, your description should not be more than about 100-200 words, even if that comes at the cost of accuracy.

Here are some tips that we've found to work well in writing these descriptions:
- The skill should be phrased in the imperative -- "Use this skill for" rather than "this skill does"
- The skill description should focus on the user's intent, what they are trying to achieve, vs. the implementation details of how the skill works.
- The description competes with other skills for the AI's attention — make it distinctive and immediately recognizable.
- If you're getting lots of failures after repeated attempts, change things up. Try different sentence structures or wordings.

I'd encourage you to be creative and mix up the style in different iterations since you'll have multiple opportunities to try different approaches and we'll just grab the highest-scoring one at the end. 

Please respond with only the new description text in <new_description> tags, nothing else."""

    return prompt


def parse_response(response_text: str) -> str:
    """Extract the new description from a response containing <new_description> tags."""
    match = re.search(r"<new_description>(.*?)</new_description>", response_text, re.DOTALL)
    if match:
        return match.group(1).strip().strip('"')
    # Fallback: return the whole text stripped
    return response_text.strip().strip('"')


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw-compatible description improver"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: generate — build the prompt
    gen = subparsers.add_parser("generate", help="Generate improvement prompt for subagent")
    gen.add_argument("--eval-results", required=True, help="Path to eval results JSON")
    gen.add_argument("--skill-path", required=True, help="Path to skill directory")
    gen.add_argument("--history", default=None, help="Path to history JSON (previous attempts)")
    gen.add_argument("--output-dir", required=True, help="Directory to write prompt and metadata")

    # Subcommand: parse — extract description from subagent response
    parse_cmd = subparsers.add_parser("parse", help="Parse subagent response for new description")
    parse_cmd.add_argument("--response-file", required=True, help="Path to subagent response text file")
    parse_cmd.add_argument("--output", default=None, help="Path to write result JSON (default: stdout)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        skill_path = Path(args.skill_path)
        if not (skill_path / "SKILL.md").exists():
            print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
            sys.exit(1)

        eval_results = json.loads(Path(args.eval_results).read_text())
        history = []
        if args.history:
            history = json.loads(Path(args.history).read_text())

        name, _, content = parse_skill_md(skill_path)
        current_description = eval_results.get("description", "")

        prompt = build_improvement_prompt(
            skill_name=name,
            skill_content=content,
            current_description=current_description,
            eval_results=eval_results,
            history=history,
        )

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write the prompt
        prompt_path = output_dir / "improve_prompt.md"
        prompt_path.write_text(prompt)

        # Write metadata
        meta = {
            "skill_name": name,
            "current_description": current_description,
            "eval_summary": eval_results.get("summary", {}),
            "prompt_path": str(prompt_path),
            "response_path": str(output_dir / "response.md"),
        }
        (output_dir / "improve_meta.json").write_text(json.dumps(meta, indent=2))

        print(f"Prompt written to: {prompt_path}", file=sys.stderr)
        print(f"\nNext steps:", file=sys.stderr)
        print(f"  1. Spawn a subagent with this prompt (read the prompt file)", file=sys.stderr)
        print(f"  2. Save the subagent's response to: {output_dir / 'response.md'}", file=sys.stderr)
        print(f"  3. Run: python -m scripts.openclaw_improve_description parse \\", file=sys.stderr)
        print(f"       --response-file {output_dir / 'response.md'}", file=sys.stderr)

    elif args.command == "parse":
        response_text = Path(args.response_file).read_text()
        new_description = parse_response(response_text)

        result = {
            "description": new_description,
            "char_count": len(new_description),
            "over_limit": len(new_description) > 1024,
        }

        if result["over_limit"]:
            print(f"WARNING: Description is {result['char_count']} chars (limit: 1024)", file=sys.stderr)

        json_output = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(json_output)
            print(f"Result written to: {args.output}", file=sys.stderr)
        else:
            print(json_output)

        print(f"\nNew description ({result['char_count']} chars):", file=sys.stderr)
        print(f"  {new_description[:200]}{'...' if len(new_description) > 200 else ''}", file=sys.stderr)


if __name__ == "__main__":
    main()
