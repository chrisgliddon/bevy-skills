# Native and browser persistence

## Native commit protocol

For a single local slot:

1. Capture/encode in memory with strict maximum size.
2. Write a uniquely named temporary file in the destination directory.
3. Flush buffered bytes and call the platform's file sync operation when crash
   durability is required.
4. Validate the temp file or its encoded checksum before commit.
5. Atomically rename/replace the committed path using platform-correct semantics.
6. Sync the parent directory where required for rename durability.
7. Update/retire the previous backup only after the new commit succeeds.

The temp file must be on the same filesystem as the destination; cross-filesystem
rename is not atomic. Replacement semantics differ across operating systems, so use a
tested storage adapter rather than assuming one `std::fs::rename` call replaces an
existing file everywhere.

Run blocking filesystem calls on `IoTaskPool` and poll the owning `Task` each frame:

```rust
use bevy::{prelude::*, tasks::{block_on, poll_once, IoTaskPool, Task}};

#[derive(Component)]
struct SaveJob {
    generation: u64,
    task: Task<std::io::Result<()>>,
}

fn start_save(mut commands: Commands, bytes: Vec<u8>, generation: u64) {
    let task = IoTaskPool::get().spawn(async move {
        let tmp = std::env::temp_dir().join("slot0.sav.tmp");
        let dst = std::env::temp_dir().join("slot0.sav");
        std::fs::write(&tmp, &bytes)?;
        std::fs::rename(&tmp, &dst) // real code: fsync + platform replace semantics
    });
    commands.spawn(SaveJob { generation, task });
}

fn poll_save(mut commands: Commands, mut jobs: Query<(Entity, &mut SaveJob)>) {
    for (entity, mut job) in &mut jobs {
        if let Some(result) = block_on(poll_once(&mut job.task)) {
            // Compare `job.generation` with the newest request before reporting.
            let _ = result;
            commands.entity(entity).remove::<SaveJob>();
        }
    }
}
```

Maintain an operation ID/generation so a slow older autosave cannot overwrite a
newer one. Return success/error to the main
world and update UI only after commit. Debounce requests and coalesce to the newest
snapshot while one write is active.

## Recovery

At startup, inspect committed, backup, and orphan temp generations. Validate magic,
declared sizes, checksum, and schema before selecting the newest valid generation.
Never overwrite all recoverable copies merely because the newest file failed to load.
Expose recovery to the player and preserve corrupt artifacts for support when consent
and privacy policy allow it.

## Browser storage

Use IndexedDB for structured/large game saves and binary blobs. Local storage is
synchronous, small, string-only, and better suited to compact preferences. Wrap the
backend behind the same asynchronous save/load service used on native.

A robust browser commit can use generation-keyed records plus a small committed-head
record in one IndexedDB transaction. On load, follow only a completely committed
generation and retain a previous valid generation. Handle:

- quota rejection and user-cleared/evicted site data;
- private browsing and storage APIs being unavailable;
- page refresh/close before an async request completes;
- multiple tabs/instances writing the same slot;
- origin/version changes and application updates;
- explicit export/import for player-controlled backups.

Requesting persistent storage can reduce eviction risk where the browser grants it,
but it is not guaranteed. Never claim a save succeeded before the transaction's
completion callback/promise resolves.

Primary platform references:

- [MDN IndexedDB](https://developer.mozilla.org/docs/Web/API/IndexedDB_API)
- [MDN Storage API](https://developer.mozilla.org/docs/Web/API/Storage_API)
- [Bevy `SettingsPlugin`](https://docs.rs/bevy/0.20.1/bevy/settings/struct.SettingsPlugin.html) (cargo feature `bevy_settings`, off by default)

## Security and privacy

Treat imported/cloud/browser bytes as untrusted. Limit allocation and decompression,
avoid path traversal, and validate before world mutation. Checksums detect accidental
damage, not adversarial edits. Encrypt only with a documented key-management/threat
model; obscuring a local save is not security. Avoid placing credentials or sensitive
personal data in ordinary game saves.
