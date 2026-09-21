"""Test cho Agent/backend/payments/x402.py -- payment gating thật cho x402.

Trọng tâm nghiệm thu:
1. Mặc định TẮT (X402_ENABLED không đặt / "false") không ảnh hưởng gì tới hệ
   thống hiện có -- import module không cần biến môi trường nào, không gọi
   mạng, không đổi hành vi mặc định.
2. Payload 402 (PaymentRequired/PaymentRequirements) sinh ra đúng định dạng
   wire thật (camelCase, tên trường) đã khảo sát được từ gói
   `okxweb3-app-x402` trên PyPI.
3. verify_payment() là xác minh THẬT (gọi facilitator qua một client được
   inject, không bao giờ gọi mạng thật trong test) -- và không có nhánh nào
   trả `is_valid=True` mà không đi qua một câu trả lời facilitator giả lập
   nói `isValid: true`. Mọi nhánh lỗi/từ chối khác đều được test riêng.

`FakeFacilitator` dưới đây đứng thay cho `Agent.backend.okx.client.OkxClient`
qua tham số `facilitator_client=` của `verify_payment()` -- test không bao
giờ chạm mạng thật, và không cần mock `urllib`/`OkxClient` nội bộ.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Tuple

import pytest

from Agent.backend.okx.client import (
    OkxApiError,
    OkxCredentialsMissing,
    OkxTransportError,
)
from Agent.backend.payments import x402


@pytest.fixture(autouse=True)
def _clear_replay_guard():
    """The replay guard is process-wide, in-memory state (see
    `x402.reset_replay_guard_for_tests` docstring) -- without this, one
    test's "already used" fingerprint could leak into the next test that
    happens to build the same PaymentPayload bytes."""
    x402.reset_replay_guard_for_tests()
    yield
    x402.reset_replay_guard_for_tests()


class FakeFacilitator:
    """Stand-in for `OkxClient` in `verify_payment(facilitator_client=...)`.

    Records every call (`self.calls`) so a test can assert the facilitator
    was (or, for a locally-rejected request, was NOT) actually invoked --
    important for proving that a requirements-mismatch or replay never even
    reaches the network.
    """

    def __init__(
        self,
        response: Any = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: List[Tuple[str, Optional[Dict[str, Any]]]] = []

    def post(self, request_path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        self.calls.append((request_path, body))
        if self.error is not None:
            raise self.error
        return self.response


# ---------------------------------------------------------------------------
# 1. Mặc định tắt / feature flag
# ---------------------------------------------------------------------------


def test_x402_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("X402_ENABLED", raising=False)
    assert x402.is_x402_enabled() is False


@pytest.mark.parametrize("raw", ["false", "0", "no", "", "anything-not-true-like"])
def test_x402_stays_disabled_for_falsy_values(
    monkeypatch: pytest.MonkeyPatch, raw: str
):
    monkeypatch.setenv("X402_ENABLED", raw)
    assert x402.is_x402_enabled() is False


def test_x402_enabled_when_env_var_true(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("X402_ENABLED", "true")
    assert x402.is_x402_enabled() is True


def test_importing_module_requires_no_env_vars(monkeypatch: pytest.MonkeyPatch):
    """Import-time side effects would break every other test in this repo
    that doesn't know about x402 -- this module must have none."""
    for name in (
        "X402_ENABLED",
        "X402_NETWORK",
        "X402_PAY_TO_ADDRESS",
        "X402_ASSET_ADDRESS",
        "OKX_X402_API_KEY",
        "OKX_X402_API_SECRET",
        "OKX_X402_API_PASSPHRASE",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = x402.X402Settings.from_env()
    assert settings.enabled is False
    assert settings.network == x402.DEFAULT_NETWORK
    assert settings.pay_to_address == ""
    assert settings.missing_for_real_payments == [
        "X402_PAY_TO_ADDRESS",
        "X402_ASSET_ADDRESS",
        "OKX_X402_API_KEY",
        "OKX_X402_API_SECRET",
        "OKX_X402_API_PASSPHRASE",
    ]


def test_okx_sdk_available_never_raises():
    # Whatever the real answer is in this environment, calling it must be safe.
    assert x402.okx_sdk_available() in (True, False)


# ---------------------------------------------------------------------------
# 2. Bảng giá theo tool
# ---------------------------------------------------------------------------

EXPECTED_TOOL_NAMES = {
    "list_assets",
    "list_bots",
    "list_assessed_bots",
    "get_assessment",
    "assess_bot",
    "get_market",
}


def test_tool_pricing_covers_exactly_the_six_mcp_tools():
    assert set(x402.TOOL_PRICING) == EXPECTED_TOOL_NAMES


def test_every_declared_price_is_a_valid_money_string():
    for name, spec in x402.TOOL_PRICING.items():
        atomic = x402.usd_price_to_atomic_amount(spec.usd_price)
        assert atomic.isdigit(), f"{name}: {spec.usd_price!r} -> {atomic!r}"
        assert int(atomic) > 0


def test_assess_bot_is_priced_far_above_the_cache_read_tools():
    """assess_bot runs a live Monte Carlo pipeline (1.5-4.76s measured in
    Agent/docs/mcp_server.md); the lookup tools just read small cached JSON
    files. The price table must reflect that cost gap, not charge them the
    same."""
    cheap = int(
        x402.usd_price_to_atomic_amount(x402.TOOL_PRICING["list_assets"].usd_price)
    )
    expensive = int(
        x402.usd_price_to_atomic_amount(x402.TOOL_PRICING["assess_bot"].usd_price)
    )
    assert expensive >= cheap * 10


# ---------------------------------------------------------------------------
# usd_price_to_atomic_amount
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "usd_price,decimals,expected",
    [
        ("$0.01", 6, "10000"),
        ("$0.05", 6, "50000"),
        ("$1", 6, "1000000"),
        ("0.001", 6, "1000"),
        ("$0", 6, "0"),
        ("$0.01", 2, "1"),
    ],
)
def test_usd_price_to_atomic_amount_exact_values(usd_price, decimals, expected):
    assert x402.usd_price_to_atomic_amount(usd_price, decimals) == expected


