from __future__ import annotations

import pytest

from app.transforms import MappingRule, TransformError, apply_mapping

R = MappingRule


def test_rename_is_the_basic_mapping() -> None:
    assert apply_mapping({"first_name": "John", "mail": "john@example.com"},
                         [R(source="first_name", target="name"), R(source="mail", target="email")]) == {
        "name": "John", "email": "john@example.com"}


def test_nested_paths_read_and_write() -> None:
    record = {"customer": {"address": {"city": "Lisbon"}}, "items": [{"sku": "A1"}]}
    rules = [R(source="customer.address.city", target="shipping.city"), R(source="items.0.sku", target="first_sku")]
    assert apply_mapping(record, rules) == {"shipping": {"city": "Lisbon"}, "first_sku": "A1"}


@pytest.mark.parametrize(("value", "expected"), [("42", 42), ("129.90", 129.9), ("$1,299.50", 1299.5), (7, 7), ("-3", -3)])
def test_number_conversion(value, expected) -> None:  # noqa: ANN001
    assert apply_mapping({"v": value}, [R(source="v", target="v", transform="to_number")])["v"] == expected


@pytest.mark.parametrize(("value", "expected"), [("yes", True), ("NO", False), ("1", True), (0, False), (True, True)])
def test_boolean_conversion(value, expected) -> None:  # noqa: ANN001
    assert apply_mapping({"v": value}, [R(source="v", target="v", transform="to_boolean")])["v"] is expected


def test_prefix_suffix_and_case() -> None:
    rules = [R(source="id", target="ref", transform="prefix", argument="CUS-"),
             R(source="code", target="code", transform="suffix", argument="-EU"),
             R(source="country", target="country", transform="lowercase")]
    assert apply_mapping({"id": 17, "code": "X9", "country": "PT"}, rules) == {"ref": "CUS-17", "code": "X9-EU", "country": "pt"}


def test_a_bad_value_names_the_field() -> None:
    with pytest.raises(TransformError, match=r"age: age — can't convert 'forty' to a number"):
        apply_mapping({"age": "forty"}, [R(source="age", target="age", transform="to_number")])


def test_required_fields_and_defaults() -> None:
    rules = [R(source="mail", target="email", required=True)]
    with pytest.raises(TransformError, match="Missing required field: mail"):
        apply_mapping({"name": "x"}, rules)
    assert apply_mapping({}, [R(source="plan", target="plan", default="free")]) == {"plan": "free"}
    assert apply_mapping({}, [R(source="plan", target="plan")]) == {}, "optional and absent: left out"


def test_rules_are_validated() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        R(source="x", target="y", transform="eval")
    with pytest.raises(ValidationError):
        R(source="x", target="y", transform="prefix")  # needs an argument
    with pytest.raises(ValidationError):
        R(source="x; drop table", target="y")
