# Plan: SocialMQTT — Social Media to Splitflap Bridge
# Status: Planning complete, implementation not started (as of 2026-03-27)
# Resume in Agent mode. Start with Phase 0.

## Context
- Hardware: scottbez1/splitflap on ESP32 (chainlink board)
- Current display: 24 modules; future displays up to 100+ modules
- Flap count: 58 or 64 per module (extended, vs standard 40/52) — firmware changes are Part II
- MQTT command topic: `home/<DEVICE_NAME>/command` — plain-text payload, uppercase
- Character set (Part I): standard 52-flap set (A-Z, 0-9, space, punctuation)
- Firmware lib: PubSubClient v2.8 — plain TCP only, needs WiFiClientSecure swap for TLS
- OTA: ArduinoOTA fully supported, chainlink_ota env in platformio.ini
- MQTT broker: EMQX Cloud free tier (serverless, TLS port 8883)
- Bridge host: Raspberry Pi on home network
- BlueSky trigger: mention + #todisplay sentinel + sender whitelist
- Discord trigger: dedicated channel + whitelist

## Part II scope (explicitly deferred — do not plan or implement yet)
- Extended flap count support (58/64 flaps) in firmware
- Multi-module image display driven by emoji-style escape sequences (e.g. [:HEART:]) in message strings
- Firmware character set expansion beyond standard 52-flap set
- Displays over 100 modules
- Note: _sanitize() should leave a placeholder comment for escape sequence passthrough

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
