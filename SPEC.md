# InfraAgentKit 规范 v4.0

本规范定义智能体卡片、工具、动作意图、回执和审计账本的契约。实现可以替换（数据库、模型、连接器），契约不变。

## 1. 智能体卡片（Agent Card）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | 小写短横线标识 | 全局唯一，例如 `hse-agent` |
| `version` | 字符串 | 卡片版本；与内容一起计算 `fingerprint` |
| `name` / `description` | 字符串 | 展示用 |
| `tier` | `control` / `domain` / `assurance` | 控制、专业或独立保证层 |
| `scope.domain` | 字符串 | 专业领域，用于证据路由 |
| `scope.lifecycle` / `scope.jurisdictions` | 列表 | 适用阶段与司法辖区；首个辖区用于检索过滤 |
| `scope.data_classes` / `scope.project_types` | 列表 | 允许处理的数据类别与项目类型 |
| `capabilities` | 列表 | 可展示、可发现的能力声明，不增加权限 |
| `collaborates_with` / `escalates_to` | 列表 | 跨智能体协作与升级关系，加载时校验引用 |
| `output_contract` | 列表 | 交接输出字段，默认 finding、evidence_refs、gaps、questions |
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

1. **分诊与动态编组**：未指定智能体时，按消息检索到的证据领域选择 1 个主责和最多 4 个协同专业智能体；控制面包含接入、编排、证据与独立验证，国家或空间上下文按信号加入。无证据时由一个 domain/advisory 智能体返回 GAP。
2. **规划**：规则规划调用卡片中输入为消息的只读工具；模型规划只能选择卡片的只读工具且参数须符合 Schema，否则退回规则。
3. **工具调用**：每次调用记录参数、输出与输出 SHA-256、规划来源和错误。
4. **结论**：`SUPPORTED` 必须引用本次证据类工具返回、且属于 `evidence.domains` 的来源，数量不少于 `minimum_sources`；否则为 `GAP`，附缺口和向人提出的问题。模型撰写的结论若引用未返回的来源，丢弃并退回规则。
5. **结论核验**：运行结束时重新核对每条 SUPPORTED 结论的引用，以及工具输出是否与记录的摘要一致。
6. **交接与合成**：协同智能体以固定输出契约向主责智能体交接；运行时汇总证据、缺口、最高风险和冲突，但合成结果不替代具名人员决定。

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

## 8. 平台智能体步骤回执

每次运行除专业智能体结果外，必须产生有序的 `platform_steps[]`。接入分诊、项目编排、证据溯源和独立验证为必选步骤；国家属地化、数字孪生空间智能体按输入信号加入。每步至少记录 `agent_id`、`tier`、`phase`、输入/输出契约、卡片指纹、状态、结果和 `output_digest`，并以独立 `agent.step` 项写入哈希账本。平台步骤不拥有审批权。

## 9. 身份与角色

生产模式通过 `INFRAAGENTKIT_API_TOKENS` 配置服务端 token 到具名人员及角色的映射。角色为 `viewer`、`analyst`、`reviewer`、`executor`、`admin`，按最小权限继承。运行、批准/驳回、执行分别至少需要 analyst、reviewer、executor；审计 actor 取 token 绑定身份而非请求体声明。

未配置 token 时系统进入 `demo-unverified`，仅用于公开演示。接口和控制台必须明确披露：身份未经验证，内置副作用连接器为模拟实现。该模式不得被描述为生产级认证。

## 10. 连接器

连接器提供严格校验的 manifest，声明连接器 ID、版本、系统、模式、工具、参数和说明。注册后的工具继续服从 Agent Card 白名单、参数 Schema、策略与回执约束。文件快照参考连接器为只读，输出必须携带来源文件 SHA-256 与 `external_write_performed: false`。生产连接器不得通过修改智能体指令绕开注册表或策略层。

## 11. 作用域、幂等与模型可观测

运行记录 `tenant_id` 与 `project_id`。客户端可以提交 `Idempotency-Key`；相同租户、项目与键只能对应一个运行，重放必须返回原运行并标注 `idempotent_replay`，不得重复产生动作意图。

模型可观测至少区分规划调用、专业结论调用、成功、失败、规则回退和延迟。评测结果必须将确定性、无密钥的治理基准与可选的在线模型基准分开呈现；规则回退不得冒充模型成功。
