#!/usr/bin/env bash
# Generate the deprecated medication reminder blueprints from the unified one.
# The former Android and iOS import URLs keep receiving updates until their
# removal, with a deprecation notice in the blueprint and at each run.
set -euo pipefail

cd "$(dirname "$0")/../blueprints"

source_file=medication_reminder.yaml
removal_date="November 2027"

for platform in android ios; do
  target="medication_reminder_${platform}.yaml"
  awk -v removal="$removal_date" '
    !name_done && /^  name: / {
      print "  name: Advanced medication reminder (deprecated)"
      name_done = 1
      next
    }
    !description_done && /^  description: >-$/ {
      print
      print "    **Deprecated:** this blueprint file will be deleted in " removal "."
      print "    Import the unified blueprint from"
      print "    https://github.com/Aohzan/hass-blueprints/blob/main/blueprints/medication_reminder.yaml"
      print "    then edit each automation in YAML and set `use_blueprint.path` to"
      print "    `Aohzan/medication_reminder.yaml`: the inputs are the same."
      print ""
      description_done = 1
      next
    }
    /^actions:$/ {
      print
      print "  - alias: Deprecation notice"
      print "    action: persistent_notification.create"
      print "    data:"
      print "      notification_id: \"medication_reminder_deprecated_{{ this.entity_id }}\""
      print "      title: Deprecated medication reminder blueprint"
      print "      message: >-"
      print "        The automation \"{{ this.attributes.friendly_name }}\" uses a"
      print "        medication reminder blueprint file that will be deleted in " removal "."
      print "        Import the [unified blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FAohzan%2Fhass-blueprints%2Fmain%2Fblueprints%2Fmedication_reminder.yaml),"
      print "        then edit the automation in YAML and set `use_blueprint.path` to"
      print "        `Aohzan/medication_reminder.yaml`: the inputs are the same."
      next
    }
    { print }
  ' "$source_file" > "$target"
done
