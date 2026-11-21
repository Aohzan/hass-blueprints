# Home-Assistant blueprints

My personnal collection of Home-Assistant's blueprints


## Advanced medication reminder

Get advanced notification and history for medication reminder, on Android and
iOS (Home Assistant 2024.10 or later, official Companion app).

[medication_reminder.yaml](blueprints/medication_reminder.yaml)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FAohzan%2Fhass-blueprints%2Fmain%2Fblueprints%2Fmedication_reminder.yaml)

Features:

- Notification with Taken, Ask later and Skip buttons, repeated until an answer
  is given, with every step written in the logbook of a dedicated
  `input_boolean`.
- Turning the `input_boolean` on from anywhere else (dashboard button, NFC tag,
  script) counts as Taken and stops the reminder.
- Days of the week and additional conditions (calendar event, zone, template
  for a monthly medication...).
- Optional `input_datetime` set to the time the medication was taken.
- Optional actions at each reminder, when taken (decrement a pill counter,
  notify someone else...), when skipped and when there is no answer (TTS
  announcement...).
- Android notification channel (custom sound per medication) and iOS
  interruption level (time-sensitive, critical).

Several medications: create one automation (and one `input_boolean`) per
medication and reminder time. Each notification only answers its own
automation.

Several phones: the notification goes to one device. To notify more people,
create one automation per device, or add a notify action in the optional
actions.

Late or missing notifications on Android: the notification is sent with a high
priority, but some vendors (Samsung, Xiaomi, Huawei...) still delay it. Disable
the battery optimization of the Companion app, and check that the
`Medication reminder` notification channel is allowed to alert.

The former `medication_reminder_android.yaml` and `medication_reminder_ios.yaml`
files are kept as copies of `medication_reminder.yaml`, so that blueprints
imported from these URLs keep receiving updates. GitHub serves symlinks as
plain text on raw URLs, hence the copies. Update all three files together.

---

## Vacuum maintenance reminder

Get a notification when your Xiaomi vacuum needs maintenance (tested with Roborock S5 Max)

[vacuum_maintenance_reminder.yaml](blueprints/vacuum_maintenance_reminder.yaml)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FAohzan%2Fhass-blueprints%2Fmain%2Fblueprints%2Fvacuum_maintenance_reminder.yaml)

---

## Window and temperature

Watch and alert on window state according to temperature

[window_temperature.yaml](blueprints/window_temperature.yaml)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FAohzan%2Fhass-blueprints%2Fmain%2Fblueprints%2Fwindow_temperature.yaml)

---

## Nodon Z-Wave Remote (with Z-Wave JS)

Run action on Nodon Remote actions

[nodon-zwave-remote.yaml](blueprints/nodon-zwave-remote.yaml)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FAohzan%2Fhass-blueprints%2Fmain%2Fblueprints%2Fnodon-zwave-remote.yaml)
