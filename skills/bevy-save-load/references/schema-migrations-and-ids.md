# Schema versions, migrations, and stable identity

## Keep three version concepts separate

- **envelope/format version:** byte framing, codec, compression, checksum layout;
- **schema version:** shape and semantics of the save DTO;
- **content build/version:** catalog data needed to interpret stable content IDs.

A new compression codec need not change quest semantics. A balance patch need not
change byte framing. Store the concepts independently so migration decisions are
precise.

## Migrate typed historical DTOs

Retain the minimum old DTO definitions needed by supported fixtures:

```text
bytes -> EnvelopeV1 -> Payload discriminator
                        | V1 -> migrate_v1_to_v2
                        | V2 -------------------> migrate_v2_to_v3
                        | V3 ------------------------------------> validate V3
```

Each migration is deterministic, side-effect free, and returns a structured error.
Do not read live assets, clocks, randomness, or network data during a schema migration.
If content lookup is required, pin a migration catalog/version and make missing IDs an
explicit error or documented fallback.

After migrating, validate domain invariants separately from deserialization:

- unique stable IDs and resolvable required references;
- finite positions/numbers and legal ranges;
- bounded collection sizes and decompressed bytes;
- valid graph ownership/no forbidden cycles;
- known content IDs or a defined unknown-content representation.

## Stable ID choices

Use immutable namespaced strings (`base:block/stone`), UUIDs, or another documented
domain key. Human-readable display names and translations can change. Dense numeric
indices are fine after load, once a map has been built for the current process.

For entity relationships, serialize `SaveId`, not Bevy `Entity`. Allocate all saved
objects first, build a map, then resolve references. Define ownership for missing
optional targets and reject missing required targets before committing the world.

Asset references should use stable asset paths plus labels or product-owned content
IDs, not transient `AssetId`/handle internals. Voxel data should store stable block IDs
directly or via a save-local palette whose entries are stable IDs.

## Golden fixture matrix

Keep immutable input fixtures for:

- every supported released schema version;
- minimum/empty and representative large saves;
- Unicode/unknown optional data;
- corrupt checksum, bad magic, truncated payload, decompression bomb limits;
- duplicate IDs, dangling references, invalid floats/ranges;
- future schema and future envelope versions.

Tests load every valid fixture to the current DTO and compare a canonical projection.
Round-trip the current format, but do not rely on round-trip alone: an encoder and
decoder can share the same bug. Never rewrite historical fixtures when adding a new
migration.
