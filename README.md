# MyDutyHA

Home Assistant integration for [MYDUTY](https://www.myduty.io/) shift schedules.

**v0.2.0 uses the MYDUTY app API instead of a web share link.** Share links
expire after 10 days (MYDUTY rotates them); the app API does not. Nothing here
scrapes the website.

## How it works

`kr.fourwheels.api` (the app's own client) signs every request with a key
embedded in the APK and identifies the account with the numeric `userId`. The
integration therefore needs your MYDUTY account once, and keeps only the
numeric user id afterwards.

* Sign in with e-mail + password → the user id is resolved and stored. The
  password is **not** kept.
* Or paste a numeric user id directly.

## Installation

1. Install via HACS (custom repository `Maypeur/MyDutyHA`) or copy
   `custom_components/mydutyha` into your `config/custom_components` folder.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → MyDutyHA**.
4. Enter a name, then either e-mail + password or a numeric user id.

### Upgrading from 0.1.x (share link)

Existing entries keep their entity ids, so automations and dashboards do not
change:

1. **Settings → Devices & Services → MyDutyHA → Configure**.
2. Sign in with the MYDUTY account whose roster you want (e-mail + password),
   or paste its numeric user id.
3. Save. Sync times stay as they were.

The old `share_id` is only kept as the stable entity key
(`sensor.myduty_<share_id>_day_code`). It is never fetched again.

## Options

* `Group id` + `Member user id` — optional: read one member's roster from a
  shared MYDUTY group instead of your own calendar. Use this when the roster
  belongs to someone else (e.g. a partner) and you don't want to store their
  login. Both fields are numeric; get the group id from the group's page in
  the app (the invite link/admin API) and the member id from the group's member
  list.
* `User id` — switch accounts without signing in again.
* `E-mail` + `Password` — optional, used to resolve a new user id.
* `Sync time 1..3` — daily refresh times (default `00:05`, `12:00`, `17:30`).

## Entities

| Entity | Meaning |
|---|---|
| `sensor.myduty_<id>_day_code` | shift code (`FD`, `Day`, `Nig`, `Off`, …) |
| `sensor.myduty_<id>_day_start` / `_day_end` | shift times as `HH:MM` |
| `binary_sensor.myduty_<id>_is_worked` | working today |
| `binary_sensor.myduty_<id>_is_off` | off / vacation today |
| `binary_sensor.myduty_<id>_is_night_shift` | night shift (incl. one started yesterday) |

## Service

`mydutyha.sync_now` — refresh immediately; optional `user_id`, otherwise all
entries.

## Example

```yaml
automation:
  - alias: Reminder on early shifts
    triggers:
      - trigger: time
        at: "06:00:00"
    conditions:
      - condition: state
        entity_id: sensor.myduty_<id>_day_code
        state: "FD"
    actions:
      - action: notify.mobile_app_iphone
        data:
          message: "Did you take your meds?"
```

## Notes

* The user id is effectively the credential for reading a calendar; treat it
  like a password.
* One entry per MYDUTY account. For someone else's roster without their
  password, create a group in the app, add them, and enter `Group id` +
  `Member user id` in the integration.