def test_usd_price_to_atomic_amount_rejects_garbage():
    with pytest.raises(ValueError):
        x402.usd_price_to_atomic_amount("not-a-number")


def test_usd_price_to_atomic_amount_rejects_negative():
    with pytest.raises(ValueError):
        x402.usd_price_to_atomic_amount("-$0.01")


# ---------------------------------------------------------------------------
# build_payment_requirements / build_402_response
# ---------------------------------------------------------------------------


def _configured_settings(**overrides) -> x402.X402Settings:
    base = dict(
        enabled=True,
        network=x402.DEFAULT_NETWORK,
        scheme=x402.DEFAULT_SCHEME,
        pay_to_address="0x000000000000000000000000000000000000AA",
        asset_address="0x000000000000000000000000000000000000BB",
        asset_decimals=6,
        facilitator_base_url="https://web3.okx.com",
        okx_api_key="",
        okx_api_secret="",
        okx_api_passphrase="",
    )
    base.update(overrides)
    return x402.X402Settings(**base)


def test_build_payment_requirements_fails_loudly_without_pay_to_address():
    settings = _configured_settings(pay_to_address="")
    with pytest.raises(ValueError, match="X402_PAY_TO_ADDRESS"):
        x402.build_payment_requirements("get_market", settings=settings)


def test_build_payment_requirements_fails_loudly_without_asset_address():
    settings = _configured_settings(asset_address="")
    with pytest.raises(ValueError, match="X402_ASSET_ADDRESS"):
        x402.build_payment_requirements("get_market", settings=settings)


