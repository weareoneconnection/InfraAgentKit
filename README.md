# InfraAgentKit

**交通基础设施智能体技能、工具与 MCP 开源框架**

InfraAgentKit 是独立的开源赛道作品：让交通行业团队可以快速开发**有权限边界、有证据、有人工关卡、有执行回执、可独立核验**的专业 Agent，而不是把 Prompt 当成全部架构。

## 5 分钟运行

Python 3.11+：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
infra-agent doctor
infra-agent serve --port 8103
```

打开 http://127.0.0.1:8103 。

运行 Benchmark：

```bash
infra-agent eval
```

启动官方 MCP Python SDK v2 server（stdio）：

```bash
infra-agent mcp-serve
```

或 Streamable HTTP：

```bash
infra-agent mcp-serve --transport streamable-http --port 8113
```

MCP endpoint 默认为 `http://127.0.0.1:8113/mcp`。

## 框架核心

```text
Agent Card
   ↓
Tool Registry
   ↓
Policy Engine
   ↓
Evidence-backed Finding
   ↓
Action Intent
   ↓
Human Approval Gate
   ↓
Tool Execution
   ↓
Execution Receipt
   ↓
Independent Contract Verifier
```

### Agent Card 不是 Prompt

每个 Agent 明确声明：

- scope / lifecycle
- authority
- allowed tools
- evidence policy
- human gate
- runtime limits

### Default Deny

未在 Agent Card 注册的 Tool 不允许调用；只读工具可直接运行，写入/外部副作用默认进入人工审批。

### Evidence Contract

`SUPPORTED` Finding 必须来自真实 tool result 中的 evidence refs。证据不足返回 `GAP`，不会生成副作用 Action。

### Receipt + Verification

Agent 不能用“我完成了”证明成功。Runtime 生成 Execution Receipt，Verifier 重新检查审批、工具、输入摘要、输出摘要和执行状态。

## 开源边界

示例知识、数据和工具均为合成内容；`notification.send` 是 `SIMULATED_NOT_SENT`，不会真的向外部系统发送。接入 P6/BIM/ERP/邮件等真实系统时，应作为独立 connector/skill，在相同 Tool + Policy + Receipt contract 下运行。
