# Visual, cognitive, and motion accessibility

## Visual presentation

- Text and essential icons remain legible under project-supported scaling, UI scale,
  resolution, safe-area, localization expansion, and high-DPI settings.
- Normal text targets at least 7:1 contrast for WCAG AAA; large text targets 4.5:1.
  Essential non-text controls/focus indicators need at least 3:1 against adjacent
  colours. Evaluate every state and worst-case dynamic background.
- Colour is never the only signal. Pair it with shape, pattern, icon, position, text,
  audio, or haptics.
- Player, enemy, objective, loot, and interactable differentiation survives common
  colour-vision deficiencies and monochrome screenshots.
- Focus indicators are thick, high-contrast, unobscured, and distinct from selection.
- Allow opaque text/caption backing where content can cross gameplay imagery.

A global colour filter can damage carefully authored contrast and does not replace
semantic colour customization. Test palettes with affected players and simulation
tools, then verify on real displays.

## Motion and photosensitivity

Provide independent settings for camera shake, head bob, motion blur, depth of field,
chromatic aberration, FOV changes, zoom animation, parallax, screen distortion,
particles, and UI animation. “Reduce motion” should have a documented effect and be
available before gameplay.

Avoid content that flashes more than three times in any one-second period; use WCAG's
general and red-flash thresholds for any unavoidable flashing. Automated video
analysis can identify candidates but requires expert/human review across HDR, frame
rate, and display conditions.

Do not tie critical aiming or orientation to camera motion. Provide a persistent
reticle/reference, adjustable FOV and sensitivity, horizon stabilization where
appropriate, and instant transitions as an alternative to animated camera travel.

## Cognitive and learning accessibility

- Use consistent terms, icons, layouts, navigation, and control behavior.
- Prefer plain, direct instructions with replayable examples and practice.
- Keep objective history, controls, tutorials, dialogue logs, and recent narration
  available on demand.
- Let players pause or slow noncompetitive single-player content, extend timeouts, and
  retry from useful checkpoints.
- Separate difficulty dimensions such as damage, timing, resource pressure, puzzle
  hints, navigation, stealth visibility, and aim assist.
- Reduce simultaneous prompts, clutter, background motion, and competing audio through
  granular settings.
- Never encode essential instructions only in transient text.

## Status effects and feedback

Damage, low health, stealth detection, cooldown, interaction success, targeting, and
navigation need redundant feedback. Avoid relying only on screen-edge colour washes,
tiny particles, controller vibration, or spatial audio.

Settings previews must be safe: do not demonstrate intense flashes/shake before the
player confirms. Provide an immediate cancel/revert path and timeouts that do not lock
in an unusable display mode.

## Sources

- [XAG 102: Contrast](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/102)
- [WCAG 2.2 contrast enhanced](https://www.w3.org/TR/WCAG22/#contrast-enhanced)
- [WCAG 2.2 three flashes](https://www.w3.org/TR/WCAG22/#three-flashes)
- [Game Accessibility Guidelines](https://gameaccessibilityguidelines.com/full-list/)
