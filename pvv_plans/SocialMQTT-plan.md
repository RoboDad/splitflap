# Plan: SocialMQTT — Social Media to Splitflap Bridge
# Status: Planning complete, implementation not started. Revised 2026-07-05
# (roadmap restructure + critical review; original plan 2026-03-27).
# Resume in Agent mode. Start with Phase 0.

## Roadmap (revised 2026-07-05)

The display-software effort is now three parts, in order:

- **Part I-A — 62-flap firmware** (STARTED 2026-07-05, spool order
  confirmed 2026-07-06): the physical display uses custom 62-flap modules
  (Scott's 52-flap sequence with 10 custom flaps — 7 emoji, 1 artwork,
  2 multi-module panels — inserted after '$').  Firmware support exists
  as `[env:chainlink_pvv62]` (`-DPVV_FLAPS_62`, "Flap option 5" in
  `firmware/src/config.h`) and builds clean.  Remaining: flash,
  re-calibrate offsets, see it flip.
- **Part I-B — BLE iPhone app** (NEW): direct Bluetooth control for
  demoing the display away from home WiFi.  Full plan in
  `pvv_plans/BLE-app-plan.md`.  Independent of the bridge; shares the
  62-flap character codes.
- **Part I-C — SocialMQTT bridge**: this document (Phases 0–5 below).

