# InfraAgentKit

**交通基础设施受治理智能体开源框架：智能体卡片 · 工具与技能 · 证据契约 · 人工关卡 · 执行回执 · 独立核验 · MCP**

InfraAgentKit 让交通行业团队用工程化的方式开发专业智能体，而不是把提示词当成全部架构。每个智能体都有声明式的“卡片”规定能做什么；所有结论必须引用本次真实检索到的证据；所有写操作和对外动作只能以“待审批意图”的形式出现，由具名的人批准后才执行；每一步写入哈希链审计账本，任何事后篡改都能被发现。

> 本项目是 GlobalInfra AI 平台的**智能体框架层**，可独立安装、独立运行；平台中的专业智能体可按同一套卡片与回执规范接入。

## 为什么需要它

| 常见做法 | 风险 | InfraAgentKit 的做法 |
| --- | --- | --- |
| 提示词里写“不要乱发邮件” | 模型被注入或出错时照样执行 | 副作用工具在分析阶段**根本不可调用**，只能生成待审批意图 |
| 让模型自己说“依据某某规范” | 引用编造的条款 | 结论只能引用**本次工具实际返回**的来源，否则退回规则或标为证据缺口 |
| 字符串包含就算命中 | “knowledge” 命中 “edge”，误报高处作业 | 英文按词边界匹配，中文按双字切分检索，停用词过滤 |
| 日志可以随意修改 | 事后无法证明谁批准了什么 | 账本逐条哈希链接，改一条、删一条都能被检出 |
| 审批后随便执行 | 卡片被改、参数被换、重复执行 | 执行前按**提出时的卡片指纹**复核策略，只执行**被批准的原参数**，比较并交换防重复 |

## 5 分钟运行

需要 Python 3.11 或更高版本。

```bash
git clone https://github.com/weareoneconnection/InfraAgentKit.git && cd InfraAgentKit
```

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
infra-agent doctor                 # 检查卡片、工具、知识包和 MCP SDK
infra-agent serve --port 8103      # 打开 http://127.0.0.1:8103 控制台
infra-agent eval                   # 35 项基准测试（含 11 项治理攻击）
pytest -q                          # 27 项单元与集成测试
```

命令行完成一次完整的闭环：

```bash
infra-agent run "P47 墩临边防护缺失，工人在高处作业未系安全带"   # 自动路由到 HSE 智能体，返回待审批意图
infra-agent pending
infra-agent approve ACT-XXXX --actor "项目经理 张工"            # 只有具名的人可以批准
infra-agent execute ACT-XXXX                                   # 执行回执 + 独立核验回执
infra-agent audit                                              # 校验哈希链账本
```

MCP（官方 MCP Python SDK v2）：

```bash
infra-agent mcp-serve                                    # stdio
infra-agent mcp-serve --transport streamable-http        # http://127.0.0.1:8113/mcp
```

MCP 只暴露分析能力（知识检索、风险评估、运行智能体、查询运行记录、待审批列表、账本校验）。**审批和执行刻意不通过 MCP 暴露**：MCP 宿主是自动化客户端，只能提出副作用，不能授权或执行。

## 核心流程

```text
消息 ──▶ 按证据路由 ──▶ 智能体卡片 ──▶ 只读工具（规则或模型规划，均受卡片约束）
                                        │  每次调用记录参数与输出 SHA-256
                                        ▼
                                  证据契约：结论只能引用本次返回的来源
                                        │  无足够证据 → GAP + 向人提问，不产生动作
                                        ▼
                                  副作用意图（write / external）
                                        │  external 永远需要人；write 需要人，
                                        │  operator 卡片可声明豁免并记为“策略批准”
                                        ▼
                     具名人员批准 ──▶ 执行前按卡片指纹复核 ──▶ 执行被批准的原参数
                                        ▼
                         执行回执 + 独立核验回执（8 项检查）──▶ 哈希链账本
```

## 智能体卡片

```yaml
id: hse-agent
version: 2.0.0
name: HSE Agent
scope: {domain: hse, lifecycle: [construction, commissioning]}
authority: advisory                      # advisory | operator
tools: [risk.assess, knowledge.search, document.draft, notification.send]
evidence: {minimum_sources: 1, domains: [hse]}
human_gate: {required_for: [write, external]}
actions:
  - tool: document.draft
    title: "{agent} stop-work and rectification instruction"
instructions: Ground every conclusion in retrieved HSE sources.
```

卡片严格校验（未知字段直接报错），并对照工具注册表做静态检查：未注册的工具、非 operator 卡片的豁免、external 工具被豁免、没有证据类工具等都会在加载时失败。完整规范见 [SPEC.md](SPEC.md)，JSON Schema 可用 `infra-agent schema` 导出。

## 扩展：接入自己的系统

```python
from infraagentkit import AgentCard, GovernedRuntime, default_registry

registry = default_registry()
registry.register("schedule.lookup", "Look up the programme activity for an asset", schedule_lookup)  # 只读
registry.register("p6.update", "Update a P6 activity", p6_update, side_effect="write")               # 需审批
runtime = GovernedRuntime([card], registry=registry)
```

完整示例见 [examples/python/custom_tool.py](examples/python/custom_tool.py)。工具参数的 JSON Schema 由函数签名自动生成，未知或缺失参数会被拒绝。

## 可选的大模型

设置 `INFRAAGENTKIT_MODEL_BASE_URL`、`INFRAAGENTKIT_MODEL` 和（如需）`INFRAAGENTKIT_MODEL_API_KEY`，即可接入任意 OpenAI 兼容接口（DeepSeek、通义千问、本地 Ollama 等）。模型只用于两件事，且都不被信任：

- **规划**：只能从卡片声明的只读工具中选，参数须符合工具 Schema；否则退回规则规划。
- **撰写结论**：只能引用本次检索到的来源编号（Schema 枚举 + 运行时复核）；否则退回规则结论。

用户消息和工具输出都以 `<data>` 包裹作为不可信数据传给模型，其中的指令不被执行。

## 内置内容

- 5 个示例智能体：HSE、质量、合同、吊装设备、资产养护（operator 权限示例）
- 13 条中英双语合成知识源（HSE、质量、合同、设备、资产），每条带版本和内容摘要
- 4 个参考工具：`knowledge.search`、`risk.assess`、`document.draft`（write，只生成草稿）、`notification.send`（external，模拟不发送）

## 基准测试

`infra-agent eval` 运行 35 项确定性测试：接地 14 项（含中文）、无证据拒答 6 项（含 “knowledge/hedge/encroachment” 等对抗子串）、风险 4 项、治理攻击 11 项（未批准执行、非人审批、重复执行、卡片篡改后执行、外部动作免审、账本篡改、编造引用、模型规划副作用、调用未声明工具、提示词注入、工具输出被改）。当前全部通过。数据为合成数据，只证明在该测试集上可复现，不代表真实项目准确率。

## 边界

示例知识与工具均为合成内容；`notification.send` 返回 `SIMULATED_NOT_SENT`，不会产生外部副作用。接入 P6、BIM、ERP、邮件等真实系统时，应在相同的工具、策略和回执契约下实现连接器，并配置最小权限凭据、身份认证和备份。参考运行时未内置身份认证，生产部署须放在企业身份网关之后。

## 许可证

Apache-2.0，见 [LICENSE](LICENSE)。第三方依赖见 [THIRD_PARTY.md](THIRD_PARTY.md)。
