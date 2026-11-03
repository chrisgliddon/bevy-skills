# Accessibility requirements and evidence

## No single universal game standard

Native games span real-time 3D content, platform services, controllers, chat, and
rendered UI. WCAG is essential for transferable UI/content criteria but does not by
itself define accessible gameplay. Use a layered requirements set:

- [Xbox Accessibility Guidelines](https://learn.microsoft.com/en-us/gaming/accessibility/guidelines)
  for public game-specific requirements and test ideas;
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) at the highest applicable level;
- [Game Accessibility Guidelines](https://gameaccessibilityguidelines.com/full-list/)
  for a broad game-design checklist;
- each platform's current certification and accessibility-feature-tag rules;
- direct research and testing with disabled players.

Do not claim “WCAG AAA game” or legal conformance without a qualified, scoped audit.
Document which surfaces were assessed: launcher, account flow, game UI, gameplay,
cutscenes, chat, companion web pages, and platform overlays may have different owners.

## Legal and procurement overlay

Engineering guidelines are not a substitute for a jurisdiction/product-scope review:

- In the United States, CVAA/FCC advanced-communications obligations can apply to
  electronic messaging, internet voice communication, and interoperable video
  conferencing supplied with a game. Treat chat, documentation/support, upgrades,
  accessibility records, and third-party communication dependencies as a separate
  compliance workstream; the CVAA is not a general gameplay-accessibility standard.
- The EU European Accessibility Act applies from 28 June 2025 to listed products and
  services including e-commerce and electronic communications. Determine with counsel
  which store, account, payment, support, launcher, and communication surfaces are in
  scope under each member state's implementation; do not label the whole game covered
  or exempt based only on the executable.
- EN 301 549 may be invoked by law, public procurement, or contract. Record the exact
  edition and clauses required: an ETSI draft or newer publication does not silently
  replace the edition cited by a contract or official journal.
- Check every shipping jurisdiction, publisher agreement, platform certification
  package, age/education context, and customer procurement requirement. Assign legal
  interpretation to qualified counsel and keep the engineering evidence ledger useful
  regardless of the resulting scope.

## Requirements ledger

For each requirement record:

| Field | Meaning |
|---|---|
| ID/source | XAG/WCAG/platform/product requirement |
| User need | barrier removed, in the player's language |
| Scope | menus, gameplay modes, platforms, peripherals |
| Design | interaction and fallback, including failure states |
| Implementation | components/systems/assets/settings involved |
| Verification | automated check plus human test cases |
| Evidence | build, device, AT version, video/log, tester finding |
| Owner/status | accountable team and remediation date |

Requirements without a user need become checkboxes; requirements without evidence
become unverified claims.

## Highest-standard principles

- Equivalent outcomes matter more than identical interaction.
- Customization is granular: players combine features rather than choose a disability
  preset that guesses their needs.
- Settings are discoverable before the barrier appears and operable with the same
  assistive setup they configure.
- Important information has at least two modalities where practical.
- Essential gameplay is not gated by one device, sensory channel, timing window, or
  precision mechanic.
- Assist features preserve agency and are available across modes, difficulty levels,
  saves, achievements, and multiplayer unless a documented constraint is unavoidable.
- Accessibility telemetry is opt-in, privacy-preserving, and never used to infer a
  diagnosis.

## Feature tags and store claims

Map store/platform tags to exact, tested behavior. “Remappable controls” should mean
all essential gameplay/UI actions, conflict resolution, persistence, and a recovery
path—not only a partial gameplay preset. “Subtitles” and “closed captions” are not
interchangeable: closed captions also communicate meaningful non-dialogue audio and
speaker/context information.

Reverify claims after input, UI, localization, or platform changes. A feature can
regress even when its settings screen still exists.

## Public source index

- [XAG 107: Input](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/107)
- [XAG 104: Captions](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/104)
- [XAG 106: Screen narration](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/106)
- [XAG 112: UI navigation](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112)
- [Xbox accessibility feature tags](https://learn.microsoft.com/en-us/gaming/accessibility/accessibility-feature-tags)
- [WCAG 2.2 conformance](https://www.w3.org/TR/WCAG22/#conformance)
- [FCC accessibility complaint categories and covered advanced communications](https://consumercomplaints.fcc.gov/hc/en-us/articles/204231424-Accessibility-Complaint-Filing-Categories)
- [FCC advanced-communications accessibility order](https://docs.fcc.gov/public/attachments/FCC-11-151A1.pdf)
- [European Commission: European Accessibility Act](https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/european-accessibility-act-eaa_en)
- [ETSI Human Factors accessibility standards programme](https://www.etsi.org/committee/hf)
