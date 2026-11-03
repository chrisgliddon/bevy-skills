# Captions, audio, audio description, and communication

## Closed captions

Caption every meaningful spoken and non-spoken sound needed to understand or play:

- exact dialogue without censoring information;
- speaker identity when it is not visually obvious;
- meaningful music, alarms, footsteps, attacks, off-screen hazards, and ambience;
- direction/location where that affects response;
- vocal tone or delivery when plot/gameplay meaning depends on it.

Caption timing follows the sound, remains on screen long enough to read, avoids
covering essential UI, and does not spoil events before they occur. Localized captions
must be retimed or reflowed; copying source line breaks is not sufficient.

Provide independent controls for size, text/background colour, opacity, speaker
formatting, and non-dialogue captions. Use a safe, readable default and a preview in
settings. Keep closed captions distinct from dialogue-only subtitles.

## Audio controls and alternatives

Offer independent volume controls for dialogue, music, effects, ambience, narration,
voice chat, and accessibility cues where the mix supports them. Preserve dynamic-range
or night-mode options and expose mono/downmix behavior as appropriate.

Meaningful sound needs a visual, haptic, or narrated equivalent. Visual sound
indicators should communicate category and direction without becoming colour-only,
tiny, or visually overwhelming. Haptics supplement information; they are not the only
alternative because some players disable or cannot perceive vibration.

## Audio description and narration

Pre-rendered cinematics need audio description for important visual action, setting,
expressions, text, and scene transitions when dialogue does not convey them. Interactive
play may require contextual narration rather than a conventional description track.

Design speech priority and ducking across dialogue, descriptions, screen reader output,
chat TTS, and gameplay narration. Provide repeat, verbosity, and interruption controls.
Localize pronunciation and test with the actual speech engine/voice configuration.

## Multiplayer communication

When communication is core:

- never require voice as the only channel;
- provide accessible text chat and keyboard/controller navigation;
- integrate speech-to-text and text-to-speech where platform services allow;
- expose speaker identity and channel in transcripts;
- caption quick-chat/pings and give non-audio direction/context;
- make mute, block, report, and privacy controls accessible;
- distinguish generated transcripts and let users correct or resend important content.

Plan latency, profanity/privacy policies, offline failure, unsupported languages, and
network loss. An unavailable cloud service must not strand the player without a basic
communication path.

## Asset/data model

Keep caption/audio-description content separate from rendered text:

- stable cue ID;
- locale and source version;
- start/end time or gameplay event key;
- speaker and sound category;
- direction/context metadata;
- text and optional style token;
- reading-speed review status;
- localization and QA provenance.

This makes timing validation, localization diffing, styling, transcript generation,
and corrections possible without scraping UI code.

## Sources

- [XAG 104: Captions](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/104)
- [XAG 105: Audio](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/105)
- [XAG 111: Audio description](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/111)
- [XAG 119: Text communication](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/119)
- [XAG 120: Voice communication](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/120)
