from infraagentkit.cards import lint_catalog, load_cards
from infraagentkit.knowledge import load_packs
from infraagentkit.tools import default_registry

from conftest import AGENTS


def test_catalog_has_24_domains_and_6_platform_agents():
    cards = load_cards(AGENTS)
    assert len(cards) == 30
    assert sum(card.tier == "domain" for card in cards) == 24
    assert sum(card.tier == "control" for card in cards) == 4
    assert sum(card.tier == "assurance" for card in cards) == 2
    assert not lint_catalog(cards, default_registry())


def test_full_lifecycle_knowledge_covers_every_domain():
    cards = load_cards(AGENTS)
    sources = load_packs()
    governed = {source.domain for source in sources}
    required = {card.scope.domain for card in cards}
    assert required <= governed
    assert len(sources) >= 50


def test_dynamic_team_uses_lead_support_and_control_plane(runtime):
    team = runtime.compose_team("分包商申请变更并要求延长关键线路工期，需评估费用和索赔证据")
    assert team["lead"] in team["members"]
    assert len(team["members"]) <= 5
    assert {"data-intake-triage-agent", "project-orchestrator-agent",
            "evidence-provenance-agent", "independent-verifier-agent"} <= set(team["control"])


def test_spatial_and_country_controls_are_contextual(runtime):
    team = runtime.compose_team("Malaysia 国家包下检查 IFC 构件、GeoJSON 图层与 IoT 传感器")
    assert "digital-twin-spatial-agent" in team["control"]
    assert "country-localization-agent" in team["control"]


def test_connector_previews_are_read_only():
    registry = default_registry()
    assert len(registry.names()) == 10
    twin = registry.call("twin.locate", {"asset_id": "P47"})
    telemetry = registry.call("telemetry.read", {"sensor_id": "BRG03-DISP-X"})
    assert twin["mode"] == "SYNTHETIC_READ_ONLY_PREVIEW"
    assert telemetry["external_write_performed"] is False


def test_run_contains_handoffs_and_synthesis(runtime):
    run = runtime.run("P47 墩临边防护缺失，工人在高处作业未系安全带")
    assert run["team"]["lead"] == "hse-agent"
    assert run["synthesis"]["status"] == "SUPPORTED"
    assert "HSE-WAH-001" in run["synthesis"]["evidence_refs"]
    assert run["synthesis"]["human_decision_required"] is True
