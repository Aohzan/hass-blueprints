"""Tests of the medication reminder blueprint and its deprecated copies."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .conftest import Phones, settle

UNIFIED = "medication_reminder.yaml"
ALL_FILES = [
    UNIFIED,
    "medication_reminder_android.yaml",
    "medication_reminder_ios.yaml",
]

# 2026-11-22 is a Sunday.
BEFORE = "2026-11-22 07:59:58"
REMINDER = "2026-11-22 08:00:00"

MoveTo = Callable[[str], Coroutine[Any, Any, None]]


class Med:
    """One automation created from the blueprint, with its helpers."""

    def __init__(
        self, hass: HomeAssistant, phones: Phones, key: str, services: dict
    ) -> None:
        self.hass = hass
        self.phones = phones
        self.key = key
        self.boolean = f"input_boolean.{key}"
        self.datetime = f"input_datetime.{key}_last"
        self.automation = f"automation.{key}"
        self._services = services
        self._triggered = async_capture_events(hass, "automation_triggered")

    @property
    def is_on(self) -> bool:
        return self.hass.states.get(self.boolean).state == "on"

    @property
    def taken_now(self) -> bool:
        """Whether the last taken input_datetime is set to the current time."""
        state = self.hass.states.get(self.datetime)
        return state.attributes["timestamp"] == dt_util.now().replace(
            microsecond=0
        ).timestamp()

    @property
    def running(self) -> int:
        return self.hass.states.get(self.automation).attributes["current"]

    @property
    def runs(self) -> int:
        return sum(
            1 for e in self._triggered if e.data["entity_id"] == self.automation
        )

    def logbook(self) -> list[str]:
        return [
            c.data["message"]
            for c in self._services["logbook"]
            if c.data["entity_id"] == self.boolean
        ]

    def calls(self, name: str) -> int:
        """Number of runs of an action input (test.<name>) for this automation."""
        return sum(
            1 for c in self._services[name] if c.data.get("med") == self.key
        )

    def pushes(self) -> list[dict[str, Any]]:
        return self.phones.pushes(self.boolean)

    def notifications(self) -> list[dict[str, Any]]:
        """Pushed notifications, without the clear_notification commands."""
        return [p for p in self.pushes() if p["message"] != "clear_notification"]

    async def turn(self, service: str) -> None:
        await self.hass.services.async_call(
            "input_boolean", service, {"entity_id": self.boolean}, blocking=True
        )
        await settle()

    async def answer(self, title: str, notification: dict | None = None) -> None:
        """Press an action button of a notification (the last one by default)."""
        notification = notification or self.notifications()[-1]
        action = next(
            a["action"] for a in notification["data"]["actions"] if a["title"] == title
        )
        self.hass.bus.async_fire("mobile_app_notification_action", {"action": action})
        await settle()


@pytest.fixture
async def setup(
    hass: HomeAssistant, blueprints_config_dir, phones: Phones, move_to: MoveTo
):
    """Create automations from the blueprint: setup({key: inputs}, ...)."""
    await move_to(BEFORE)
    services = {
        name: async_mock_service(hass, "test", name)
        for name in ("remind", "taken", "skip", "no_answer")
    }
    services["logbook"] = async_mock_service(hass, "logbook", "log")
    services["notice"] = async_mock_service(hass, "persistent_notification", "create")
    android = await phones.add("android")
    ios = await phones.add("iphone", os_name="iOS")

    async def _setup(
        meds: dict[str, dict[str, Any]],
        blueprint: str = UNIFIED,
        booleans: tuple[str, ...] = (),
    ) -> dict[str, Med]:
        assert await async_setup_component(
            hass,
            "input_boolean",
            {"input_boolean": {key: {"name": key} for key in (*meds, *booleans)}},
        )
        assert await async_setup_component(
            hass,
            "input_datetime",
            {
                "input_datetime": {
                    f"{key}_last": {"has_date": True, "has_time": True}
                    for key in meds
                }
            },
        )
        automations = []
        for key, inputs in meds.items():
            inputs = {
                "reminder_time": "08:00:00",
                "notify_device": android,
                "input_boolean": f"input_boolean.{key}",
                "last_taken_datetime": f"input_datetime.{key}_last",
                **{
                    f"{name}_action": [
                        {"action": f"test.{name}", "data": {"med": key}}
                    ]
                    for name in ("taken", "skip", "no_answer")
                },
                "optional_action": [{"action": "test.remind", "data": {"med": key}}],
                **inputs,
            }
            if inputs["notify_device"] == "iphone":
                inputs["notify_device"] = ios
            inputs = {k: v for k, v in inputs.items() if v is not None}
            automations.append(
                {
                    "id": key,
                    "alias": key,
                    "use_blueprint": {"path": f"Aohzan/{blueprint}", "input": inputs},
                }
            )
        assert await async_setup_component(
            hass, "automation", {"automation": automations}
        )
        await hass.async_block_till_done()
        for key in meds:
            assert hass.states.get(f"automation.{key}").state == "on", key
        return {key: Med(hass, phones, key, services) for key in meds}

    return _setup


@pytest.mark.parametrize("blueprint", ALL_FILES)
async def test_turned_on_outside_a_reminder(hass, setup, blueprint) -> None:
    """Issue #19: turning the input_boolean on at any time counts as taken."""
    med = (await setup({"med": {}}, blueprint))["med"]

    await med.turn("turn_on")

    assert med.taken_now
    assert med.logbook() == ["Medication marked as taken"]
    assert med.calls("taken") == 1
    assert med.pushes() == []
    assert med.running == 0


