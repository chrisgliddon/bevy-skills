# Screen readers, semantics, and navigation

## Bevy and AccessKit

Bevy's `AccessibilityNode` wraps an `accesskit::Node`; the Winit integration exports
the tree to supported native platform accessibility APIs. `ui_widgets::Button`
requires `AccessibilityNode(Role::Button)`; `Label` and related widgets populate basic
roles; `AccessibleLabel` supplies an explicit name. The deprecated `ui::prelude::Button`
still gets a role through `bevy_ui`'s accessibility systems until it is removed.

If constructing custom nodes, depend on the same AccessKit line as Bevy 0.20 (`bevy_a11y 0.20.1` pins `accesskit 0.24`):

```toml
accesskit = "0.24"
```

```rust
use accesskit::{Node, Role};
use bevy::{a11y::AccessibilityNode, prelude::*};

fn custom_slider(mut commands: Commands) {
    let mut node = Node::new(Role::Slider);
    node.set_label("Music volume");
    node.set_numeric_value(70.0);
    node.set_min_numeric_value(0.0);
    node.set_max_numeric_value(100.0);
    commands.spawn(AccessibilityNode::from(node));
}
```

Verify method names against AccessKit 0.24 when adding advanced actions/states. Do not
add a second incompatible AccessKit version: its `Node` type will not convert.

## Semantic contract

Every interactive element needs:

- accurate role;
- concise accessible name that does not repeat the role;
- current value/state, range, selection, expanded state, and disabled state;
- relationships such as group, label, description, and error where supported;
- supported actions and a response to AccessKit `ActionRequest` messages;
- stable hierarchy and reading order;
- removal/update notifications when UI changes.

Decorative entities should not clutter the accessibility tree. Conversely, a rendered
world-space prompt that is essential must have an accessible equivalent even if it is
not a Bevy UI node.

## Focus/navigation contract

- `DefaultPlugins` initializes `InputFocus`; `TabNavigationPlugin` and
  `DirectionalNavigationPlugin` are explicit.
- In Bevy 0.20, call `focus.set(entity, FocusCause::Navigated)`; fields are private.
  `FocusCause::Auto` is recorded when an `AutoFocus` component grants focus.
- `Escape` in a focused `EditableText` clears focus and keeps bubbling, so a
  dialog-level cancel handler runs on the same press.
- Show a strong focus indicator whenever non-pointer navigation is active.
- Modal focus stays inside the modal; closing restores a sensible origin.
- Hidden/disabled/despawned controls leave navigation immediately.
- Directional navigation must be deterministic. Use manual overrides when spatial
  auto-navigation produces surprising results.
- Long lists, grids, tabs, sliders, text input, maps, and radial menus need dedicated
  keyboard/controller/screen-reader test cases.

Pointer hover is not focus. Visually highlighting hover must not silently move
screen-reader or keyboard focus.

## Gameplay narration

AccessKit exposes UI semantics; it is not a complete gameplay narrator or TTS engine.
Blind access may also require structured announcements for objectives, hazards,
orientation, targets, inventory changes, timing, and spatial navigation. Design an
announcement queue with priority, interruption, deduplication, rate limiting, and
localized text. Let players control verbosity and repeat recent announcements.

Use platform-supported speech facilities where required and test audio ducking with
screen readers. Never make the same critical information compete with dialogue,
captions, and narrator speech at once.

## Platform scope

AccessKit support and platform adapters vary. Console accessibility APIs and
certification requirements may require platform-specific work beyond Bevy/Winit.
Validate the actual shipping binary with the target screen reader and platform SDK;
do not infer support from a desktop development build.

## Sources

- [AccessKit](https://github.com/AccessKit/accesskit)
- [Bevy `bevy_a11y`](https://docs.rs/bevy/0.20.1/bevy/a11y/)
- [XAG 106: Screen narration](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/106)
- [XAG 112: UI navigation](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112)