def test_build_payment_requirements_rejects_unknown_tool():
    settings = _configured_settings()
    with pytest.raises(ValueError, match="assess_bott"):
        x402.build_payment_requirements("assess_bott", settings=settings)


def test_build_payment_requirements_matches_wire_shape():
    settings = _configured_settings()
    req = x402.build_payment_requirements("assess_bot", settings=settings)

    assert req.scheme == "exact"
    assert req.network == x402.DEFAULT_NETWORK
    assert req.pay_to == settings.pay_to_address
    assert req.asset == settings.asset_address
    assert req.amount == x402.usd_price_to_atomic_amount(
        x402.TOOL_PRICING["assess_bot"].usd_price, settings.asset_decimals
    )
    assert req.max_timeout_seconds == x402.DEFAULT_MAX_TIMEOUT_SECONDS

    as_dict = req.to_dict()
    # Wire format is camelCase, matching okxweb3-app-x402's PaymentRequirements.
    assert set(as_dict) == {
        "scheme",
        "network",
        "asset",
        "amount",
        "payTo",
        "maxTimeoutSeconds",
        "extra",
    }
    assert as_dict["payTo"] == settings.pay_to_address
    assert as_dict["maxTimeoutSeconds"] == x402.DEFAULT_MAX_TIMEOUT_SECONDS


def test_build_402_response_shape_and_header():
    settings = _configured_settings()
    response = x402.build_402_response(
        "get_market", "mcp://okx-risk-supervisor/get_market", settings=settings
    )

    assert response["status"] == 402
    assert response["headers"]["Content-Type"] == "application/json"
    header_value = response["headers"][x402.PAYMENT_REQUIRED_HEADER]

    # Decode the header exactly the way a real client would, independent of
    # this module's own encode_header() helper, to prove the wire bytes
    # themselves are right -- not just that encode/decode are internally
    # consistent with each other.
    decoded = json.loads(base64.b64decode(header_value.encode("ascii")).decode("utf-8"))
    assert decoded["x402Version"] == 2
    assert len(decoded["accepts"]) == 1
    accepted = decoded["accepts"][0]
    assert accepted["scheme"] == "exact"
    assert accepted["network"] == x402.DEFAULT_NETWORK
    assert accepted["payTo"] == settings.pay_to_address
    assert accepted["asset"] == settings.asset_address
    assert accepted["amount"] == x402.usd_price_to_atomic_amount(
        x402.TOOL_PRICING["get_market"].usd_price, settings.asset_decimals
    )
    assert decoded["resource"]["url"] == "mcp://okx-risk-supervisor/get_market"


def test_build_402_response_propagates_configuration_errors():
    settings = _configured_settings(pay_to_address="")
    with pytest.raises(ValueError):
        x402.build_402_response("get_market", "mcp://x/get_market", settings=settings)


# ---------------------------------------------------------------------------
# PaymentPayload.decode_header -- structural parsing of untrusted input
# ---------------------------------------------------------------------------


def _encode_payload_header(data: dict) -> str:
    raw = json.dumps(data).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _sample_requirements_dict() -> dict:
    return {
        "scheme": "exact",
        "network": x402.DEFAULT_NETWORK,
        "asset": "0x000000000000000000000000000000000000BB",
        "amount": "10000",
        "payTo": "0x000000000000000000000000000000000000AA",
        "maxTimeoutSeconds": 60,
        "extra": {},
    }


def test_decode_header_round_trip():
    header = _encode_payload_header(
        {
            "x402Version": 2,
            "payload": {"signature": "0xdeadbeef"},
            "accepted": _sample_requirements_dict(),
        }
    )
    decoded = x402.PaymentPayload.decode_header(header)
    assert decoded.x402_version == 2
    assert decoded.payload == {"signature": "0xdeadbeef"}
    assert decoded.accepted.scheme == "exact"
    assert decoded.accepted.pay_to == "0x000000000000000000000000000000000000AA"


def test_decode_header_rejects_non_base64():
    with pytest.raises(ValueError):
        x402.PaymentPayload.decode_header("not-valid-base64-!!!")


