# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""Consensus compilation of a small progressive tariff into exact integer math."""

from genlayer import *
import json
from typing import Any


MAX_USAGE = 1_000_000
MAX_CENTS = 1_000_000_000_000


def _fail(code: str) -> None:
    raise gl.vm.UserError("[EXPECTED] " + code)


def _bad_model(code: str) -> None:
    raise gl.vm.UserError("[LLM_ERROR] " + code)


def _key(value: str) -> str:
    clean = value.strip().lower()
    if not 1 <= len(clean) <= 40 or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in clean):
        _fail("invalid_key")
    return clean


def _formula(raw: Any) -> dict:
    if not isinstance(raw, dict) or set(raw) != {"fixed_cents", "tiers"}:
        _bad_model("formula_shape")
    fixed = raw["fixed_cents"]
    tiers = raw["tiers"]
    if type(fixed) is not int or not 0 <= fixed <= 100_000_000:
        _bad_model("fixed_charge")
    if not isinstance(tiers, list) or not 1 <= len(tiers) <= 4:
        _bad_model("tiers_shape")
    clean = []
    previous = 0
    for index, tier in enumerate(tiers):
        if not isinstance(tier, dict) or set(tier) != {"up_to", "rate_cents"}:
            _bad_model("tier_shape")
        limit = tier["up_to"]
        rate = tier["rate_cents"]
        if type(limit) is not int or type(rate) is not int or not 0 <= rate <= 100_000:
            _bad_model("tier_value")
        if index == len(tiers) - 1:
            if limit != 0:
                _bad_model("final_tier_must_be_unlimited")
        elif not previous < limit <= MAX_USAGE:
            _bad_model("tier_limits")
        previous = limit
        clean.append({"up_to": limit, "rate_cents": rate})
    return {"fixed_cents": fixed, "tiers": clean}


class RateScript(gl.Contract):
    tariffs: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def publish(self, key: str, tariff_text: str) -> str:
        tariff_id = str(gl.message.sender_address).lower() + ":" + _key(key)
        if self.tariffs.get(tariff_id, ""):
            _fail("tariff_exists")
        source = tariff_text.strip()
        if not 30 <= len(source) <= 3000:
            _fail("invalid_source_length")
        prompt = (
            "Extract ONLY an exact progressive usage tariff from this supplied text. "
            "Return JSON with fixed_cents (integer) and tiers, each {up_to,rate_cents}. "
            "up_to is the inclusive cumulative usage-unit ceiling; the final tier has up_to 0 "
            "for unlimited. Convert money amounts to whole cents. Do not invent missing rates. "
            "If the text cannot express this simple tariff, return an invalid empty object.\n"
            "SOURCE:\n" + source
        )

        def leader_fn():
            return _formula(gl.nondet.exec_prompt(prompt, response_format="json"))

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                return _formula(leader_result.calldata) == leader_fn()
            except Exception:
                return False

        formula = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.tariffs[tariff_id] = json.dumps(
            {"owner": str(gl.message.sender_address), "source": source, "formula": formula},
            sort_keys=True,
            separators=(",", ":"),
        )
        return tariff_id

    @gl.public.view
    def get_tariff(self, tariff_id: str) -> dict:
        raw = self.tariffs.get(tariff_id, "")
        if not raw:
            _fail("tariff_missing")
        return json.loads(raw)

    @gl.public.view
    def quote_cents(self, tariff_id: str, usage_units: u256) -> u256:
        record = self.get_tariff(tariff_id)
        usage = int(usage_units)
        if usage > MAX_USAGE:
            _fail("usage_too_large")
        total = record["formula"]["fixed_cents"]
        previous = 0
        for tier in record["formula"]["tiers"]:
            limit = tier["up_to"]
            units_here = max(0, usage - previous) if limit == 0 else max(0, min(usage, limit) - previous)
            total += units_here * tier["rate_cents"]
            if limit == 0 or usage <= limit:
                break
            previous = limit
        if total > MAX_CENTS:
            _fail("quote_too_large")
        return u256(total)
