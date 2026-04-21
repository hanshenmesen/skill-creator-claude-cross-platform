# skill-creator-claude（OpenClaw 适配版）

> Anthropic 的 skill 创作方法论 —— 已完整适配 OpenClaw 平台。

原版由 Anthropic 为 Claude Code 打造，涵盖技能起草、测评、迭代、benchmark 和 description 优化的完整开发闭环。本版本在保留全部核心方法论的基础上，将 Claude Code 专有依赖替换为 OpenClaw 原生能力，实现所有功能可用。


---

## 功能概览

整个技能围绕一个核心循环：

```
构思 → 草稿 → 测试 → 评审 → 改进 → 再测试 → 满意为止 → 打包发布
```

### 五大功能模块

| 模块 | 说明 |
|------|------|
| **① 技能创建** | 通过问答理解意图，生成 SKILL.md 草稿 |
| **② 测试运行** | 用子代理跑测试用例（with_skill vs without_skill 对比） |
| **③ 评分 & Benchmark** | 子代理评分 → 聚合统计 → 生成可视化评审页面 |
| **④ 迭代改进** | 根据反馈修改技能，重跑测试，循环至满意 |
| **⑤ 描述优化** | 测试并优化 SKILL.md 的 description 字段触发准确率 |

---

## 文件结构

```
skill-creator-claude-master/
├── SKILL.md                          # 技能主文件（核心指令）
├── README.md                         # 英文说明
├── README_CN.md                      # 中文说明（本文件）
│
├── scripts/                          # Python 脚本
│   ├── utils.py                      # 共享工具（解析 frontmatter）
│   ├── __init__.py                   # 包标识
│   ├── aggregate_benchmark.py        # 聚合 grading → benchmark 统计
│   ├── generate_report.py            # 生成描述优化 HTML 报告
│   ├── quick_validate.py             # 验证 SKILL.md 格式
│   ├── package_skill.py              # 打包为 .skill 文件
│   ├── openclaw_run_eval.py          # ✨ OpenClaw 触发率测试（替代 run_eval.py）
│   ├── openclaw_improve_description.py  # ✨ OpenClaw 描述改进（替代 improve_description.py）
│   ├── run_eval.py                   # 原版触发测试（需 claude -p，备用）
│   ├── run_loop.py                   # 原版优化循环（需 claude -p + anthropic SDK，备用）
│   └── improve_description.py        # 原版描述改进（需 anthropic SDK，备用）
│
├── eval-viewer/                      # 评审页面
│   ├── generate_review.py            # 生成评审 HTML
│   └── viewer.html                   # HTML 模板
│
├── agents/                           # 子代理指令
│   ├── grader.md                     # 评分代理
│   ├── comparator.md                 # 盲比较代理
│   └── analyzer.md                   # 分析代理
│
├── assets/
│   └── eval_review.html              # eval 查询审查页面模板
│
└── references/
    └── schemas.md                    # JSON 结构规范
```

---

## OpenClaw 适配说明

### 与原版的差异

原版三个核心脚本依赖 Claude Code 专有工具，本版本用 OpenClaw 原生能力替代：

| 原始脚本 | 依赖 | OpenClaw 替代 | 替代原理 |
|---------|------|--------------|---------|
| `run_eval.py` | `claude -p` CLI | `openclaw_run_eval.py` | 用 `sessions_spawn` 子代理模拟触发决策 |
| `improve_description.py` | `anthropic` SDK | `openclaw_improve_description.py` | 用 `sessions_spawn` 子代理执行改进 prompt |
| `run_loop.py` | 上面两者 | 由 AI 在对话中编排循环 | 组合上面两个替代脚本 |

### 替代脚本用法

**触发率测试**（`openclaw_run_eval.py`）— 三步走：

```bash
# 1. 准备任务
python -m scripts.openclaw_run_eval \
  --eval-set trigger_eval.json --skill-path <skill> \
  --output-dir verdicts/ --runs-per-query 1 \
  prepare --tasks-output tasks.json

# 2. 用 sessions_spawn 执行每个 task 的 prompt（子代理写 verdict JSON）

# 3. 聚合结果
python -m scripts.openclaw_run_eval \
  --eval-set trigger_eval.json --skill-path <skill> \
  --output-dir verdicts/ \
  aggregate --tasks-input tasks.json --results-output results.json
```

**描述改进**（`openclaw_improve_description.py`）— 三步走：

```bash
# 1. 生成 prompt
python -m scripts.openclaw_improve_description generate \
  --eval-results results.json --skill-path <skill> \
  --output-dir improve/

# 2. 用 sessions_spawn 执行 improve/improve_prompt.md，响应写入 improve/response.md

# 3. 解析结果
python -m scripts.openclaw_improve_description parse \
  --response-file improve/response.md --output improved.json
```

### 其他适配

- **Eval Viewer**：使用 `--static` 模式生成独立 HTML，通过 CDN 上传分享
- **子代理**：通过 `sessions_spawn`（`runtime="subagent"`, `mode="run"`）执行
- **Python 依赖**：仅需 `pyyaml`（`pip install --break-system-packages pyyaml`）

---

## 功能完整性

| 功能 | 状态 | 说明 |
|------|------|------|
| Skill 起草与迭代 | ✅ | 完整支持 |
| 测试运行（子代理） | ✅ | 通过 sessions_spawn 并发执行 |
| 评分（Grading） | ✅ | 子代理按 grader.md 规范评分 |
| Benchmark 聚合 | ✅ | aggregate_benchmark.py 正常工作 |
| Eval Viewer | ✅ | --static 模式生成 HTML |
| Description 触发测试 | ✅ | openclaw_run_eval.py 替代实现 |
| Description 改进 | ✅ | openclaw_improve_description.py 替代实现 |
| 盲比较 | ✅ | 通过子代理执行 comparator.md |
| 打包 .skill | ✅ | package_skill.py 正常工作 |
| 技能验证 | ✅ | quick_validate.py 正常工作 |

**所有功能在 OpenClaw 平台上均可完整运行。**