def test_decode_header_rejects_base64_non_json():
    garbage = base64.b64encode(b"not json at all").decode("ascii")
    with pytest.raises(ValueError):
        x402.PaymentPayload.decode_header(garbage)


def test_decode_header_rejects_missing_accepted_field():
    header = _encode_payload_header({"x402Version": 2, "payload": {}})
    with pytest.raises(ValueError, match="accepted"):
        x402.PaymentPayload.decode_header(header)


def test_decode_header_rejects_empty_string():
    with pytest.raises(ValueError):
        x402.PaymentPayload.decode_header("")


# ---------------------------------------------------------------------------
# 3. verify_payment -- real verification, never a fake True
# ---------------------------------------------------------------------------


def _full_settings(**overrides) -> x402.X402Settings:
    """A fully-configured settings object: wallet/asset AND facilitator
    credentials all present, the precondition for verify_payment() to reach
    the facilitator call at all."""
    return _configured_settings(
        okx_api_key="merchant-key",
        okx_api_secret="merchant-secret",
        okx_api_passphrase="merchant-pass",
        **overrides,
    )


def _header_for(requirements: x402.PaymentRequirements, **payload_overrides) -> str:
    body = {
        "x402Version": 2,
        "payload": {"signature": "0xdeadbeef", **payload_overrides},
        "accepted": requirements.to_dict(),
    }
    return _encode_payload_header(body)


def test_verify_payment_raises_when_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("X402_ENABLED", raising=False)
    requirements = x402.PaymentRequirements.from_dict(_sample_requirements_dict())

    with pytest.raises(RuntimeError, match="X402_ENABLED"):
        x402.verify_payment("irrelevant", requirements)


def test_verify_payment_raises_without_header_when_enabled():
    settings = _configured_settings()
    requirements = x402.PaymentRequirements.from_dict(_sample_requirements_dict())

    with pytest.raises(ValueError, match="PAYMENT-SIGNATURE"):
        x402.verify_payment(None, requirements, settings=settings)

    with pytest.raises(ValueError, match="PAYMENT-SIGNATURE"):
        x402.verify_payment("", requirements, settings=settings)


def test_verify_payment_raises_on_malformed_header():
    settings = _configured_settings()
    requirements = x402.PaymentRequirements.from_dict(_sample_requirements_dict())

    with pytest.raises(ValueError):
        x402.verify_payment("not-base64-!!!", requirements, settings=settings)


# --- Thiếu credential merchant: PHẢI ném lỗi, không bao giờ cho qua --------


def test_verify_payment_raises_config_error_when_okx_credentials_missing():
    settings = _configured_settings(
        okx_api_key="", okx_api_secret="", okx_api_passphrase=""
    )
    requirements = x402.build_payment_requirements("get_market", settings)
    header = _header_for(requirements)

    with pytest.raises(x402.X402ConfigError) as excinfo:
        x402.verify_payment(header, requirements, settings=settings)

    message = str(excinfo.value)
    assert "OKX_X402_API_KEY" in message
    assert "OKX_X402_API_SECRET" in message
    assert "OKX_X402_API_PASSPHRASE" in message
    assert "TUYỆT ĐỐI không được coi như đã thanh toán" in message


def test_verify_payment_raises_config_error_when_wallet_not_configured():
    """Merchant creds present but no payTo/asset -- build_payment_requirements
    itself already refuses (tested elsewhere); this test is the corresponding
    guarantee at the verify_payment layer using a requirements object built
    by hand, in case a caller ever constructs one without going through
    build_payment_requirements()."""
    settings = _configured_settings(
        okx_api_key="k",
        okx_api_secret="s",
        okx_api_passphrase="p",
        pay_to_address="",
        asset_address="",
    )
    requirements = x402.PaymentRequirements.from_dict(_sample_requirements_dict())
    header = _header_for(requirements)

    with pytest.raises(x402.X402ConfigError):
        x402.verify_payment(header, requirements, settings=settings)


