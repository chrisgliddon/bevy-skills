# similarity-rs 0.5 — False Positives

Not all high-similarity pairs need to be merged. Here are the common cases where
structural similarity is intentional — review the context before refactoring.

---

## 1. Test fixtures (`--skip-test` handles most)

Test files frequently contain structurally similar `setup` functions, helper
builders, and expected-value tables that mirror production code by design.

```rust
// Two test helpers that set up similar but distinct scenarios — both are needed
fn setup_empty_world() -> World { ... }
fn setup_world_with_player() -> World { ... }
```

**Action:** Run CI with `--skip-test`. Review test-file hits locally with
judgment — some test helpers genuinely should be extracted; most shouldn't.

---

## 2. Derive-macro generated code

Proc-macros (`#[derive(Serialize, Deserialize, Debug, Clone)]`) emit identical
structural boilerplate for similar types. The tool may flag the generated output
as duplicated even though it is not hand-written.

**Action:** Ignore. The duplication is in the macro, not the code. No refactor
needed.

---

## 3. FFI shims mirroring an external API

Thin wrappers around a C or system API must match the external interface.
Two shims with different names but the same parameter patterns are structurally
similar by specification, not accident.

```rust
// These look identical but wrap two distinct system calls
unsafe fn write_file(fd: i32, buf: *const u8, len: usize) -> isize { ... }
unsafe fn read_file (fd: i32, buf: *mut   u8, len: usize) -> isize { ... }
```

**Action:** Ignore. The shape is dictated by the external ABI.

---

## 4. Trait impls for similar types

Implementing `From<A>` and `From<B>` for a common type often produces similar
bodies when `A` and `B` are structurally related (both newtypes around `u32`,
for instance). The trait system requires separate impls.

```rust
impl From<ChunkId> for usize { fn from(id: ChunkId) -> usize { id.0 as usize } }
impl From<BlockId> for usize { fn from(id: BlockId) -> usize { id.0 as usize } }
```

**Action:** Ignore, or consider a macro if there are 5+ similar impls.

---

## 5. Bevy systems with similar structure but different queries

Two systems that run the same logic on different archetype slices are
*intentionally parallel*, not accidentally duplicated.

```rust
// These query different component combinations — unifying them would require
// unsafe query merges or parameter over-generalization
fn update_static_meshes (q: Query<&mut Transform, With<StaticMesh>>)  { ... }
fn update_animated_meshes(q: Query<&mut Transform, With<AnimatedMesh>>) { ... }
```

**Action:** Only merge if the body would remain identical after unification.
If the `Query` filter *is* the semantic difference, leave them separate.

---

## 6. Protocol/serialization symmetry

Encode and decode functions often look like mirrors of each other (same field
list, same length, inverted operations). High structural similarity is expected.

```rust
fn encode_packet(p: &Packet, buf: &mut Vec<u8>) { ... }
fn decode_packet(buf: &[u8]) -> Packet           { ... }
```

**Action:** Ignore.

---

## 7. Builder pattern steps

Builder methods often have identical structure: take `self`, set one field,
return `self`. A 10-field builder will produce 10 structurally similar functions.

```rust
impl SpawnConfig {
    pub fn with_health(mut self, v: f32) -> Self { self.health = v; self }
    pub fn with_speed (mut self, v: f32) -> Self { self.speed  = v; self }
    // ...
}
```

**Action:** Consider a macro if the pattern repeats 5+ times; otherwise ignore.
The semantic difference is which field is set.
