"""Direct behavior and edge tests for this contract."""

import json
import pytest

def address(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)

def mock(direct_vm, result, pattern=r".*"):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(pattern, json.dumps(result))

def _address(value):
    return "0x" + bytes(value).hex() if isinstance(value, (bytes, bytearray)) else str(value)

def _mock(vm, answer):
    vm.clear_mocks()
    vm.mock_llm(r".*", json.dumps(answer))

def test_rate_script_tiers_and_rejections(deploy, direct_vm):
    contract = deploy("rate_script.py")
    mock(direct_vm, {"fixed_cents": 125, "tiers": [
        {"up_to": 100, "rate_cents": 10}, {"up_to": 0, "rate_cents": 20}]})
    tariff_id = contract.publish("home", "Fixed 1.25 dollars plus 10 cents per unit for the first 100 units, then 20 cents.")
    assert contract.quote_cents(tariff_id, 0) == 125
    assert contract.quote_cents(tariff_id, 150) == 2125
    with direct_vm.expect_revert("tariff_exists"):
        contract.publish("home", "Fixed 1.25 dollars plus 10 cents per unit for the first 100 units, then 20 cents.")
    with direct_vm.expect_revert("usage_too_large"):
        contract.quote_cents(tariff_id, 1_000_001)
    mock(direct_vm, {"fixed_cents": 0, "tiers": [{"up_to": 100, "rate_cents": 10}]})
    with direct_vm.expect_revert("final_tier_must_be_unlimited"):
        contract.publish("bad", "This is a sufficiently long but deliberately incomplete tariff text.")

def test_rate_script_rejects_nonprogressive_tiers(deploy, direct_vm):
    contract = deploy("rate_script.py")
    _mock(direct_vm, {"fixed_cents": 10, "tiers": [
        {"up_to": 200, "rate_cents": 4},
        {"up_to": 100, "rate_cents": 5},
        {"up_to": 0, "rate_cents": 6}]})
    with direct_vm.expect_revert("tier_limits"):
        contract.publish("bad", "First 200 units cost 4 cents, next 100 cost 5 cents, the rest cost 6 cents.")