def test_verify_payment_never_calls_facilitator_when_config_missing():
    settings = _configured_settings(
        okx_api_key="", okx_api_secret="", okx_api_passphrase=""
    )
    requirements = x402.build_payment_requirements("get_market", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(response={"isValid": True, "payer": "0xabc"})

    with pytest.raises(x402.X402ConfigError):
        x402.verify_payment(
            header, requirements, settings=settings, facilitator_client=fake
        )

    assert fake.calls == []


# --- Facilitator timeout / lỗi / trả không hợp lệ: PHẢI ném lỗi -----------


def test_verify_payment_raises_on_facilitator_transport_error():
    """Network unreachable / timeout -- OkxClient surfaces this as
    OkxTransportError after its own retries; verify_payment must turn that
    into a raise, never a silent pass."""
    settings = _full_settings()
    requirements = x402.build_payment_requirements("assess_bot", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(error=OkxTransportError("Không kết nối được tới OKX"))

    with pytest.raises(x402.X402FacilitatorError, match="mạng lỗi hoặc timeout"):
        x402.verify_payment(
            header, requirements, settings=settings, facilitator_client=fake
        )


def test_verify_payment_raises_on_facilitator_api_error():
    """Facilitator answered but rejected the request at the OKX-envelope
    level (code != '0') -- an API-level failure, not a payment denial."""
    settings = _full_settings()
    requirements = x402.build_payment_requirements("assess_bot", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(error=OkxApiError("50111", "invalid signature"))

    with pytest.raises(x402.X402FacilitatorError):
        x402.verify_payment(
            header, requirements, settings=settings, facilitator_client=fake
        )


def test_verify_payment_raises_on_facilitator_credentials_missing_error():
    """Defense in depth: even if a caller-supplied facilitator_client somehow
    raises OkxCredentialsMissing (shouldn't happen -- verify_payment already
    checked settings.missing_for_real_payments), it must still be a raise,
    not a fallthrough."""
    settings = _full_settings()
    requirements = x402.build_payment_requirements("assess_bot", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(error=OkxCredentialsMissing("thiếu credential"))

    with pytest.raises(x402.X402ConfigError):
        x402.verify_payment(
            header, requirements, settings=settings, facilitator_client=fake
        )


@pytest.mark.parametrize(
    "malformed_response",
    [
        {},  # no isValid at all
        {"isValid": "true"},  # truthy string, not a real bool
        {"isValid": 1},  # truthy int, not a real bool
        {"data": {"nope": "not the right shape"}},
        None,
        "a bare string, not even a dict",
        {"code": "0", "data": "not-a-dict", "msg": ""},
    ],
)
def test_verify_payment_raises_on_malformed_facilitator_response(malformed_response):
    settings = _full_settings()
    requirements = x402.build_payment_requirements("get_market", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(response=malformed_response)

    with pytest.raises(x402.X402FacilitatorError, match="isValid"):
        x402.verify_payment(
            header, requirements, settings=settings, facilitator_client=fake
        )


# --- Sai số tiền / network / địa chỉ nhận: từ chối cục bộ, KHÔNG gọi mạng -


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("amount", "999999999"),
        ("network", "eip155:1"),
        ("asset", "0x000000000000000000000000000000000000CC"),
        ("payTo", "0x000000000000000000000000000000000000CC"),
        ("scheme", "upto"),
    ],
)
def test_verify_payment_rejects_mismatched_field_without_calling_facilitator(
    field, bad_value
):
    settings = _full_settings()
    requirements = x402.build_payment_requirements("get_market", settings)
    claimed = requirements.to_dict()
    claimed[field] = bad_value
    header = _encode_payload_header(
        {"x402Version": 2, "payload": {"signature": "0xdeadbeef"}, "accepted": claimed}
    )
    fake = FakeFacilitator(response={"isValid": True, "payer": "0xabc"})

    result = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=fake
    )

    assert result.is_valid is False
    assert result.invalid_reason == "requirements_mismatch"
    assert fake.calls == [], "a mismatched claim must never reach the facilitator"


# --- Facilitator xác nhận: verify đạt -------------------------------------


def test_verify_payment_succeeds_when_facilitator_confirms():
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(response={"isValid": True, "payer": "0xPAYER"})

    result = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=fake
    )

    assert result.is_valid is True
    assert result.payer == "0xPAYER"
    assert fake.calls[0][0] == x402.FACILITATOR_VERIFY_PATH
    sent_body = fake.calls[0][1]
    assert sent_body["x402Version"] == 2
    assert sent_body["paymentRequirements"] == requirements.to_dict()


def test_verify_payment_succeeds_with_okx_envelope_shaped_response():
    """Facilitator response wrapped in OKX's own {code, data, msg} envelope
    (what OkxClient._send already unwraps for a 'code' key present, but a
    caller-supplied facilitator_client might return the raw envelope) --
    accepted the same way as a bare VerifyResponse."""
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(
        response={"code": "0", "msg": "", "data": {"isValid": True, "payer": "0xPAYER"}}
    )

    result = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=fake
    )
    assert result.is_valid is True


