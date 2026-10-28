# Catalog and filesystem design

## Instance layout

~~~text
mira_data/
  instance.json                  instance ID and format versions; no raw keys
  instance.lock                  OS-enforced single-owner lock
  control/                       local endpoint metadata; socket on Unix
  catalog/
    platform.db                  private installation catalog
    engine-owned sidecars
  databases/<database_uuid>/
    database.json                immutable identity/provider/dialect metadata
    generations/<generation_uuid>/
      main.db
      engine-owned WAL/log/schema/FTS files
      generation.json            file bundle manifest and format versions
    current.json                 active generation reference
  objects/<sha256>/              immutable local snapshot/branch/archive objects
  history/<database_uuid>/<generation_uuid>/
    manifests/
    commit-index/
  snapshots/<snapshot_uuid>/
  backups/<backup_uuid>/
  trash/<resource_uuid>/
  staging/<job_uuid>/
  logs/
  diagnostics/
  secrets/                       protected local secret material or references
~~~

File names are design choices, not Turso's existing on-disk format. Engine sidecars are discovered through a native manifest, not inferred from one file extension. PostgreSQL namespaces and FTS can own additional files. Store each logical database in its own UUID directory to prevent schema-file name collisions across databases.

## Identity and names

Generate UUIDv7 resource identifiers in the application; they are independent of native row IDs. Display names may be human-readable Unicode. Slugs used in endpoints use a documented lowercase ASCII grammar with a maximum length and unique scope. Names never become filesystem paths. A database rename changes catalog labels and routing aliases, not its storage UUID.

Persist instance ID, database ID, generation ID, provider, dialect, native revision, storage format, journal mode, schema revision, encryption key reference, and relevant feature flags. Verify these before admitting a file bundle. A directory renamed by an operator does not become a new authenticated database.

## Private catalog

[catalog.sql](contracts/catalog.sql) defines a proposed schema with these groups:

- Installation version/settings and catalog migration history.
- Organizations, groups, principals, memberships, invitations, and roles/grants.
- Credentials, sessions, revocation/policy epochs, and secret references.
- Databases and storage generations, including active-generation references.
- Templates, migration runs, and schema revisions.
- Jobs, job events, idempotency records, and staged file assets.
- History segments, snapshots, branches, backup policies/artifacts, and trash retention.
- Sync clients/checkpoints, subscription cursors, and audit events.

Use SQLite-dialect Turso for this private catalog, with foreign-key enforcement, explicit durable sync behavior, and a bounded pool. Public SQL sessions cannot open it. Catalog writes use parameterized statements and optimistic revision checks. Timestamps are UTC integer microseconds; presentation converts to the user's configured timezone.

The SQL file is a design contract checked for syntax by an independent SQLite parser. That check is not evidence that every statement executes identically on the audited Turso engine; native catalog conformance remains a release requirement.

## Atomicity across catalog and files

A catalog transaction cannot atomically commit an arbitrary filesystem rename and user-database transaction. Use durable operation intents and idempotent reconciliation rather than pretending they are one transaction.

For every lifecycle job:

1. Commit an intent containing resource IDs, expected old revision/generation, desired state, staged paths, and operation ID.
2. Perform bounded native/file work into the job's staging area.
3. Flush content and manifest before publication; synchronize parent directory metadata where the OS/filesystem supports the required guarantee.
4. Publish an immutable completed artifact or a replacement current-generation reference using a documented atomic rename strategy.
5. Finalize the catalog transaction and operation receipt.
6. Reconcile any missing finalization after restart by checking manifest identity and checksums.

Windows and Unix have different rename/open-handle behavior. Restore/deletion closes or drains handles before replacement on platforms that require it. Never remove a directory that can still be reached through a live session or retained snapshot reference.

## Database/generation consistency

The catalog's active generation and current.json must agree after reconciliation. Neither is blindly trusted when a crash interrupted publication. The operation intent and completed, checksummed generation manifest determine whether to roll forward or leave the previous generation active.

Restore creates a new generation. Existing sessions keep the old generation until drained or are rejected with generation_changed; no session follows a pointer swap silently. Recovery, branch creation, encryption transforms, and format migration each produce explicit generation lineage.

## File containment

Resolve resources through catalog IDs to canonical paths under the installation root. Reject traversal, device paths, alternate data streams where inappropriate, symlinks/reparse points escaping roots, hard-link ambiguity where file identity matters, and path changes between validation and open. Prefer directory-relative opens and handles with OS-appropriate no-follow behavior. Remote operations accept staged asset IDs or snapshot IDs, never arbitrary host paths.

Operators can authorize backup roots and extension roots explicitly. Resource access still checks instance ownership, target identity, and expected revisions. A network client cannot turn PostgreSQL COPY, SQLite ATTACH, CSV functions, or native extension loading into unrestricted file access.

## Secrets and encryption

Catalog rows store credential hashes or references, never plaintext passwords/tokens. The secrets directory has restrictive OS access. Snapshot/history encryption uses explicit key IDs; manifests retain required key references through the recovery retention window. Losing a key may make encrypted backups unrecoverable, so installation recovery documents key custody separately from backing up encrypted bytes.

Do not assume page encryption also encrypts every MVCC log, FTS artifact, diagnostic file, or archive object. Verify each artifact type or encrypt it in the platform archive layer. A plaintext catalog can reveal resource names and policy metadata; whole-installation encryption is a separate declared setting with its own recovery tests.

## Quotas and garbage collection

No database-count quota is imposed by the vendor. An operator may set an optional count policy, bytes limit, active-handle budget, or concurrency budget. Null count quota means unset. Active-handle exhaustion does not delete catalog entries or report that the product license is exhausted.

Garbage collection walks immutable manifest reachability, retained backups, branches, active native generation references, and sync retention cursors. Delete only objects no retained root references. Persist a deletion intent and make cleanup retryable. Checksums detect accidental corruption; they are not proof against an administrator who can replace both data and manifests.
