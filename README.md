# skill-creator-claude (cross-platform)

[中文版说明](./README_CN.md)

> Anthropic’s skill-creation methodology — runnable on **Claude Code**, **OpenClaw**, and other agent platforms, with minimal upstream drift.

This repository is a faithful derivative of the Claude Code **skill-creator** plugin: the same loop (draft → eval → benchmark → iterate → description tuning → package). Claude Code–only pieces (`claude -p`, `present_files`, etc.) are either removed or documented with fallbacks. For **OpenClaw**, dedicated scripts replace the `claude -p` workflow so trigger testing and description improvement can run end-to-end via `sessions_spawn`.

---

## Origin & attribution

- **Original author**: Anthropic  
- **License**: Apache 2.0 (same license family as the upstream skill-creator; retain notices when redistributing).  
- **Upstream path (Claude Code plugin)**:  
  `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator`  
- **Full upstream experience**: [Claude Code](https://claude.ai/code) — where every feature is available out of the box.

Design and methodology credit belong to Anthropic; this repo is a derivative work.

---

## Philosophy

- **Minimal surface change**: Keep methodology, scripts layout, and agent prompts aligned with upstream unless a hard dependency blocks portability.  
- **Clear attribution**: Preserve upstream intent and license obligations.  
- **OpenClaw as a first-class path**: Not “generic only” — the repo ships `openclaw_run_eval.py` and `openclaw_improve_description.py` plus `SKILL.md` **Platform Notes** so OpenClaw users are not stuck without `claude -p`.  
- **Gateway, not a full product**: For the complete Claude Code–integrated experience, use Claude Code; this tree is for running the same ideas elsewhere.

---

## What differs from upstream

### `SKILL.md` (conceptual edits)

Roughly the same four themes described in earlier releases: modification notice at the top, packaging without `present_files`, unified **Platform Notes**, and guidance when `run_loop.py` / `claude -p` are unavailable. The file now also documents **OpenClaw** (`sessions_spawn`, `--static` eval viewer, skill install paths, and the OpenClaw replacement scripts).

### New / platform-specific scripts

| Script | Role |
|--------|------|
| `scripts/openclaw_run_eval.py` | Trigger-style evaluation without `claude -p` — prepare tasks, run via subagents, aggregate verdicts. |
| `scripts/openclaw_improve_description.py` | Description-improvement flow driven by subagents instead of the Anthropic SDK-only path where applicable. |

Original scripts (`run_eval.py`, `run_loop.py`, `improve_description.py`, etc.) remain for Claude Code or environments where you still use those stacks.

---

## Feature matrix (honest)

| Capability | Claude Code (upstream) | OpenClaw (this repo) |
|------------|-------------------------|------------------------|
| Skill drafting & iteration | Yes | Yes |
| Eval runner, benchmark aggregation, eval viewer | Yes | Yes — use `--static` for headless HTML |
| Blind compare / grader subagents | Yes | Yes — via `sessions_spawn` |
| **Automated** trigger-rate testing (`run_eval` stack) | Yes (`claude -p`) | Yes — `openclaw_run_eval.py` + subagents |
| **Automated** description loop (`run_loop` stack) | Yes | Yes — `openclaw_*` scripts + subagents |
| Package `.skill` | Yes | Yes |

---

## Repository layout

```
skill-creator-claude-cross-platform/
├── SKILL.md                 # Main skill instructions (read this when using the skill)
├── README.md / README_CN.md
├── scripts/                 # Python tooling (eval, package, OpenClaw helpers, …)
├── eval-viewer/             # generate_review.py + viewer template
├── agents/                  # grader, comparator, analyzer prompts
├── assets/                  # HTML templates
└── references/              # e.g. schemas.md
```

---

## Installation

```bash
git clone https://github.com/hanshenmesen/skill-creator-claude-cross-platform.git
```

Copy or symlink the folder into your platform’s skills directory (for OpenClaw, see path hints in `SKILL.md` → Platform Notes).

---

## OpenClaw quick reference

Full commands, path conventions, and subagent patterns live in **`SKILL.md` → “Platform Notes” → “OpenClaw Platform Specifics”**. In short:

- Use `sessions_spawn` with `runtime="subagent"` and `mode="run"` for evals and OpenClaw helper scripts.  
- Prefer `python …/eval-viewer/generate_review.py … --static <out.html>` in headless setups.  
- Run trigger / description flows via `python -m scripts.openclaw_run_eval …` and `python -m scripts.openclaw_improve_description …` as documented there.

Python dependency commonly needed: `pyyaml` (see `SKILL.md`).

---

## Credits

All core methodology and original structure are Anthropic’s work, under Apache 2.0. If this skill helps you, try [Claude Code](https://claude.ai/code) for the reference implementation.
