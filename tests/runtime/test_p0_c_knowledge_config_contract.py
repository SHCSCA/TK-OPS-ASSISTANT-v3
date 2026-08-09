from __future__ import annotations

from services.config.schema import DEFAULT_VALUES, WRITABLE_RULES


def test_knowledge_index_limits_are_owned_by_config_bus() -> None:
    assert DEFAULT_VALUES["knowledge.index.maxSourceBytes"] == 20_971_520
    assert DEFAULT_VALUES["knowledge.index.urlTimeoutSeconds"] == 15
    assert DEFAULT_VALUES["knowledge.index.maxRedirects"] == 3


def test_knowledge_index_limits_enforce_safe_boundaries() -> None:
    source_rule = WRITABLE_RULES["knowledge.index.maxSourceBytes"]
    timeout_rule = WRITABLE_RULES["knowledge.index.urlTimeoutSeconds"]
    redirects_rule = WRITABLE_RULES["knowledge.index.maxRedirects"]

    assert source_rule.validator(1_048_576)
    assert source_rule.validator(104_857_600)
    assert not source_rule.validator(1_048_575)
    assert not source_rule.validator(104_857_601)
    assert timeout_rule.validator(1)
    assert timeout_rule.validator(120)
    assert not timeout_rule.validator(0)
    assert redirects_rule.validator(0)
    assert redirects_rule.validator(10)
    assert not redirects_rule.validator(11)
