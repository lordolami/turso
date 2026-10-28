# Proposed storage, receipt, and event formats

This chapter fixes product-owned format proposals at version 1. It does not redefine Turso's database pages, WAL frames, MVCC log, or PostgreSQL catalogs. Native payload encodings are pinned to their engine reader version. Every new format requires golden fixtures, malformed-input tests, and crash recovery tests before use with real data.

## Manifest serialization and addressing

Product manifests use UTF-8 JSON without BOM, duplicate keys, NaN, or Infinity. IDs, digests, counters, byte lengths, and microsecond timestamps use lowercase ASCII or decimal strings as defined by their fields. Binary data uses base64 only when it cannot be stored as a referenced object. Numeric fractions do not appear in identity-bearing metadata. Serialize identity-bearing manifests with keys sorted by UTF-8 bytes, no insignificant whitespace, and a single documented string-escape implementation. Hash those exact canonical bytes with SHA-256; pretty JSON is a display/export representation and is re-canonicalized before hash verification.

The canonicalizer must have fixtures shared between Go and native code; do not assume two default JSON encoders escape HTML or Unicode identically. Persist canonical bytes so readers do not need to infer a historical serializer. Format versions define their serializer and checksum algorithm permanently. Changing either creates a new version.

Objects are addressed by the digest of stored bytes. Encryption happens before the stored-object digest; a manifest can additionally record a protected plaintext digest for verification. Identical plaintext encrypted with different nonces is not assumed to deduplicate. Object filenames are lower-case 64-character digests, split into a two-character directory prefix if needed for filesystem scaling.

Publish using a random same-filesystem staging name, complete write, flush, verify digest and length, then atomic publication under the final digest. If another worker already published that digest, verify its size/identity before reuse. A catalog row does not make an incomplete file a completed object. Parent-directory durability is implemented and qualified per OS; unsupported durability behavior must not be silently accepted.

## Generation manifest

| Field | Required meaning |
|---|---|
| format / version | `mira.generation` and decimal version 1 |
| instance_id / database_id / generation_id | Immutable UUID identities |
| provider / dialect | `turso`; `sqlite` or `postgres`, immutable |
| native_revision / build_manifest_sha256 | Exact engine source and linked feature manifest |
| native_format_versions | Versioned database/WAL/MVCC/frontend/index reader requirements |
| persistence / journal_mode | Persistent or memory; actual native mode |
| schema_revision | Platform schema epoch, not a guessed native cookie |
| namespaces | Stable namespace ID, SQL name, native file ID, safe bundle-relative path, namespace revision |
| files | Complete file inventory described below |
| commit_boundary | Native commit identity or coordinated file revision vector |
| encryption | Key IDs and coverage by artifact; no raw keys |
| extensions | IDs, exact versions/build digests, state/object references |
| parent / source | Optional generation, snapshot, branch, and restore lineage |
| created_at / verified_at | UTC microsecond strings |

A file entry contains file_id, role, relative_path, logical_length, storage_encoding, object/extent references, digest, native identity, and encryption coverage. Roles include main database, PG namespace, page WAL, MVCC log, index artifact, and native metadata. Relative paths contain no empty, dot, dot-dot, device, or root segments. The reader checks duplicate/case-colliding paths under the target OS's rules. An FTS directory is inventoried recursively rather than treated as one unknown mutable path.

The current-generation pointer is a small canonical manifest: format, version, database_id, active_generation_id, generation_manifest_digest, lifecycle_intent_id, and expected_previous_generation_id. A replacement is published only by the lifecycle protocol. Readers do not select the largest UUID or newest modification time.

## Snapshot and backup manifest

A snapshot records snapshot_id, source generation manifest, exact native boundary, complete file inventory, object digests, key dependencies, extension dependencies, verification state, and originating job. A backup records backup_id, destination identity, snapshot manifests, optional history segment ranges, private catalog inclusion, installation identity, and completion marker digest. A multiple-database backup has one boundary per database unless a verified installation-wide write drain was used.

