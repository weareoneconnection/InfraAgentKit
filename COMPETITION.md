# 参赛对齐说明

赛道：开源项目。

作品形态：**可安装 Python 开源框架 + CLI + Agent Card 规范 + Tool/Skill Registry + Governance Runtime + 官方 MCP SDK v2 Server + Benchmark + 示例 Agent。**

## 冠军演示

```bash
pip install -e .
infra-agent doctor
infra-agent init my-agent
infra-agent serve
```

浏览器运行一个 HSE Agent：

1. Agent 调用风险和知识工具。
2. Finding 必须引用实际证据。
3. Side-effect Action 显示 `AWAITING_APPROVAL`。
4. 未批准直接执行返回拒绝。
5. 人工批准后执行生成 Receipt。
6. Verifier 独立检查摘要与授权并 PASS。
7. 同一套工具通过 MCP 暴露给标准 MCP Host。

## 开源交付

- Apache-2.0
- CLI / SDK / Runtime API
- 官方 MCP SDK v2 adapter
- 3 个行业 Agent 示例
- Benchmark 数据与 CI
- SECURITY / CONTRIBUTING / CODE_OF_CONDUCT
