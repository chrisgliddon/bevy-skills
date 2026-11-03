# Testing and evidence

## Test with disabled players

Recruit across relevant access needs and intersections; do not ask one participant to
represent an entire disability. Pay consultants/testers, support carers/interpreters,
allow breaks and remote participation, and let participants use their own devices and
assistive technology. Treat health/disability information as sensitive data.

Test task outcomes, effort, errors, recovery, fatigue, confidence, and preference—not
only whether a feature can technically be enabled.

## Minimum manual matrix

| Surface | Configurations |
|---|---|
| First launch | screen reader, controller-only, keyboard-only, large UI, captions before intro |
| Menus | tab/shift-tab, D-pad/stick, switch-like single input, pointer/touch, remapped controls |
| Gameplay | one hand/stick, digital movement, no hold/mash/chords, reduced motion, no audio, no colour |
| Controllers | adaptive device, unknown buttons/axes, two devices per player, hotplug, drift, reconnect |
| Text/audio | long locales, RTL where supported, large text, captions, narration overlap, chat STT/TTS |
| Platform | each OS/console screen reader, display mode, safe area, HDR/SDR, minimum hardware |
| Persistence | restart, profile switch, cloud/save migration, reset/recovery after bad binding |

Include tutorials, QTEs, vehicles, minigames, photo mode, maps, inventory, shops,
pause/death screens, multiplayer lobbies, disconnects, and end credits. Accessibility
often fails outside the primary gameplay loop.

## Automated gates

Automation catches regressions, not lived usability:

- input manifest coverage and mechanical-alternative flags;
- duplicate/conflicting bindings and inaccessible recovery actions;
- caption parse/timing/line-length/reading-speed and locale cue alignment;
- static contrast pairs and focus-state colours;
- semantic node snapshots for critical menus;
- focus reachability/cycle tests and modal containment;
- settings serialization/migration tests;
- image/video candidate scans for flashes, tiny text, and unsafe-area overlap.

Keep thresholds project-configurable and review warnings. A passing script is not a
store-tag or conformance decision.

## Evidence bundle

For each release candidate preserve:

- build commit/version and content hash;
- platform, device model, controller/AT/OS versions;
- requirement/test case ID;
- exact settings and save state;
- expected and observed result;
- logs, semantic tree snapshot, screenshot/video where consent permits;
- participant/expert finding with privacy-safe identifier;
- severity, owner, fix, retest result, and accepted residual risk.

Accessibility feature tags and public claims should link internally to this evidence.
Reopen evidence when UI, input, localization, audio mix, platform SDK, or content changes.

## Severity

- Blocker: cannot start, navigate, understand, or complete an essential path.
- Critical: feature claim is false, causes harm risk, or lacks a usable recovery path.
- Major: substantial extra effort, fatigue, ambiguity, or loss of important information.
- Minor: localized friction without blocking an outcome.

Prioritize impact and frequency, but never use low usage telemetry to dismiss an access
barrier; telemetry undercounts people who cannot enter or complete the flow.
