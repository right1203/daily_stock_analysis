# -*- coding: utf-8 -*-
"""Unit tests for system configuration service."""

import os
import tempfile
import unittest
from pathlib import Path

from src.config import Config
from src.core.config_manager import ConfigManager
from src.services.system_config_service import ConfigConflictError, SystemConfigService


class SystemConfigServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text(
            "\n".join(
                [
                    "STOCK_LIST=005930,035720",
                    "GEMINI_API_KEY=secret-key-value",
                    "SCHEDULE_TIME=18:00",
                    "LOG_LEVEL=INFO",
                    "TUSHARE_TOKEN=legacy-token",  # kr-us-static-allow: removed-service
                    "WECHAT_WEBHOOK_URL=https://example.com/wechat",  # kr-us-static-allow: removed-service
                    "WECOM_CORPID=legacy-corpid",  # kr-us-static-allow: removed-service
                    "WECOM_TOKEN=legacy-token",  # kr-us-static-allow: removed-service
                    "WECOM_AES_KEY=legacy-aes-key",  # kr-us-static-allow: removed-service
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        os.environ["ENV_FILE"] = str(self.env_path)
        Config.reset_instance()

        self.manager = ConfigManager(env_path=self.env_path)
        self.service = SystemConfigService(manager=self.manager)

    def tearDown(self) -> None:
        Config.reset_instance()
        os.environ.pop("ENV_FILE", None)
        self.temp_dir.cleanup()

    def test_get_config_returns_raw_sensitive_values(self) -> None:
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertIn("GEMINI_API_KEY", items)
        self.assertEqual(items["GEMINI_API_KEY"]["value"], "secret-key-value")
        self.assertFalse(items["GEMINI_API_KEY"]["is_masked"])
        self.assertTrue(items["GEMINI_API_KEY"]["raw_value_exists"])

    def test_get_config_excludes_removed_china_service_fields(self) -> None:
        payload = self.service.get_config(include_schema=True)
        item_keys = {item["key"] for item in payload["items"]}

        self.assertNotIn("TUSHARE_TOKEN", item_keys)  # kr-us-static-allow: removed-service
        self.assertNotIn("WECHAT_WEBHOOK_URL", item_keys)  # kr-us-static-allow: removed-service
        self.assertNotIn("WECOM_CORPID", item_keys)  # kr-us-static-allow: removed-service
        self.assertNotIn("WECOM_TOKEN", item_keys)  # kr-us-static-allow: removed-service
        self.assertNotIn("WECOM_AES_KEY", item_keys)  # kr-us-static-allow: removed-service

    def test_get_config_exposes_retained_astrbot_fields_by_default(self) -> None:
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertIn("ASTRBOT_URL", items)
        self.assertIn("ASTRBOT_TOKEN", items)
        self.assertEqual(items["ASTRBOT_URL"]["schema"]["category"], "notification")
        self.assertEqual(items["ASTRBOT_TOKEN"]["schema"]["ui_control"], "password")

    def test_validate_rejects_removed_prefixed_fields(self) -> None:
        validation = self.service.validate(
            items=[{"key": "WECOM_TOKEN", "value": "legacy-token"}]  # kr-us-static-allow: removed-service
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "WECOM_TOKEN"  # kr-us-static-allow: removed-service
                and issue["code"] == "removed_field"
                for issue in validation["issues"]
            )
        )

    def test_validate_rejects_removed_exact_field_but_allows_similar_unknown_prefix(self) -> None:
        removed = self.service.validate(
            items=[{"key": "SERVERCHAN3_SENDKEY", "value": "legacy-sendkey"}]  # kr-us-static-allow: removed-service
        )
        benign = self.service.validate(items=[{"key": "SERVERCHANNEL_INTERNAL_NOTE", "value": "keep"}])

        self.assertFalse(removed["valid"])
        self.assertTrue(any(issue["code"] == "removed_field" for issue in removed["issues"]))
        self.assertTrue(benign["valid"])
        self.assertEqual([], benign["issues"])

    def test_update_preserves_masked_secret(self) -> None:
        old_version = self.manager.get_config_version()
        response = self.service.update(
            config_version=old_version,
            items=[
                {"key": "GEMINI_API_KEY", "value": "******"},
                {"key": "STOCK_LIST", "value": "005930,MSFT"},
            ],
            mask_token="******",
            reload_now=False,
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["applied_count"], 1)
        self.assertEqual(response["skipped_masked_count"], 1)
        self.assertIn("STOCK_LIST", response["updated_keys"])

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["STOCK_LIST"], "005930,MSFT")
        self.assertEqual(current_map["GEMINI_API_KEY"], "secret-key-value")

    def test_validate_reports_invalid_time(self) -> None:
        validation = self.service.validate(items=[{"key": "SCHEDULE_TIME", "value": "25:70"}])
        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_format" for issue in validation["issues"]))

    def test_update_raises_conflict_for_stale_version(self) -> None:
        with self.assertRaises(ConfigConflictError):
            self.service.update(
                config_version="stale-version",
                items=[{"key": "STOCK_LIST", "value": "005930"}],
                reload_now=False,
            )


if __name__ == "__main__":
    unittest.main()