Completed manifests are immutable. Verification results and retention changes are separate revisioned catalog records. Restore refuses unknown mandatory fields/format versions, missing files, mismatched lengths/digests, invalid path mappings, unavailable keys, incompatible native formats, and incomplete history. A user-selected destination name never changes the source identity recorded in the artifact.

## Archive envelope

Product archive segments wrap exact native recovery payloads with durable framing. Version 1 proposes this fixed 64-byte little-endian record header:

| Offset | Bytes | Field |
|---|---|---|
| 0 | 8 | Magic `MIRALOG` followed by zero byte |
| 8 | 2 | Envelope version, 1 |
| 10 | 2 | Header length, 64 |
| 12 | 2 | Record type |
| 14 | 2 | Mandatory flags; unknown bits rejected |
| 16 | 8 | Payload byte length, bounded before allocation |
| 24 | 8 | Segment-local record sequence |
| 32 | 16 | Native transaction/capture identity mapped to a UUID |
| 48 | 8 | Logical commit sequence, zero for uncommitted fragments |
| 56 | 4 | CRC32C of payload |
| 60 | 4 | CRC32C of header bytes 0 through 59 |

Record types are SEGMENT_BEGIN=1, TX_BEGIN=2, NATIVE_FRAGMENT=3, TX_COMMIT=4, TX_ABORT=5, FILE_MAP=6, CHECKPOINT_BOUNDARY=7, SEGMENT_END=8. Payload schemas are versioned by type. SEGMENT_BEGIN binds database, generation, archive generation, native format, sequence, and previous completed segment digest. NATIVE_FRAGMENT identifies stream kind, file ID, native offset/revision, and exact bytes. FILE_MAP carries durable create/rename/delete identity changes. TX_COMMIT carries the complete fragment digest set, native commit marker identity, observed commit time, and resulting revision vector. SEGMENT_END records counts, final committed boundary, and preceding bytes digest.

CRC detects torn records cheaply; complete-segment SHA-256 and previous-segment linkage verify publication and ordering. A record is never trusted based only on length or CRC. Decoders reject arithmetic overflow, excessive allocation, duplicate/conflicting sequences, wrong generation, impossible native format, invalid commit membership, and a forked chain. A torn uncommitted tail is reported and truncated only according to a native-verified recovery boundary. A checksum failure in an acknowledged committed range is corruption, not an ignorable tail.

The timestamp index is derived/rebuildable and maps microsecond time to complete commit sequence plus segment/record positions. Clock rollback does not reorder commits: the monotonic sequence is authoritative. Timestamp selection chooses the last complete retained commit whose recorded commit time is at or before the requested time, with deterministic sequence tie-breaking. The resolved commit is returned before restore. Time is an observation of the commit boundary, not a distributed/global clock promise.

## Commit/archive ordering

The difficult boundary is a crash between native durability and archive publication. The required algorithm is a recoverable capture protocol integrated with the native journal, not a watcher after commit:

1. Reserve capture identity, file map, and archive capacity before the write can require a history guarantee.
2. Stage and flush sufficient exact native fragments and capture intent, or retain the originating native log durably under an explicit no-truncate dependency.
3. Perform native commit with a durable mapping from its commit marker to the capture identity. An application catalog row is not that marker.
4. Publish/flush the archive TX_COMMIT and index from the native outcome, then acknowledge a history-guaranteed application result.
5. Release the originating log dependency only after the archive commit is durable and readable.

Recovery of a pending capture inspects native commit truth. A committed marker completes archival from staged/retained bytes. An aborted marker records abort. An uncertain marker blocks history-guaranteed writes until resolved. A commit may have reached disk even though the caller received an archive error; return unknown_commit_state with a recovery reference rather than lying that it rolled back.

