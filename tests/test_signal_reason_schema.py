import typing

from cilly_trading.models import (
    DataRef,
    RuleRef,
    SignalReason,
    compute_signal_reason_id,
)


def _annotation_keys(typed_dict_cls: type) -> set[str]:
    try:
        hints = typing.get_type_hints(typed_dict_cls)
    except TypeError:
        hints = getattr(typed_dict_cls, "__annotations__", {})
    return set(hints.keys())


def _base_inputs():
    rule_ref: RuleRef = {
        "rule_id": "rule-1",
        "rule_version": "1.0.0",
    }
    data_refs: list[DataRef] = [
        {
            "data_type": "INDICATOR_VALUE",
            "data_id": "rsi-14",
            "value": 72.5,
            "timestamp": "2024-01-01T00:00:00Z",
        },
        {
            "data_type": "PRICE_VALUE",
            "data_id": "close",
            "value": 101.25,
            "timestamp": "2024-01-01T00:00:00Z",
        },
    ]
    return rule_ref, data_refs


def test_signal_reason_id_deterministic():
    rule_ref, data_refs = _base_inputs()
    first = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=data_refs,
    )
    second = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=data_refs,
    )
    assert first == second


def test_signal_reason_id_order_invariant_for_data_refs():
    rule_ref, data_refs = _base_inputs()
    reversed_refs = list(reversed(data_refs))
    first = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=data_refs,
    )
    second = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=reversed_refs,
    )
    assert first == second


def test_signal_reason_id_sensitive_to_inputs():
    rule_ref, data_refs = _base_inputs()
    baseline = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=data_refs,
    )
    changed_rule = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref={"rule_id": "rule-2", "rule_version": "1.0.0"},
        data_refs=data_refs,
    )
    changed_data = compute_signal_reason_id(
        signal_id="signal-1",
        reason_type="INDICATOR_THRESHOLD",
        rule_ref=rule_ref,
        data_refs=[
            {
                "data_type": "INDICATOR_VALUE",
                "data_id": "rsi-14",
                "value": 70.0,
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "data_type": "PRICE_VALUE",
                "data_id": "close",
                "value": 101.25,
                "timestamp": "2024-01-01T00:00:00Z",
            },
        ],
    )
    assert baseline != changed_rule
    assert baseline != changed_data


def test_no_free_text_fields_in_schema():
    forbidden = {"description", "explanation", "message", "text", "notes", "comment"}
    schema_keys = (
        _annotation_keys(SignalReason)
        | _annotation_keys(RuleRef)
        | _annotation_keys(DataRef)
    )
    assert not {key for key in schema_keys if key.lower() in forbidden}
