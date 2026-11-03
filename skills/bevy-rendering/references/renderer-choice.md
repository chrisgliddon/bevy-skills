# Renderer decision guide

## Built-in Bevy renderer

Choose it by default when the project needs Bevy cameras, PBR, sprites, UI, glTF,
post-processing, platform surfaces, or ecosystem plugins that insert render-world
systems. It provides the integration surface most Bevy plugins test.

Use high-level profiles first:

| Profile | Includes |
|---|---|
| `2d` | 2D APIs, Bevy sprite rendering, platform baseline |
| `3d` | 3D APIs, Bevy PBR/rendering, platform baseline |
| `ui` | UI APIs plus Bevy UI rendering |
| `audio` | Bevy audio; independent of rendering since 0.19 |

Low-level `*_bevy_render` collections keep Bevy rendering for one domain. `*_api`
collections retain components/assets without supplying pixels.

## Extend the built-in renderer

Prefer an extension when the need is local:

- a custom surface model → `Material`, `MaterialExtension`, or `MaterialExtension2d` (sprites, 0.20);
- a full-screen effect → post-process/fullscreen material;
- extra geometry → custom phase or specialized mesh pipeline;
- off-screen output → camera `RenderTarget`;
- a custom pass → render system in `Core2d` or `Core3d`;
- captured imagery or particles → a compatible plugin that uses the same render app.

This preserves asset extraction, visibility, view uniforms, scheduling, and platform
surface handling.

## External renderer

Choose an external renderer when there is a concrete non-negotiable constraint, such
as an existing embedded engine, a platform API wgpu cannot target, a proprietary
pipeline, or a research renderer whose architecture cannot fit Bevy phases.

Define the bridge contract before implementation:

| Concern | Required decision |
|---|---|
| World state | snapshot, change stream, or shared data ownership |
| Coordinates | handedness, units, axes, transform interpolation |
| Assets | who decodes, owns, uploads, and retires each asset |
| Visibility | Bevy-side, renderer-side, or duplicated culling |
| Cameras | projection/exposure conventions and render targets |
| Windowing | Bevy Winit ownership versus external event loop |
| Threading | which thread owns the GPU device and surface |
| Failure | device loss, resize, reload, and shutdown behavior |

Use stable IDs rather than raw Bevy `Entity` values across a process boundary.

## Headless

Headless means no pixels. It is appropriate for authoritative servers, offline
simulation, and tests. Avoid loading Bevy's render stack just to satisfy a plugin's
default feature set; disable that plugin's render/debug features or put visualization
in a separate client/tool.

## Selection evidence

Record at least:

- target platforms and minimum GPUs;
- frame-time, memory, and build-size budgets;
- required visual features and unsupported cases;
- ecosystem plugins that assume Bevy rendering;
- prototype measurements for the riskiest scene;
- maintenance ownership for custom GPU code.

Renderer replacement is an architecture decision. Capture it in an ADR so later
performance work does not quietly create two competing rendering stacks.

## Primary sources

- [Bevy Cargo features](https://docs.rs/bevy/0.20.1/bevy/#cargo-features)
- [Bevy 0.20 release notes](https://bevy.org/news/bevy-0-20/)
- [Bevy examples](https://bevy.org/examples/)
