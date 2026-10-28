# Local history, snapshots, branching, and recovery

## Required outcome

Users can create consistent snapshots, independent branches, copy-on-write branches, retained historical branches, local backup policies, point-in-time restores, deleted-database recovery, and whole-installation backups. These are standalone services we implement. A native database file and a CDC table alone do not provide this outcome.

## Storage mode inventory

| Mode/artifact | Required treatment |
|---|---|
| Standard WAL | Preserve complete committed page-frame history and checkpoint/reset identity |
| MVCC logical log | Preserve complete versioned transaction frames before checkpoint/truncation changes the source |
| Main database | Snapshot under an engine-consistent read/checkpoint boundary |
| PostgreSQL schema files | Include their identities, commit relationships, sidecars, and schema mapping |
| FTS/native extension storage | Include required artifacts or a documented deterministic rebuild recipe |
| Encryption | Preserve ciphertext/codec context and key IDs without disclosing key bytes |
| Catalog | Back up independently under an installation manifest; reconcile resource/file publication |

The audited sqlite3_backup_* functions are stubs. Add a native snapshot API or use a proved quiesced snapshot protocol. Never copy a live main.db and assume it includes committed WAL or MVCC state.

## Native commit/archive integration

For history-enabled databases, integrate with the engine's actual commit and checkpoint paths. A filesystem watcher cannot reliably capture bytes before truncation, distinguish failed/partial commits, or preserve logical-log generation identity.

The proposed local archive contract is:

1. A transaction obtains an engine commit sequence and records the affected storage bundle.
2. Native commit/history integration produces an immutable complete archive record or durable append with checksum, format ID, generation ID, and commit boundary.
3. The engine's normal durability operation completes under the configured sync policy.
4. The history layer durably records the commit and its revision mapping before acknowledging the history-enabled write as fully durable.
5. Checkpoint/truncation cannot discard the only retained representation of a required commit.

The implementation must define recovery for a crash between the database commit and archive publication. Reserve/recover archive intent in the native commit path, retain sufficient original log bytes, and never acknowledge a guarantee whose required archive data can be lost. A poisoned archive blocks further history-guaranteed writes until reconciled or the operator explicitly changes the guarantee. It does not manufacture an apparently complete history with gaps.

Persist exact native format versions and reader compatibility. MVCC log offsets can reset after checkpoint; offset alone is not a revision. Product revision identity includes database, generation, archive/log generation, commit sequence, and relevant checksum/salt identity.

## Consistent snapshots

Snapshots retain a native generation reference and freeze an engine-consistent revision. Capture a complete file bundle and record its checksums/lengths, journal mode, dialect/provider, schema revision, extension state, encryption key IDs, and commit/history boundary. For PostgreSQL attached schemas, establish a consistent bundle checkpoint or capture an explicitly coordinated revision vector. Do not claim atomicity across files that the engine cannot yet guarantee; implement the coordinator and verify it before publishing that capability.

If using a write-drain snapshot, admission blocks new writes, active writes complete/rollback, checkpoints execute with correct native locking, all relevant files are flushed and captured, and writes resume only after a recoverable snapshot root exists. Reads may continue only if the chosen native mechanism guarantees their file references remain valid.

## Local copy-on-write storage

The design target is a portable manifest-backed storage layer with immutable base objects and branch-owned changed blocks/history. Each branch reads unchanged content through its base manifest and writes into its own generation. Implement it through the native I/O/storage abstraction with correct file locking, read/write ordering, WAL/MVCC behavior, checksums, sync calls, and extension artifact handling.

A page-codec callback is not a complete COW virtual filesystem: it transforms pages but does not automatically implement branching, file replacement, allocation, sidecars, or checkpoint semantics. Filesystem reflinks can accelerate snapshots where available but cannot be the sole cross-platform semantic contract. A full-copy clone is useful but must not be labeled copy-on-write.

Branch metadata stores source database/generation/revision, base manifest digest, current writable generation, lineage, and retention references. Deleting a parent does not remove shared objects still referenced by children. Branch merging is explicit migration/data work; no automatic general-purpose merge is promised.

## Backup artifacts

A backup manifest records artifact ID, originating job, creation time, provider/dialect, native revision/format, snapshot boundary, file/object list, checksums, encryption references, history range, and catalog associations. Write to a staging destination, verify, then atomically publish a completed marker. A partially written backup is never listed as complete.

Policies configure local destination root, schedule, timezone, retention by age/count/bytes, verification mode, and the databases/groups included. Use local files or operator-mounted storage; do not add managed cloud storage provisioning. Multiple database backups have independently recorded boundaries unless an explicit installation-wide write gate coordinates them.

## Point-in-time restore

Input identifies a database, retained target timestamp or commit revision, destination name, and restore mode. Time selection resolves to the last fully committed retained revision at or before the requested time, with the resolved revision returned to the caller.

1. Authorize restore and resolve required snapshot/archive/key dependencies.
2. Create a durable restore job and hold retention references.
3. Reconstruct into a new generation under staging.
4. Replay only complete committed records in the correct native format and order.
5. Verify file checksums, native integrity, schema, required extension state, and expected target revision.
6. For restore-as-new, publish a new database identity. For replacement, drain old sessions and atomically switch the generation through the lifecycle protocol.
7. Revoke/invalidate old generation sessions, query cursors, and sync cursors explicitly.
8. Retain the old generation according to rollback/retention policy and publish the result manifest.

Never replay a SQL audit log as equivalent to physical/native recovery: nondeterminism, missing binds, DDL, implicit effects, and failed transactions invalidate that shortcut. Never replay past the verified archive end. Report history_gap, missing_key, unsupported_format, or corruption with an actionable job result.

## Trash and whole-installation recovery

Deleted database recovery restores its retained bundle and policy/ownership identity, subject to name conflicts and current authorization. Whole-installation recovery includes the private catalog and resource manifests; it also requires access to the key material referenced by encrypted content. A restored installation receives an explicit identity decision so old credentials cannot silently gain access to an unintended clone.

## Retention and failure behavior

Reference roots include completed backups, branches, active restore jobs, active snapshots, required sync cursors, and configured history windows. Refuse new history work or return capacity errors before deleting needed history under disk pressure. An operator can explicitly expire retention with a recorded effect on recovery/client bootstrap; cleanup must not silently shorten a promised recovery window.

Test abrupt termination at each manifest write, directory sync, log append, native commit, checkpoint, archive rotation, generation switch, and cleanup boundary. Verify WAL and MVCC independently, plus PostgreSQL schema bundles and FTS/encryption combinations.
