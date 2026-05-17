# bevy-porting — Flash / SWF → Bevy 0.18

> Referenced from `bevy-porting/SKILL.md § Engine coverage`.

Many studios still have legacy Flash content — sprite art, sounds, font assets, level-layout constants — with real business value even though Flash Player is dead. **This reference is about extracting that content**, not porting ActionScript 1:1. Gameplay logic in ActionScript is a rewrite; the assets are a mechanical extraction job.

## Tool: `ffdec` (JPEXS Free Flash Decompiler)

`ffdec` is the standard open-source tool for reading `.swf` files without Flash Player or Adobe Animate.

- Project: <https://github.com/jindrapetrik/jpexs-decompiler>
- License: GPL 3+
- Install: download the release, ensure `ffdec` (Linux/macOS: `ffdec.sh`) is on `$PATH`, or pass `--ffdec` to the wrapper script.
- Java 11+ required (ffdec is a Java application).

`ffdec` can extract:

| SWF content | Exported format |
|---|---|
| Sprites / bitmaps | PNG |
| Shapes (`DefineShape`) | SVG or PNG (see vector note) |
| Sounds | MP3 or WAV (original codec) |
| Fonts | TTF / OTF where available |
| ActionScript 3 classes | `.as` source |
| ActionScript 1/2 bytecode | Partial decompilation (see AS version note) |

## `scripts/flash/swf_assets.py`

A thin Python wrapper around `ffdec`'s CLI that runs an extraction and emits a JSON manifest:

```sh
python3 scripts/flash/swf_assets.py game.swf \
    --out /tmp/swf-assets/ \
    --manifest manifest.json
```

Manifest shape:
```json
{
  "swf": "game.swf",
  "out_dir": "/tmp/swf-assets/",
  "assets": {
    "images":  [{"id": "Sprite_42", "path": "images/42.png",  "bytes": 1234}],
    "sounds":  [{"id": "Sound_5",   "path": "sounds/5.mp3",   "bytes": 56789}],
    "scripts": [{"id": "/MainClass.as", "path": "scripts/MainClass.as"}],
    "shapes":  [],
    "fonts":   []
  }
}
```

Use `--dry-run` to print the `ffdec` command without executing it (exits 0, safe without `ffdec` installed).

## Asset porting workflow

1. **Extract.** Run `swf_assets.py` — it calls `ffdec -export all <out_dir> <swf>`.
2. **Read the manifest.** Each entry maps a SWF symbol ID to an output file path. Symbol IDs are stable across extractions of the same SWF.
3. **Load in Bevy.** PNG images → `asset_server.load::<Image>("...")`. MP3/WAV → `asset_server.load::<AudioSource>("...")`.
4. **Assemble sprite-sheets.** SWF "MovieClip" timelines export as a sequence of numbered PNGs. Load them into a `TextureAtlasBuilder` or assemble manually. See `phaser.md § Sprite-sheet animation` for the `TextureAtlas` + `Timer` frame-advance pattern.

## ActionScript versions

| Version | Decompilation quality | Porting approach |
|---|---|---|
| AS3 (Flash 9+, SWF version ≥ 9) | Clean, readable class files | Read source; rewrite logic in Rust |
| AS2 (Flash 6–8) | Partially decompiled, limited typing | Use as a reference for constants/structure; rewrite |
| AS1 (Flash 1–5) | Obfuscated structure | Not a viable port target — treat game logic as lost |

For AS3, `ffdec` emits `.as` source under `scripts/`. Grep these files for `const` declarations to extract enemy stats, level layouts, and dialogue tables — these are the most reusable artifacts.

## Vector animation note

Flash's `DefineShape` records describe vector paths that play as timeline animations. `ffdec` can export shapes to SVG, but Bevy 0.18 core does not load SVG.

**Pragmatic recommendation: bake vector clips to PNG sprite-sheets.** Use ffdec's GUI or CLI to export each MovieClip at your target resolution (e.g. 2× the original SWF stage size) as a numbered PNG sequence, then treat them as raster sprites. Community crates (`bevy_prototype_lyon`) can draw vector primitives, but they do not reconstruct Flash's timeline system.

## Audio

Flash's embedded sounds export as MP3 or WAV without further processing. Load them into Bevy with `bevy_audio`:

```rust
let handle: Handle<AudioSource> = asset_server.load("sounds/jump.mp3");
commands.spawn(AudioPlayer::new(handle));
```

See `unity-audio.md` for the full Bevy audio concept map (`AudioPlayer`, `SpatialListener`, volume, etc.).

## Bytecode constants — level data, enemy stats, dialogue

The most portable artifacts in a Flash game are numeric and string constants. For AS3 projects:

```sh
# After ffdec extraction:
grep -r "static const" /tmp/swf-assets/scripts/ | grep -v "//.*$"
```

Transcribe these into Bevy `Asset<T>` configs (`.ron` or `.json`) loaded via `AssetServer`, rather than hardcoding in Rust source.

## See also

- [`../SKILL.md`](../SKILL.md) — bevy-porting dispatcher and general porting principles
- [`phaser.md`](phaser.md) — Phaser 3 → Bevy 0.18; sprite-sheet animation pattern used for MovieClip exports
- [`javascript.md`](javascript.md) — vanilla JS / Canvas → Bevy; useful if the Flash game had a companion JS version
- `bevy-ui` — re-creating Flash UI elements (buttons, text, panels) in Bevy's `Node` / Taffy system
- `bevy-animation` — `AnimationGraph`, sprite-sheet patterns for baked MovieClip sequences