def test_verify_payment_returns_denied_when_facilitator_says_invalid():
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header = _header_for(requirements)
    fake = FakeFacilitator(
        response={
            "isValid": False,
            "invalidReason": "expired",
            "invalidMessage": "signature expired",
        }
    )

    result = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=fake
    )

    assert result.is_valid is False
    assert result.invalid_reason == "expired"
    assert result.invalid_message == "signature expired"


# --- Chống phát lại (replay) ------------------------------------------------


def test_verify_payment_rejects_replay_of_the_same_proof():
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header = _header_for(requirements)

    first = FakeFacilitator(response={"isValid": True, "payer": "0xPAYER"})
    result1 = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=first
    )
    assert result1.is_valid is True

    # Same exact PAYMENT-SIGNATURE header again -- even though this second
    # facilitator would also say "valid", the local replay guard must reject
    # it before ever calling out.
    second = FakeFacilitator(response={"isValid": True, "payer": "0xPAYER"})
    result2 = x402.verify_payment(
        header, requirements, settings=settings, facilitator_client=second
    )

    assert result2.is_valid is False
    assert result2.invalid_reason == "replay"
    assert second.calls == [], "a replayed proof must never reach the facilitator"


def test_verify_payment_different_proofs_are_independent():
    """Sanity check on the fingerprinting: two distinct payloads (different
    signature bytes) must not collide in the replay guard."""
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header_a = _header_for(requirements, signature="0xaaaa")
    header_b = _header_for(requirements, signature="0xbbbb")

    result_a = x402.verify_payment(
        header_a,
        requirements,
        settings=settings,
        facilitator_client=FakeFacilitator(response={"isValid": True, "payer": "0xA"}),
    )
    result_b = x402.verify_payment(
        header_b,
        requirements,
        settings=settings,
        facilitator_client=FakeFacilitator(response={"isValid": True, "payer": "0xB"}),
    )
    assert result_a.is_valid is True
    assert result_b.is_valid is True


def test_reset_replay_guard_for_tests_actually_clears_state():
    settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", settings)
    header = _header_for(requirements)

    x402.verify_payment(
        header,
        requirements,
        settings=settings,
        facilitator_client=FakeFacilitator(response={"isValid": True, "payer": "0xA"}),
    )
    x402.reset_replay_guard_for_tests()
    # After an explicit reset, the exact same proof must be usable again --
    # proves the guard was really cleared, not just "hasn't expired yet".
    result = x402.verify_payment(
        header,
        requirements,
        settings=settings,
        facilitator_client=FakeFacilitator(response={"isValid": True, "payer": "0xA"}),
    )
    assert result.is_valid is True