async def test_turned_on_outside_a_reminder_minimal_config(hass, setup) -> None:
    """Only the required inputs: no input_datetime nor actions."""
    med = (
        await setup(
            {
                "med": {
                    "last_taken_datetime": None,
                    "taken_action": None,
                    "skip_action": None,
                    "no_answer_action": None,
                    "optional_action": None,
                }
            }
        )
    )["med"]

    await med.turn("turn_on")

    assert not med.taken_now
    assert med.logbook() == ["Medication marked as taken"]
    assert med.running == 0


async def test_turned_on_again_when_already_on(hass, setup) -> None:
    """No state change, nothing happens."""
    med = (await setup({"med": {}}))["med"]
    await med.turn("turn_on")

    await med.turn("turn_on")

    assert med.calls("taken") == 1


@pytest.mark.parametrize("blueprint", ALL_FILES)
async def test_taken_from_the_notification(hass, setup, move_to, blueprint) -> None:
    med = (await setup({"med": {}}, blueprint))["med"]
    await med.turn("turn_on")

    await move_to(REMINDER)

    assert not med.is_on
    assert med.running == 1
    assert med.calls("remind") == 1
    [notification] = med.notifications()
    assert notification["title"] == "Medication reminder!"
    assert notification["message"] == "It's time to take your medication"
    assert [a["title"] for a in notification["data"]["actions"]] == [
        "Taken",
        "Ask later",
        "Skip",
    ]

    await med.answer("Taken")

    assert med.is_on
    assert med.running == 0
    # One run when turned on before the reminder, one for the reminder:
    # turning the input_boolean on from the reminder must not restart it.
    assert med.runs == 2
    assert med.taken_now
    assert med.calls("taken") == 2
    assert med.logbook()[-2:] == ["Reminder sent", "Medication taken"]
    notices = [c.data["notification_id"] for c in med._services["notice"]]
    if blueprint == UNIFIED:
        assert notices == []
    else:
        assert "medication_reminder_deprecated_automation.med" in notices


async def test_custom_texts_and_android_options(hass, setup, move_to) -> None:
    med = (
        await setup(
            {
                "med": {
                    "notification_title": "Title",
                    "notification_message": "Message",
                    "notification_action_taken": "Pris",
                    "notification_action_later": "Plus tard",
                    "notification_action_skip": "Sauter",
                    "android_channel": "Pills",
                    "logbook_message_remind": "Rappel",
                    "logbook_message_taken": "Pris !",
                }
            }
        )
    )["med"]

    await move_to(REMINDER)

    [notification] = med.notifications()
    assert notification["title"] == "Title"
    assert notification["message"] == "Message"
    data = notification["data"]
    assert [a["title"] for a in data["actions"]] == ["Pris", "Plus tard", "Sauter"]
    assert data["channel"] == "Pills"
    assert data["importance"] == "high"
    assert data["priority"] == "high"
    assert data["ttl"] == 0
    assert data["push"]["interruption-level"] == "active"

    await med.answer("Pris")

    assert med.logbook() == ["Rappel", "Pris !"]


async def test_ios_interruption_level(hass, setup, move_to) -> None:
    med = (
        await setup(
            {"med": {"notify_device": "iphone", "ios_interruption_level": "critical"}}
        )
    )["med"]

    await move_to(REMINDER)

    [notification] = med.notifications()
    assert notification["push_token"] == "token-iphone"
    assert notification["data"]["push"]["interruption-level"] == "critical"
    await med.answer("Taken")
    assert med.is_on


async def test_skip(hass, setup, move_to) -> None:
    med = (await setup({"med": {}}))["med"]
    await move_to(REMINDER)

    await med.answer("Skip")

    assert med.is_on
    assert med.running == 0
    assert med.runs == 1
    assert not med.taken_now
    assert med.calls("skip") == 1
    assert med.calls("taken") == 0
    assert med.logbook() == ["Reminder sent", "Reminder skipped"]


