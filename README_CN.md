# skill-creator-claude（跨平台 · 含 OpenClaw 完整路径）

[English README](./README.md)

> Anthropic 的 skill 创作方法论 —— 可在 **Claude Code**、**OpenClaw** 及其他支持子代理/文件系统的智能体平台上使用，并尽量与上游保持一致。

本仓库来自 Claude Code 内置的 **skill-creator** 插件：同一套闭环（起草 → 测评 → benchmark → 迭代 → 描述优化 → 打包）。与 Claude Code 强绑定的能力（如 `claude -p`、`present_files` 等）已剥离或改为说明与替代方案。针对 **OpenClaw**，仓库提供独立脚本，用 `sessions_spawn` 子代理替代依赖 `claude -p` 的触发率测试与描述改进流程，从而在 OpenClaw 上跑通同类自动化路径。

---

## 来源与署名

- **原作者**：Anthropic  
- **许可证**：Apache 2.0（与上游 skill-creator 同属该许可体系；再分发时请保留相应声明）  
- **上游位置（Claude Code 插件）**：  
  `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator`  
- **完整上游体验**：[Claude Code](https://claude.ai/code) —— 功能最全、集成最深。

方法论与设计的知识产权归 Anthropic；本仓库为其衍生作品。

---

## 理念

- **改动面尽量小**：除非存在无法移植的硬依赖，否则保持与上游相同的方法论、脚本组织与 agent 提示。  
- **署名清晰**：遵守 Apache 2.0 与对上游的尊重。  
- **OpenClaw 一等公民**：不仅「泛泛支持跨平台」——仓库内含 `openclaw_run_eval.py`、`openclaw_improve_description.py`，并在 `SKILL.md` 的 **Platform Notes** 中写明 OpenClaw 下的路径与用法，避免没有 `claude -p` 时无从下手。  
- **入口而非替代品**：若要 100% 原生 Claude Code 体验，请直接使用 Claude Code；本仓库面向「在其他环境复用同一套方法」。

---

## 相对上游的变化

### `SKILL.md`

与常见说明一致：文首修改说明、打包流程不依赖 `present_files`、合并为统一的 **Platform Notes**、在缺少 `run_loop.py` / `claude -p` 时的替代指引。当前版本在此基础上补充了 **OpenClaw** 专节（`sessions_spawn`、`--static` 评审页、技能安装路径、OpenClaw 替代脚本等）。

### 新增 / 平台向脚本

| 脚本 | 作用 |
|------|------|
| `scripts/openclaw_run_eval.py` | 不依赖 `claude -p` 的触发类评测：准备任务 → 子代理执行 → 聚合 verdict。 |
| `scripts/openclaw_improve_description.py` | 以子代理编排为主的描述改进流程，对应上游中依赖 CLI/SDK 组合的部分路径。 |

`run_eval.py`、`run_loop.py`、`improve_description.py` 等仍保留，供 Claude Code 或仍使用原栈的环境选用。

---

## 功能对照

| 能力 | Claude Code（上游） | OpenClaw（本仓库） |
|------|---------------------|-------------------|
| 技能起草与迭代 | 支持 | 支持 |
| 测评、benchmark、评审页 | 支持 | 支持 —— 无界面环境请用 `--static` 生成 HTML |
| 盲评 / 评分子代理 | 支持 | 支持 —— `sessions_spawn` |
| **自动化**触发率测试（`run_eval` 体系） | 支持（`claude -p`） | 支持 —— `openclaw_run_eval.py` + 子代理 |
| **自动化**描述优化闭环（`run_loop` 体系） | 支持 | 支持 —— `openclaw_*` + 子代理 |
| 打包 `.skill` | 支持 | 支持 |

---

## 仓库结构

```
skill-creator-claude-cross-platform/
├── SKILL.md                 # 技能主文档（使用本技能时以该文件为准）
├── README.md / README_CN.md
├── scripts/                 # Python 工具链（含 OpenClaw 辅助脚本）
├── eval-viewer/             # generate_review.py 与页面模板
├── agents/                  # grader / comparator / analyzer
├── assets/
└── references/              # 如 schemas.md
```

---

## 安装与使用

```bash
git clone https://github.com/hanshenmesen/skill-creator-claude-cross-platform.git
```

将整个目录放入你所在平台的 skills 目录（OpenClaw 的路径约定见 `SKILL.md` → Platform Notes）。

---

## OpenClaw 速查

完整命令、路径与子代理约定见 **`SKILL.md` →「Platform Notes」→「OpenClaw Platform Specifics」**。摘要如下：

- 子代理统一通过 `sessions_spawn`，`runtime="subagent"`，`mode="run"`。  
- 无头环境用 `generate_review.py` 的 `--static` 输出独立 HTML。  
- 触发测试与描述改进分别使用 `python -m scripts.openclaw_run_eval …` 与 `python -m scripts.openclaw_improve_description …`，步骤与参数以 `SKILL.md` 为准。  

Python 侧常见依赖：`pyyaml`（详见 `SKILL.md`）。

---

## 致谢

核心方法论与原始结构来自 Anthropic，Apache 2.0 许可。若本技能对你有用，也欢迎体验 [Claude Code](https://claude.ai/code) 中的完整实现。
