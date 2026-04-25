# -*- coding: utf-8 -*-
"""Static residue guards for the KR/US migration baseline."""

from tests.kr_us_static_guard import scan_paths, scan_repository


def test_repository_has_no_unapproved_kr_us_migration_residue():
    """Active project files must not reintroduce removed China/service residue."""
    assert scan_repository() == []


def test_guard_detects_synthetic_residue(tmp_path):
    """The static guard must flag synthetic service, market, and Han text residue."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        'LEGACY = "TUSHARE_TOKEN SH600518 \u4e0a\u8bc1"\n',  # kr-us-static-allow: removed-service, removed-market
        encoding="utf-8",
    )

    offenders = scan_paths(tmp_path, [sample])

    assert any(":removed-service:" in offender for offender in offenders)
    assert any(":removed-market:" in offender for offender in offenders)
    assert any(":han-text:" in offender for offender in offenders)


def test_inline_allow_marker_does_not_hide_unmarked_residue(tmp_path):
    """Inline allow markers must not suppress unrelated residue in the same file."""
    registry = tmp_path / "src" / "core" / "config_registry.py"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "\n".join(
            [
                '"TUSHARE_",  # kr-us-static-allow: removed-service',
                '"TUSHARE_ACTIVE_FIELD",',  # kr-us-static-allow: removed-service
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    offenders = scan_paths(tmp_path, [registry])

    assert offenders == [  # kr-us-static-allow: removed-service
        'src/core/config_registry.py:2:removed-service:"TUSHARE_ACTIVE_FIELD",'  # kr-us-static-allow: removed-service
    ]


def test_guard_detects_camel_case_service_residue_without_common_false_positive(tmp_path):
    """Removed-service detection must catch class-style names without matching unrelated prefixes."""
    sample = tmp_path / "services.py"
    sample.write_text(
        "\n".join(
            [
                "class FeishuSender: pass",  # kr-us-static-allow: removed-service
                "TushareToken = 'x'",  # kr-us-static-allow: removed-service
                "AKSHAREFetcher = object()",  # kr-us-static-allow: removed-service
                "serverchannel_note = 'allowed'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    offenders = scan_paths(tmp_path, [sample])

    assert offenders == [
        "services.py:1:removed-service:class FeishuSender: pass",  # kr-us-static-allow: removed-service
        "services.py:2:removed-service:TushareToken = 'x'",  # kr-us-static-allow: removed-service
        "services.py:3:removed-service:AKSHAREFetcher = object()",  # kr-us-static-allow: removed-service
    ]


def test_guard_detects_embedded_snake_case_service_residue(tmp_path):
    """Removed-service detection must catch snake_case names while avoiding similar words."""
    sample = tmp_path / "services.py"
    sample.write_text(
        "\n".join(
            [
                "legacy_wechat_sender = object()",  # kr-us-static-allow: removed-service
                "send_tushare_report = object()",  # kr-us-static-allow: removed-service
                "my_tushare_token = 'x'",  # kr-us-static-allow: removed-service
                "serverchannel_note = 'allowed'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    offenders = scan_paths(tmp_path, [sample])

    assert offenders == [
        "services.py:1:removed-service:legacy_wechat_sender = object()",  # kr-us-static-allow: removed-service
        "services.py:2:removed-service:send_tushare_report = object()",  # kr-us-static-allow: removed-service
        "services.py:3:removed-service:my_tushare_token = 'x'",  # kr-us-static-allow: removed-service
    ]


def test_guard_detects_case_insensitive_legacy_hk_prefix(tmp_path):
    """Legacy prefixed market codes should be blocked regardless of letter case."""
    sample = tmp_path / "market.py"
    sample.write_text('"hk00700"\n', encoding="utf-8")  # kr-us-static-allow: removed-market

    offenders = scan_paths(tmp_path, [sample])

    assert offenders == [
        'market.py:1:removed-market:"hk00700"',  # kr-us-static-allow: removed-market
    ]
