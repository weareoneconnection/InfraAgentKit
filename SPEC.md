# InfraAgentKit 规范 v2.0

本规范定义智能体卡片、工具、动作意图、回执和审计账本的契约。实现可以替换（数据库、模型、连接器），契约不变。

## 1. 智能体卡片（Agent Card）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | 小写短横线标识 | 全局唯一，例如 `hse-agent` |
| `version` | 字符串 | 卡片版本；与内容一起计算 `fingerprint` |
| `name` / `description` | 字符串 | 展示用 |
| `scope.domain` | 字符串 | 专业领域，用于证据路由 |
| `scope.lifecycle` / `scope.jurisdictions` | 列表 | 适用阶段与司法辖区；首个辖区用于检索过滤 |
| `authority` | `advisory` \| `operator` | advisory 的所有副作用都需人工；operator 可豁免指定的 write 工具 |
| `tools` | 列表 | 允许调用的工具；未声明即拒绝 |
| `evidence.minimum_sources` | 1–5 | SUPPORTED 结论所需的最少来源数 |
| `evidence.domains` | 列表 | 只有这些领域的来源才算证据；空表示不限 |
| `human_gate.required_for` | `write` / `external` | 需要人工批准的副作用类别 |
| `human_gate.exempt_tools` | 列表 | 仅 operator：按策略批准的 write 工具；external 工具永远不能豁免 |
| `limits.max_tool_calls` / `max_runtime_seconds` | 整数 | 单次运行上限 |
| `actions[]` | `{tool, when, title}` | 卡片可以提出的副作用；`when: supported` 表示仅在结论有证据时提出 |
| `instructions` | 字符串 | 给可选模型的专业指引；不改变任何权限 |

卡片严格校验，未知字段为错误。加载时执行静态检查（lint），以下任一情况拒绝加载：未注册的工具、动作不在 `tools` 中、动作是只读工具、非 operator 卡片声明豁免、external 工具被豁免、卡片没有任何证据类工具。

## 2. 工具（Tool）

工具声明 `name`、`description`、`side_effect`（`read_only` / `write` / `external`）、`evidence_output` 和由函数签名生成的参数 JSON Schema（`additionalProperties: false`）。调用时校验参数，未知或缺失参数拒绝。证据类工具输出 `hits[]`，每条含 `ref`、`title`、`version`、`jurisdiction`、`domain`、`digest`（来源文本 SHA-256）、`score`。

## 3. 运行（Run）

1. **路由**：未指定智能体时，按消息检索到的证据领域选择智能体；次要领域的最佳得分须不低于首要领域的 60%。无证据时由一个 advisory 智能体返回 GAP。
2. **规划**：规则规划调用卡片中输入为消息的只读工具；模型规划只能选择卡片的只读工具且参数须符合 Schema，否则退回规则。
3. **工具调用**：每次调用记录参数、输出与输出 SHA-256、规划来源和错误。
4. **结论**：`SUPPORTED` 必须引用本次证据类工具返回、且属于 `evidence.domains` 的来源，数量不少于 `minimum_sources`；否则为 `GAP`，附缺口和向人提出的问题。模型撰写的结论若引用未返回的来源，丢弃并退回规则。
5. **结论核验**：运行结束时重新核对每条 SUPPORTED 结论的引用，以及工具输出是否与记录的摘要一致。

## 4. 动作意图（ActionIntent）与人工关卡

意图记录 `run_id`、`agent_id`、`card_fingerprint`、`tool`、`arguments`、`side_effect`、`status`、`approved_by`、`approval_kind`（`human` / `policy`）。

状态机：`AWAITING_APPROVAL → APPROVED → EXECUTING → EXECUTED | FAILED`，`AWAITING_APPROVAL | APPROVED → REJECTED`。所有状态转换为比较并交换，失败即冲突。

- 批准人必须是具名的人；以 `agent:`、`policy:`、`model:`、`runtime` 开头或为空的批准人一律拒绝。
- 策略批准仅用于 operator 卡片豁免的 write 工具，记为 `policy:<card-id>@<version>`。

## 5. 执行与回执

执行前重新评估策略：提出该意图的卡片必须仍然存在且指纹未变、工具仍被允许、批准有效且类型满足要求。执行只使用被批准时的原参数。

- **执行回执**：`tool`、`status`、`input_digest`（被批准参数的 SHA-256）、`output_digest`、`output`。
- **核验回执**：8 项检查——执行时策略允许、批准已记录、需要时为人工批准、工具一致、输入与批准参数一致、输出摘要有效、执行成功、write 工具未发生外部投递。

## 6. 审计账本

每次状态变化追加一条记录：`seq`、`kind`、`subject`、`actor`、`payload_digest`、`prev_hash`、`hash = SHA-256(prev_hash | kind | subject | actor | payload_digest)`，首条的 `prev_hash` 为 64 个 0。`verify_ledger` 从头重算，返回是否完整以及第一处断裂的序号。

## 7. MCP 映射

MCP 服务暴露：`list_agents`、`knowledge_search`、`risk_assess`、`run_agents`、`get_run`、`list_pending_actions`、`verify_ledger`。不暴露批准、驳回和执行。
