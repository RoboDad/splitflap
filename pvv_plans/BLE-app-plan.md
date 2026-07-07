# Plan: BLE iPhone App — direct display control without WiFi
# Status: Planning (2026-07-05). Decision gate RESOLVED 2026-07-06:
#   user has an iMac (not yet set up for development — Xcode install needed).
#   Native SwiftUI app path is GO; SoftAP fallback stays documented as plan B.
# Roadmap position: Part I-B — after 62-flap firmware (I-A), before SocialMQTT bridge (I-C).
# See pvv_plans/SocialMQTT-plan.md for the overall roadmap.

## Goal
Show off the display at work, where it cannot join the corporate WiFi.
An iPhone app connects to the ESP32 **directly over Bluetooth LE** and can:
- send text strings (with a decent composer UI),
- insert the 7 custom emoji flaps,
- trigger the multi-module artwork panels (skyline, triptych),
- show connection/display state.

Not a full-featured product — but polished enough to demo proudly.

## Decision gate (RESOLVED: iMac available, Xcode install needed)

Resolution 2026-07-06: user has an iMac; it needs Xcode installed
(free, ~15–30 GB disk, App Store or developer.apple.com).  With a free
Apple ID, sideloaded builds expire after 7 days (re-deploy from Xcode
each week — fine for a personal demo device); a $99/yr Apple Developer
account lifts this to 1 year + TestFlight.  Add "B2a: install Xcode +
first Hello-World deploy to the physical iPhone" as the first app step —
do this early, since Apple provisioning is the likeliest source of
first-day friction.

Original considerations (kept for the record) — building a native iPhone
app requires Xcode on macOS; there is no Windows path to an installable
iOS app:

- **Web Bluetooth does NOT exist on iOS** (Safari and all iOS browsers) —
  a browser-based BLE client on the iPhone is ruled out.
- Cross-platform frameworks (Flutter, React Native) still require a Mac
  for the iOS build step.
- With a Mac + free Apple ID: sideloaded builds expire after 7 days
  (re-deploy from Xcode each week).  A $99/yr Apple Developer account
  lifts this (1-year provisioning, TestFlight).

**Fallback if no Mac — SoftAP web app (no Bluetooth at all):** the ESP32
broadcasts its own WiFi access point and serves the control page itself;
the iPhone joins the ESP32's AP in Safari.  This never touches the work
network (the security constraint is the corporate LAN, not radios), needs
no app install, and reuses `http_task.cpp` patterns.  ⚠ Check your
workplace policy on personal wireless APs first — some orgs prohibit any
unauthorized AP; BLE is usually less regulated.

**Recommendation:** build the firmware BLE service (Phase B1) regardless —
it is testable without any custom app, is the explicit ask, and also
serves future Android/desktop clients.  Choose native app vs SoftAP
fallback at the gate.

## Firmware side (Phase B1) — BLE GATT service

Slots into `firmware/esp32/splitflap/main.cpp` exactly like the MQTT/HTTP
tasks: `#if BLE` + `BleTask bleTask(splitflapTask, displayTask, serialTask, 0);`
with a `-DBLE=true` build flag in a new `[env:chainlink_pvv62_ble]`.

- **Stack**: NimBLE-Arduino **1.4.x** (pin it — 2.x requires a newer
  arduino-esp32 core than the project's `espressif32@3.4` / core 1.0.6).
  NimBLE uses ~35 KB RAM vs Bluedroid's ~100 KB; current build sits at
  10.7% RAM so either fits, but NimBLE leaves the most headroom.
- **WiFi off in this mode** (BLE env replaces MQTT/HTTP envs, mirroring
  how MQTT and HTTP are already mutually optional tasks).  No coexistence
  complexity for the demo use-case.
- **GATT design** (one custom 128-bit service):

  | Characteristic | Props | Payload |
  |---|---|---|
  | Text | write | UTF-8/ASCII string, ≤ NUM_MODULES bytes; app maps emoji → single-byte flap codes (h/j/n/s/b/k/e — see config.h option 5) and calls `showString()` |
  | FlapIndexes | write | byte array ≤ NUM_MODULES; each byte = flap index 0..61, `0xFF` = leave module unchanged. Needs a small new `SplitflapTask::showIndexes()` (trivial — `showString()` minus `findFlapIndex`). Used for the skyline/triptych panels |
  | State | read + notify | compact per-module state: flap index + moving + home-status bits; app renders a live display mirror |
  | Control | write | 1-byte ops: reset&home, clear (all → flap 0) |

- **Panels are just index arrays**: panorama/skyline = index 51 on
  modules 0–5, art_2/triptych = index 52 on modules 0–5 (indexes per
  config.h option 5; spool order confirmed 2026-07-06 — customs sit at
  43–52, inserted after '$').  The app hardcodes/configures these
  patterns; the firmware stays generic.
- **MTU**: iOS negotiates ≥185 bytes; 24-module payloads fit in a single
  write even at the 20-byte minimum with chunking never required in
  practice — but accept long-writes anyway (NimBLE handles it).
- **Security**: open (no pairing) for v1 — anyone in radio range could
  write to the display during the demo.  Acceptable; add a
  passkey/allowlist later if it ever lives somewhere public.
- **Bench test without any custom app**: LightBlue or nRF Connect on the
  iPhone can write to the characteristics directly — Phase B1 is fully
  verifiable before a single line of app code exists.

## iPhone app (Phases B2–B4, if Mac available)

SwiftUI + CoreBluetooth, single-screen-plus-sheet design:

- **B2 — skeleton**: scan/auto-reconnect to the service UUID, connection
  status, plain text field → Text characteristic.  (Deliverable: strings
  on the display from the phone.)
- **B3 — the fun part**:
  - Live display mirror: 24 cells rendering the current flap of each
    module (State notifications), using the actual flap artwork — reuse
    `pvv_tools/assets/emoji/*.svg` and glyph SVGs as app assets.
  - Emoji picker row (the 7 emoji flaps) inserting codes into the composer.
  - Panel buttons: SKYLINE / TRIPTYCH → FlapIndexes writes.
  - Character counter vs module count; uppercase-as-you-type.
- **B4 — polish**: haptics on send, preset messages, offset/home controls
  (Control characteristic), app icon.

## Phases summary

- **B0**: Decision gate — RESOLVED (iMac; native app path GO).  Still
  worth checking the workplace personal-AP policy only if the SoftAP
  fallback is ever wanted.
- **B1**: Firmware BLE task + GATT service + `showIndexes()`; bench-test
  via nRF Connect / LightBlue.  *No app dependency.*
- **B2a**: Install Xcode on the iMac + Hello-World deploy to the physical
  iPhone (de-risk Apple provisioning first).
- **B2**: App skeleton (connect + text).
- **B3**: Emoji picker, panels, live display mirror.
- **B4**: Polish.
- **F1** (fallback, replaces B2–B4 if no Mac): SoftAP + embedded web app
  with the same composer/emoji/panel features, served from the ESP32.

## Dependencies / interactions

- **62-flap firmware (Part I-A)** must land first: the emoji codes and
  panel indexes come from config.h "Flap option 5".  Spool order confirmed
  2026-07-06 (customs at indexes 43–52, inserted after '$'), so
  character-based text mapping is settled.
- **SocialMQTT (Part I-C)** is unaffected: BLE and MQTT are separate
  build-flag tasks.  Long-term both could be enabled together (RAM
  permitting) so the home display keeps MQTT while BLE remains a local
  override channel.