**Canonical custom-flap code map** (single source of truth is
`firmware/src/config.h` "Flap option 5"; the bridge's `_sanitize()`
charset and the BLE app's emoji picker must match it):
`h`=heart `j`=joy `n`=wink `s`=smile `b`=sob `k`=kiss `e`=heart_eyes
`d`=art_1(woodgathering) `c`=panorama(skyline, multi) `t`=art_2(triptych,
multi) — indexes 43–52, inserted after '$' (42) in Scott's sequence.

## Context
- Hardware: scottbez1/splitflap on ESP32 (chainlink board)
- Current display: 24 modules; future displays up to 100+ modules
- Flap count: 62 per module (standard 52-flap set + 10 custom) — firmware support started, see Part I-A in the roadmap above
- MQTT command topic: `home/<DEVICE_NAME>/command` — plain-text payload, uppercase
- Character set (bridge Part I-C): standard 52-flap subset (A-Z, 0-9, space, punctuation); custom-flap codes arrive with the Part II escape sequences
- Firmware lib: PubSubClient v2.8 — plain TCP only, needs WiFiClientSecure swap for TLS
- OTA: ArduinoOTA fully supported, chainlink_ota env in platformio.ini
- MQTT broker: EMQX Cloud free tier (serverless, TLS port 8883)
- Bridge host: Raspberry Pi on home network
- BlueSky trigger: mention + #todisplay sentinel + sender whitelist
- Discord trigger: dedicated channel + whitelist

## Part II scope (updated 2026-07-05)
- ~~Extended flap count support (58/64 flaps) in firmware~~ → **promoted to
  Part I-A and started**: the display is 62 flaps; firmware charset done
  (pending spool-order confirmation).
- Still deferred:
  - Bridge-side emoji escape sequences in message strings
    (e.g. `[:HEART:]` → flap code `h`) — becomes a small `_sanitize()`
    translation table once Part I-A is confirmed; `_sanitize()` should
    leave a placeholder comment for this passthrough.
  - Multi-module panel triggers in messages (e.g. `[:SKYLINE:]` spanning
    modules 0–5) — needs index-level control from the bridge (the plain
    text topic can carry the `c`/`t` codes per module as an interim hack).
  - Displays over 100 modules.

## Directory structure
- Firmware fork: C:\Users\phgev\Documents\Make\Splitflap\Firmware\splitflap\
- Bridge code: C:\Users\phgev\Documents\Make\Splitflap\SocialMQTT\
- GitHub: RoboDad/SocialMQTT

## Architecture: Cloud MQTT + Pluggable Adapters + FIFO Queue

```
BlueSkyAdapter (thread) ──┐
                           ├──► queue.Queue (FIFO) ──► DisplayController ──► EMQX Cloud TLS ──► Display(s)
DiscordAdapter (thread) ──┘
```

- Multiple displays supported: each has a name + topic + module_count in config
- First-come first-served; DisplayController holds each message for min_display_time seconds (default 10s)

### Core Python components
- Message dataclass: text, source, sender, timestamp, display (optional target)
- SourceAdapter ABC: start(queue), stop(), _sanitize(text, module_count), _check_rate_limit(sender)
- DisplayController: queue.get(block=True) loop, paho-mqtt TLS publish, time.sleep(min_display_time)
- BlueSkyAdapter: polls app.bsky.notification.listNotifications every 30s
- DiscordAdapter: discord.py bot, reads dedicated channel

## Config shape (config.yaml template)
```yaml
mqtt:
  host: abc123.emqxsl.com
  port: 8883
  tls: true

displays:
  - name: darlington
    topic: home/darlington/command
    module_count: 24   # current display; set per display
  # - name: grandma
  #   topic: home/grandma/command
  #   module_count: 12

display:
  default_display: darlington
  min_display_time: 10   # seconds

bluesky:
  enabled: true
  handle: you.bsky.social
  sentinel: "#todisplay"
  whitelist: [friend.bsky.social, family.bsky.social]
  poll_interval: 30
  rate_limit_seconds: 300

discord:
  enabled: false
  # bot_token: xxxx
  # channel_id: 123456789
  # whitelist: [123456789]   # Discord user IDs
  # rate_limit_seconds: 300
```

## Files to create

### SocialMQTT repo (C:\Users\phgev\Documents\Make\Splitflap\SocialMQTT\)
- requirements.txt — atproto, discord.py, paho-mqtt, PyYAML
- config.yaml — full template with placeholders (committed)
- config.secret.yaml — actual credentials (gitignored)
- socialmqtt/__init__.py
- socialmqtt/adapter.py — Message dataclass + SourceAdapter ABC
- socialmqtt/bluesky_adapter.py — BlueSkyAdapter
- socialmqtt/discord_adapter.py — DiscordAdapter
- socialmqtt/display_controller.py — FIFO + TLS MQTT loop
- socialmqtt/main.py — load config, start adapters, run controller
- splitflap-bridge.service — systemd unit (Restart=always)
- setup.sh — RPi install helper (apt, venv, pip, service enable)
- README.md — project overview + links to all docs + quick-start
- docs/setup-emqx.md — EMQX Cloud free tier signup + credentials
- docs/setup-display.md — firmware WiFi/MQTT/OTA configuration ("product setup" doc)
- docs/setup-bluesky.md — app password, account setup
- docs/setup-discord.md — bot creation, permissions, channel setup
- docs/setup-raspberry-pi.md — full RPi walkthrough
- docs/adding-a-display.md — how to add a second remote display
- docs/architecture.md — system diagram + component descriptions

### Firmware fork changes (C:\Users\phgev\Documents\Make\Splitflap\Firmware\splitflap\)
- firmware/esp32/splitflap/secrets.h.example — add MQTT_TLS define, port 8883, CA cert placeholder note
- firmware/esp32/splitflap/mqtt_task.h — add WiFiClientSecure member (conditional on MQTT_TLS)
- firmware/esp32/splitflap/mqtt_task.cpp — use WiFiClientSecure when MQTT_TLS defined; call setInsecure()
- platformio.ini — add MQTT_TLS=1 to chainlink build_flags; set MQTT=true

## Security
- Sender whitelist per adapter (BlueSky handles, Discord user IDs)
- Per-sender rate limit (default 5 min) in-memory per adapter
- Shared _sanitize() in SourceAdapter base class: uppercase, strip to [A-Z0-9 .?$'#!@&,-], truncate to module_count
- paho-mqtt TLS to EMQX; credentials only in gitignored config.secret.yaml
- BlueSky: app password only (never main account password)
- Discord: bot scoped to one channel, read + send messages permissions only
- EMQX: separate credentials for bridge vs. each display device

## Phases

### Phase 0 — Repo + Cloud broker (FIRST in agent mode)
0a. Create RoboDad/SocialMQTT on GitHub, clone to C:\Users\phgev\Documents\Make\Splitflap\SocialMQTT
0b. Sign up for EMQX Cloud Serverless free tier; document in docs/setup-emqx.md

### Phase 1 — Firmware: WiFi + MQTT TLS + OTA
1a. Populate secrets.h from secrets.h.example (WiFi SSID/pass, EMQX host/8883/user/pass, OTA password, DEVICE_INSTANCE_NAME=darlington)
1b. Add MQTT=true + MQTT_TLS=1 to platformio.ini chainlink build_flags
1c. Modify mqtt_task.h — add `#ifdef MQTT_TLS WiFiClientSecure #else WiFiClient #endif` member
1d. Modify mqtt_task.cpp — use WiFiClientSecure, call secure_client_.setInsecure() in connectWifi()
1e. Initial USB flash (chainlink env); verify WiFi connects, device shows online in EMQX dashboard
1f. OTA test (chainlink_ota env, upload over network)
1g. Write docs/setup-display.md

### Phase 2 — Core bridge (steps parallel)
2a. socialmqtt/adapter.py — Message dataclass, SourceAdapter ABC with _sanitize/_check_rate_limit
2b. socialmqtt/display_controller.py — queue.get loop, TLS MQTT publish, time.sleep(min_display_time)
2c. socialmqtt/main.py + config.yaml template + .gitignore (gitignore config.secret.yaml)

### Phase 3 — BlueSky adapter
3a. socialmqtt/bluesky_adapter.py — poll listNotifications, filter mention+sentinel+whitelist, enqueue
3b. End-to-end test: BlueSky post → MQTT → splitflap flips
3c. docs/setup-bluesky.md

### Phase 4 — Discord adapter
4a. socialmqtt/discord_adapter.py — discord.py bot on dedicated channel, whitelist, enqueue
4b. Multi-source concurrency test (both adapters running, verify FIFO order)
4c. docs/setup-discord.md

### Phase 5 — Deployment + Documentation
5a. splitflap-bridge.service + setup.sh
5b. docs/setup-raspberry-pi.md, docs/adding-a-display.md, docs/architecture.md
5c. README.md with overview + quick-start + all doc links
5d. Full integration test: both platforms simultaneously, FIFO ordering, min_display_time gap verified

## Critical review (2026-07-05, against the actual repo and current services)

Verified correct — no action needed:
- All firmware paths in this plan exist as written (`firmware/esp32/splitflap/
  mqtt_task.{h,cpp}`, `secrets.h.example`, `[env:chainlink_ota]`).
- `-DMQTT=false` flag and PubSubClient 2.8 are wired exactly as assumed;
  `MQTT_MAX_PACKET_SIZE` is already 512 in platformio.ini (ample for text).
- The MQTT command topic (`home/<DEVICE_INSTANCE_NAME>/command`) feeds
  `showString(payload, length, false, true)` — plain text, as planned.
- espressif32@3.4 (arduino-esp32 1.0.6) has `WiFiClientSecure` with
  `setInsecure()`, so the Phase 1 TLS swap is a small, safe change.
- EMQX Serverless free-tier quota check: 2 always-on clients (bridge +
  display) ≈ 86k session-minutes/month vs the 1M free allowance — fine
  even with several displays.

Corrections / additions to fold into the phases:
1. **Discord privileged intent** (Phase 4 + docs/setup-discord.md): reading
   message text requires enabling the *Message Content Intent* in the
   Discord developer portal AND passing `intents.message_content = True`
   to discord.py. The plan omits this; bots silently receive empty
   message bodies without it.
2. **Firmware behavior with unknown characters**: `showString()` silently
   leaves a module UNCHANGED for any character not in `flaps[]` (no error,
   no homing). The bridge's `_sanitize()` is therefore load-bearing — and
   it should PAD messages to the display's module count with spaces,
   because the MQTT path sets `default_unspecified_home=true` (modules
   beyond the payload go to blank, which is desirable — rely on it and
   document it rather than discovering it).
3. **Retained messages**: publish commands NOT retained. A retained social
   post would replay onto the display every time it reboots, arbitrarily
   late. If "restore last message after power cycle" is ever wanted, do it
   bridge-side with a freshness window.
4. **`_sanitize()` charset must match firmware**: the allowed set
   `[A-Z0-9 .?$'#!@&,-]` remains correct for the standard subset, but the
   canonical source of truth is now `config.h` "Flap option 5" (62 flaps).
   Add the lowercase custom codes only via the Part II escape-sequence
   table — never let raw lowercase from social posts through, since
   lowercase letters are flap codes (`h` = heart!). Uppercasing BEFORE
   filtering (as planned) already guarantees this; keep that order.
5. **TLS with `setInsecure()`**: acceptable for v1 (low-sensitivity data,
   credentials still protect the broker), but note it explicitly accepts
   MITM. v2 option: embed the EMQX CA cert (`setCACert()`); costs ~1.5 KB
   flash and breaks on CA rotation, so document the tradeoff in
   docs/setup-emqx.md rather than hard-requiring it.
6. **Home Assistant discovery publish** in `connectMQTT()` fires a config
   message to `homeassistant/text/...` on every connect. Harmless on EMQX,
   but consider gating it behind a `HOME_ASSISTANT` define during the
   Phase 1 firmware edits to keep the broker tidy.
7. **BlueSky auth**: app passwords still work but Bluesky is moving toward
   OAuth; atproto-lib handles sessions either way. Not a blocker — note in
   docs/setup-bluesky.md to revisit if login starts failing. Polling
   `listNotifications` every 30 s is far inside rate limits.
8. **Bridge resilience** (Phase 2): add explicit reconnect/backoff for the
   MQTT client and a bounded queue (drop-oldest + log) so a burst of posts
   or a display outage cannot grow memory unbounded on the Pi.
9. **Ordering nit**: Phase 1e says "verify device shows online in EMQX
   dashboard" — EMQX signup is Phase 0b, so keep 0b strictly before 1e
   (already implied, just noting the dependency).
