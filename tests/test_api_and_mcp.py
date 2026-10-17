import asyncio
import json

from fastapi.testclient import TestClient

from conftest import EDGE


def test_runtime_api_end_to_end():
    from infraagentkit.web import app
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        run = client.post("/runs", json={"message": EDGE}).json()
        aid = run["actions"][0]["id"]
        assert client.post(f"/actions/{aid}/execute").status_code == 403
        assert client.post(f"/actions/{aid}/approve", json={"actor": "agent:hse"}).status_code == 403
        assert client.post(f"/actions/{aid}/approve", json={"actor": "项目经理 张工"}).status_code == 200
        result = client.post(f"/actions/{aid}/execute").json()
        assert result["verification_receipt"]["passed"]
        assert client.post(f"/actions/{aid}/execute").status_code in (403, 409)
        assert client.get("/ledger/verify").json()["valid"]
        assert "properties" in client.get("/schema/agent-card").json()
        assert client.get("/").status_code == 200


def test_mcp_server_exposes_analysis_but_not_approval(runtime):
    from mcp import Client
    from infraagentkit.mcp_server import EXPOSED, build_server

    async def go():
        async with Client(build_server(runtime)) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            assert tools == set(EXPOSED) and not {"approve", "execute"} & tools
            result = await client.call_tool("run_agents", {"message": EDGE})
            payload = json.loads(result.content[0].text)
            assert payload["findings"][0]["status"] == "SUPPORTED"
            assert payload["actions"][0]["status"] == "AWAITING_APPROVAL"
            ledger = json.loads((await client.call_tool("verify_ledger", {})).content[0].text)
            assert ledger["valid"]

    asyncio.run(go())
