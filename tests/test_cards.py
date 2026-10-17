import pytest
from pydantic import ValidationError

from infraagentkit.cards import AgentCard, lint, load_cards
from infraagentkit.tools import default_registry

from conftest import AGENTS


def card(**overrides):
    base = {"id": "test-agent", "name": "Test", "scope": {"domain": "hse"}, "tools": ["knowledge.search", "document.draft"],
            "actions": [{"tool": "document.draft"}]}
    base.update(overrides)
    return AgentCard.model_validate(base)


def test_example_cards_are_clean():
    registry = default_registry()
    assert all(not lint(c, registry) for c in load_cards(AGENTS))


def test_unknown_keys_and_bad_ids_are_rejected():
    with pytest.raises(ValidationError):
        card(permissions="all")
    with pytest.raises(ValidationError):
        card(id="Bad Id")


def test_lint_catches_unsafe_or_ineffective_cards():
    registry = default_registry()
    assert any("not registered" in i for i in lint(card(tools=["knowledge.search", "document.draft", "erp.pay"]), registry))
    assert any("only operator" in i for i in lint(card(human_gate={"exempt_tools": ["document.draft"]}), registry))
    external = card(authority="operator", tools=["knowledge.search", "notification.send"], actions=[{"tool": "notification.send"}],
                    human_gate={"required_for": [], "exempt_tools": ["notification.send"]})
    assert any("never be exempt" in i for i in lint(external, registry))
    assert any("no evidence-producing tool" in i for i in lint(card(tools=["document.draft"]), registry))


def test_fingerprint_changes_with_the_card():
    assert card().fingerprint() != card(version="1.0.1").fingerprint()