# --- Meta test: mọi nhánh, không nhánh nào "đã trả tiền" mà thiếu xác nhận -


def test_verify_payment_exhaustive_branches_never_fake_a_paid_result():
    """Enumerates every reachable branch in verify_payment() and asserts
    each one is EITHER a raise OR a `VerifyResult(is_valid=False, ...)` --
    with exactly one exception, the final "facilitator confirms" branch,
    which is the only branch allowed to produce `is_valid=True`, and only
    because a facilitator call (here, a `FakeFacilitator`) was mocked to
    explicitly say so.
    """
    good_settings = _full_settings()
    requirements = x402.build_payment_requirements("list_assets", good_settings)

    branches: list = []

    # 1. Disabled.
    branches.append(
        (
            lambda: x402.verify_payment(
                "x", requirements, settings=_configured_settings(enabled=False)
            ),
            "raises",
        )
    )
    # 2. No header.
    branches.append(
        (
            lambda: x402.verify_payment(None, requirements, settings=good_settings),
            "raises",
        )
    )
    # 3. Malformed header.
    branches.append(
        (
            lambda: x402.verify_payment(
                "garbage", requirements, settings=good_settings
            ),
            "raises",
        )
    )
    # 4. Missing merchant config.
    branches.append(
        (
            lambda: x402.verify_payment(
                _header_for(requirements),
                requirements,
                settings=_configured_settings(),  # no okx_* creds
            ),
            "raises",
        )
    )
    # 5. Requirements mismatch (never calls facilitator).
    mismatched = requirements.to_dict()
    mismatched["amount"] = "1"
    mismatch_header = _encode_payload_header(
        {"x402Version": 2, "payload": {"signature": "0xm"}, "accepted": mismatched}
    )
    branches.append(
        (
            lambda: x402.verify_payment(
                mismatch_header,
                requirements,
                settings=good_settings,
                facilitator_client=FakeFacilitator(response={"isValid": True}),
            ),
            "denied",
        )
    )
    # 6. Facilitator transport error.
    branches.append(
        (
            lambda: x402.verify_payment(
                _header_for(requirements, signature="0x6"),
                requirements,
                settings=good_settings,
                facilitator_client=FakeFacilitator(error=OkxTransportError("timeout")),
            ),
            "raises",
        )
    )
    # 7. Facilitator malformed response.
    branches.append(
        (
            lambda: x402.verify_payment(
                _header_for(requirements, signature="0x7"),
                requirements,
                settings=good_settings,
                facilitator_client=FakeFacilitator(response={}),
            ),
            "raises",
        )
    )
    # 8. Facilitator explicitly denies.
    branches.append(
        (
            lambda: x402.verify_payment(
                _header_for(requirements, signature="0x8"),
                requirements,
                settings=good_settings,
                facilitator_client=FakeFacilitator(
                    response={"isValid": False, "invalidReason": "bad_signature"}
                ),
            ),
            "denied",
        )
    )
    # 9. The ONLY branch allowed to produce is_valid=True: facilitator
    #    explicitly confirms.
    branches.append(
        (
            lambda: x402.verify_payment(
                _header_for(requirements, signature="0x9"),
                requirements,
                settings=good_settings,
                facilitator_client=FakeFacilitator(
                    response={"isValid": True, "payer": "0xreal"}
                ),
            ),
            "paid",
        )
    )

    saw_a_paid_result = False
    for scenario, expected in branches:
        x402.reset_replay_guard_for_tests()
        if expected == "raises":
            with pytest.raises((RuntimeError, ValueError)):
                scenario()
            continue
        result = scenario()
        if expected == "denied":
            assert result.is_valid is False
        elif expected == "paid":
            assert result.is_valid is True
            saw_a_paid_result = True

    # Sanity on the test itself: prove branch 9 really did exercise the
    # is_valid=True path, so this test can't pass vacuously.
    assert saw_a_paid_result