async def test_turned_on_while_waiting_for_an_answer(hass, setup, move_to) -> None:
    med = (await setup({"med": {}}))["med"]
    await move_to(REMINDER)

    await med.turn("turn_on")

    assert med.running == 0
    assert med.runs == 1
    assert med.pushes()[-1]["message"] == "clear_notification"
    assert med.taken_now
    assert med.calls("taken") == 1
    assert med.logbook() == ["Reminder sent", "Medication marked as taken"]


async def test_ask_later(hass, setup, move_to) -> None:
    med = (await setup({"med": {"ask_later_wait_time": 10}}))["med"]
    await move_to(REMINDER)

    await med.answer("Ask later")
    await move_to("2026-11-22 08:09:59")
    assert len(med.notifications()) == 1

    await move_to("2026-11-22 08:10:01")
    assert len(med.notifications()) == 2
    assert med.calls("remind") == 2

    await med.answer("Taken")
    assert med.is_on
    assert med.running == 0
    assert med.runs == 1
    assert med.logbook() == [
        "Reminder sent",
        "Postpone reminder",
        "Reminder sent",
        "Medication taken",
    ]


async def test_ask_later_then_turned_on(hass, setup, move_to) -> None:
    med = (await setup({"med": {}}))["med"]
    await move_to(REMINDER)
    await med.answer("Ask later")

    await med.turn("turn_on")

    assert med.running == 0
    assert med.runs == 1
    assert med.taken_now
    assert med.calls("taken") == 1
    assert med.logbook()[-1] == "Medication marked as taken"


async def test_no_answer(hass, setup, move_to) -> None:
    med = (await setup({"med": {"ask_later_wait_time": 5}}))["med"]
    await move_to(REMINDER)

    await move_to("2026-11-22 08:05:01")

    assert [p["message"] for p in med.pushes()] == [
        "It's time to take your medication",
        "clear_notification",
        "It's time to take your medication",
    ]
    assert med.calls("no_answer") == 1
    assert med.logbook() == ["Reminder sent", "No answer time out", "Reminder sent"]

    await med.turn("turn_on")
    assert med.running == 0
    assert med.runs == 1
    assert med.calls("taken") == 1


async def test_weekday_not_selected(hass, setup, move_to) -> None:
    """No reminder on a day not selected, turning on still counts as taken."""
    med = (
        await setup({"med": {"weekdays": ["mon", "tue", "wed", "thu", "fri", "sat"]}})
    )["med"]

    await move_to(REMINDER)
    assert med.pushes() == []
    assert med.runs == 0

    await med.turn("turn_on")
    assert med.calls("taken") == 1


async def test_reminder_conditions(hass, setup, move_to) -> None:
    """No reminder when a condition fails, turning on still counts as taken."""
    condition = {"condition": "state", "entity_id": "input_boolean.flag", "state": "on"}
    meds = await setup({"med": {"reminder_conditions": [condition]}}, booleans=("flag",))
    med = meds["med"]

    await move_to(REMINDER)
    assert med.pushes() == []

    await med.turn("turn_on")
    assert med.calls("taken") == 1


async def test_reminder_conditions_pass(hass, setup, move_to) -> None:
    condition = {"condition": "state", "entity_id": "input_boolean.flag", "state": "on"}
    meds = await setup({"med": {"reminder_conditions": [condition]}}, booleans=("flag",))
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.flag"}, blocking=True
    )

    await move_to(REMINDER)

    assert len(meds["med"].notifications()) == 1


async def test_two_medications_on_the_same_phone(hass, setup, move_to) -> None:
    """Answering one notification does not answer the other one."""
    meds = await setup({"morning": {}, "vitamin": {}})
    await move_to(REMINDER)
    morning, vitamin = meds["morning"], meds["vitamin"]

    await morning.answer("Taken")

    assert morning.is_on
    assert not vitamin.is_on
    assert vitamin.running == 1
    assert not vitamin.taken_now

    await vitamin.answer("Skip")
    assert vitamin.is_on
    assert vitamin.calls("skip") == 1
    assert morning.calls("skip") == 0


async def test_answer_from_a_previous_run_is_ignored(hass, setup, move_to) -> None:
    med = (await setup({"med": {}}))["med"]
    await move_to(REMINDER)
    old = med.notifications()[-1]

    await move_to("2026-11-23 08:00:00")
    assert med.runs == 2

    await med.answer("Taken", old)
    assert not med.is_on
    assert med.running == 1

    await med.answer("Taken")
    assert med.is_on