The actual WAL and MVCC hooks must prove that the native marker survives until this reconciliation completes. If current storage cannot persist the necessary association, extend that native format/metadata deliberately with backward-compatibility handling. An on-paper two-file sequence is not an atomicity proof. PG attached schemas additionally need a consistent bundle boundary; an archive record does not create native cross-file atomic transactions that do not exist.

## COW extents and overlays

Use 64 KiB immutable storage chunks as the proposed initial product extent size, independent of native database page size. The native I/O adapter maps file ID plus byte offsets to base chunks and branch-owned overlays. An extent entry has logical chunk index, stored-object digest, meaningful length, encoding/key reference, and optional zero/hole marker. File length is explicit; reads after truncate cannot expose old shared bytes.

Partial writes read the current chunk, replace only the written byte range, and stage a branch-owned replacement. WAL/log append and fsync semantics remain native operations; chunk sharing never allows a checkpoint to overwrite a parent's object. A sparse extent reads as zero only where the native filesystem contract permits it. Writes spanning chunks preserve native ordering and failure semantics. Publication groups dirty chunk references into an immutable overlay root; fsync acknowledgment requires the root and dependencies to be durable.

The mutable working overlay needs a native crash-recoverable delta journal; it cannot rewrite a large JSON extent map for every page write. That journal records file identity, truncate/rename, changed extents, and root publication with checksums. Its accepted commit point must align with the native log's fsync contract. Native file locks remain scoped to the branch's writable generation, with safe shared immutable reads. No Go callback retains a page slice after the call returns.

Keep base+overlay lookup depth bounded by background consolidation into a new immutable root while retaining old roots for readers. Metrics expose shared bytes, unique bytes, logical bytes, lookup depth, dirty overlay bytes, and consolidation backlog. Benchmark 4/16/64 KiB native page sizes, small WAL appends, large sequential imports, FTS segment publication, and repeated tiny branch edits before freezing the 64 KiB choice. Changing the extent format requires a versioned migration.

## Target-database receipts

For retryable product-managed writes/migrations, reserve an internal native metadata namespace inaccessible to user SQL. The engine/frontend must hide it from normal object discovery and protect it through native authorization; merely choosing an unusual public table name is insufficient.

Within the SAME target transaction as the effects, write receipt_id, operation_id, principal_id, credential_scope_digest, payload_digest, generation_id, commit identity where assignable, result digest, and expiry policy. A receipt lookup requires the same authority and payload binding. A repeated key with another digest returns idempotency_conflict. A receipt is not expired while a durable job can legitimately retry it. If native internals cannot provide this namespace safely, implement a protected system table with explicit compatibility tests before advertising write retry guarantees.

The private catalog mirrors the receipt for service discovery but is not its atomic source of truth. For multi-database jobs, each target has a receipt and independent outcome. No distributed commit is introduced. Arbitrary user SQL remains non-retryable unless executed through this explicit protected-receipt mode.

## Event envelope and retention

Job, change, audit, and subscription streams share an envelope: envelope_version, event_id, stream_id, sequence, occurred_at, kind, resource_type/resource_id, database_id/generation_id if relevant, request_id/job_id, policy_epoch, payload_version, and bounded payload. Resource visibility and event payloads are authorized independently. Sensitive SQL, bind values, result rows, credentials, and keys are absent by default.

Job kinds include queued, started, progress, waiting, cancel_requested, cancelled, succeeded, failed, and reconciliation_required. Progress carries unit/current/total only when real. Change events carry native revision and the authorized row/object change; schema changes invalidate incompatible live-query state. Gap events carry the first available cursor and bootstrap requirement. Transport reconnection never silently resets a durable cursor.

Cursors are opaque authenticated encodings of stream, resource/generation, position, policy binding, expiry, and format version. They are not raw database offsets or authorization credentials. On resume, authenticate again, check current policy, validate cursor binding/expiry, and reject generation_changed, cursor_expired, or history_gap precisely. Bounded queues disconnect/require resync rather than allocating forever or silently dropping events.
