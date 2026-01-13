import pytest

from cilly_trading.engine.core import canonical_json, sha256_hex


def test_canonical_json_deterministic_for_key_order() -> None:
    payload_a = {"b": 1, "a": 2}
    payload_b = {"a": 2, "b": 1}

    canonical_a = canonical_json(payload_a)
    canonical_b = canonical_json(payload_b)

    assert canonical_a == canonical_b
    assert sha256_hex(canonical_a) == sha256_hex(canonical_b)


def test_canonical_json_normalizes_assets_list() -> None:
    payload_a = {"assets": [" btc", "Eth", "BTC "]}
    payload_b = {"assets": ["ETH", "BTC", "BTC"]}

    canonical_a = canonical_json(payload_a)
    canonical_b = canonical_json(payload_b)

    assert canonical_a == canonical_b
    assert sha256_hex(canonical_a) == sha256_hex(canonical_b)


def test_canonical_json_tuple_equals_list_for_non_assets() -> None:
    payload_a = {"params": ("b", "a")}
    payload_b = {"params": ["b", "a"]}

    assert canonical_json(payload_a) == canonical_json(payload_b)


def test_canonical_json_nested_structure_deterministic() -> None:
    payload_a = {
        "outer": {"b": 2, "a": {"d": 4, "c": 3}},
        "list": [{"y": 2, "x": 1}, {"b": 2, "a": 1}],
    }
    payload_b = {
        "list": [{"x": 1, "y": 2}, {"a": 1, "b": 2}],
        "outer": {"a": {"c": 3, "d": 4}, "b": 2},
    }

    assert canonical_json(payload_a) == canonical_json(payload_b)


def test_canonical_json_rejects_float() -> None:
    with pytest.raises(TypeError):
        canonical_json({"value": 1.0})


def test_canonical_json_rejects_unsupported_type() -> None:
    with pytest.raises(TypeError):
        canonical_json({"value": {1, 2}})


def test_canonical_json_rejects_non_string_dict_keys() -> None:
    with pytest.raises(TypeError):
        canonical_json({1: "value"})
