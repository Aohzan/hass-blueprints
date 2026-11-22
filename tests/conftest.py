"""Fixtures to run the blueprints in a Home Assistant test instance."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import asyncio
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockUser,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

BLUEPRINTS_DIR = Path(__file__).parent.parent / "blueprints"
PUSH_URL = "https://mobile-push.home-assistant.dev/push"


@pytest.fixture
async def blueprints_config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Expose the repository blueprints as `Aohzan/<file>` in a config dir."""
    target = tmp_path / "blueprints" / "automation" / "Aohzan"
    shutil.copytree(BLUEPRINTS_DIR, target)
    hass.config.config_dir = str(tmp_path)
    return target


class Phones:
    """Mocked Companion app devices, recording the pushed notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        aioclient_mock: AiohttpClientMocker,
        user: MockUser,
    ) -> None:
        self._hass = hass
        self._aioclient_mock = aioclient_mock
        self._user = user
        self._count = 0
        aioclient_mock.post(
            PUSH_URL,
            json={
                "rateLimits": {
                    "attempts": 1,
                    "successful": 1,
                    "errors": 0,
                    "total": 1,
                    "maximum": 150,
                    "remaining": 149,
                    "resetsAt": "2099-01-01T00:00:00Z",
                }
            },
        )

    async def add(self, name: str, os_name: str = "Android") -> str:
        """Register a phone and return its device id."""
        self._count += 1
        entry = MockConfigEntry(
            domain="mobile_app",
            source="registration",
            title=name,
            version=1,
            data={
                "app_data": {"push_token": f"token-{name}", "push_url": PUSH_URL},
                "app_id": "io.homeassistant.mobile_app",
                "app_name": "Home Assistant",
                "app_version": "1.0",
                "device_id": f"device-{name}",
                "device_name": name,
                "manufacturer": "Test",
                "model": "Test",
                "os_name": os_name,
                "os_version": "1",
                "secret": f"secret-{name}",
                "supports_encryption": False,
                "user_id": self._user.id,
                "webhook_id": f"webhook-{name}",
            },
        )
        entry.add_to_hass(self._hass)
        if self._count == 1:
            assert await async_setup_component(self._hass, "mobile_app", {})
        else:
            assert await self._hass.config_entries.async_setup(entry.entry_id)
        await self._hass.async_block_till_done()
        [device] = dr.async_entries_for_config_entry(
            dr.async_get(self._hass), entry.entry_id
        )
        return device.id

    def pushes(self, tag: str | None = None) -> list[dict[str, Any]]:
        """Notifications pushed so far, optionally only those with this tag."""
        payloads = [
            call[2] if isinstance(call[2], dict) else json.loads(call[2])
            for call in self._aioclient_mock.mock_calls
            if str(call[1]) == PUSH_URL
        ]
        return [p for p in payloads if tag is None or p["data"].get("tag") == tag]


@pytest.fixture
async def phones(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_admin_user: MockUser,
) -> Phones:
    """Mocked Companion app devices."""
    return Phones(hass, aioclient_mock, hass_admin_user)


@pytest.fixture
def move_to(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> Callable[[str], Coroutine[Any, Any, None]]:
    """Move the clock to a local `YYYY-MM-DD HH:MM:SS` and fire the timers."""

    async def _move_to(local: str) -> None:
        moment = datetime.fromisoformat(local).replace(
            tzinfo=ZoneInfo(hass.config.time_zone)
        )
        freezer.move_to(moment)
        async_fire_time_changed(hass, moment)
        await settle()

    return _move_to


async def settle() -> None:
    """Let the automations run until they wait for something.

    `hass.async_block_till_done()` would wait forever for a reminder waiting
    for an answer.
    """
    for _ in range(100):
        await asyncio.sleep(0)


@pytest.fixture
def expected_lingering_timers() -> bool:
    """The time trigger of the automations keeps a timer for the next day."""
    return True


@pytest.fixture
def expected_lingering_tasks() -> bool:
    """A reminder still waiting for an answer at the end of a test."""
    return True
