# PostgreSQL integration

## Product promise

PostgreSQL is an explicit database frontend and connection endpoint in the standalone product. It is not a translation label applied to SQLite SQL and not a promise of complete upstream PostgreSQL server compatibility. The runtime publishes the exact supported subset and feature status for its linked frontend revision.

The audited implementation is split into postgres/parser, postgres/frontend, postgres/server, and postgres/cli. Preserve the parser -> native Turso AST -> compiler -> VDBE path. Go owns the public listener and platform services; a new native bridge owns frontend database and connection objects.

## Fixed dialect and file identity

The frontend opens a database using PostgresDialect with MVCC enabled. The engine's Dialect is fixed for an open database and participates in the global file registry. Catalog dialect is immutable for an existing database. A request selecting SQLite against a PostgreSQL database returns dialect_mismatch.

PostgreSQL schemas are implemented with attached storage. Their files belong to the containing logical database's generation. Names must resolve through safe schema metadata instead of becoming arbitrary paths. A create/drop schema job records every affected file, closes relevant handles, and coordinates durable publication. Backup, restore, branch, and purge include those files and their sidecars.

## Per-client session ownership

Each authenticated connection gets an independent PgConnection and session state. Do not reuse the reference server's single shared Arc<Mutex<PgConnection>>. Isolate search_path, custom parameters, current sequence values, transactions, prepared statements, portals, errors, and cancellation IDs.

Connection settings that can carry request.jwt.claims are application data, not authenticated authority. Native policy receives principal context only through the trusted bridge. SQL current_user/auth helper results must be derived or constrained consistently with that trusted identity if exposed as security-relevant information.

## Startup and authentication

The Go adapter parses the startup packet, checks message size/protocol support, negotiates configured TLS behavior, authenticates credentials, resolves the requested database alias to its immutable ID, authorizes connect, reserves capacity, and then creates the native frontend session.

Use SCRAM-SHA-256 service credentials as the proposed normal method. The configuration contract also permits password_over_tls only with verified TLS policy and a separately implemented verifier; it is not allowed over an exposed plaintext connection. Store SCRAM verifiers rather than plaintext passwords. A browser session cookie is not a PostgreSQL password. Database tokens may be exchanged/used only through a documented supported login mechanism; do not pretend any JWT automatically satisfies a PostgreSQL client's password protocol. Client-certificate authentication would require a separately specified identity mapping and is not claimed by the current configuration schema.

Bind non-loopback listeners only when operator configuration supplies the required authentication/TLS policy. Support reverse-proxy exposure deliberately. The upstream NoopHandler/trust path and process_socket(..., None, ...) are evidence of work required, not production defaults.

For scoped service access, credential issuance with kind=postgres_scram generates a random password and a credential-specific login identifier, returns the password through the protected issuance-delivery flow, and stores SCRAM verifier material under a protected reference. The startup username resolves that immutable credential ID, while the startup database resolves the catalog database ID/alias. Their scopes must intersect. Local human login can use a separately maintained principal SCRAM verifier only when explicitly enabled; an Argon2 password hash cannot be converted back into a SCRAM verifier. Revocation checks the credential record and policy epochs even after successful SCRAM authentication. A credential alias cannot choose a native PostgreSQL superuser role.

## Wire behavior

| Area | Required product behavior |
|---|---|
| Startup/SSLRequest | Correct framing, explicit supported versions, configured certificates, useful rejection |
| Simple Query | Native PG statement splitting, ordered responses, transaction-status correctness |
| Parse/Bind/Describe/Execute/Sync/Close | Independent statement/portal maps, exact parameter count/type handling, resource budgets |
| RowDescription/DataRow | Preserve column names, OIDs/type modifiers, NULL, arrays, decimal/numeric precision, text/binary format availability |
| ErrorResponse/ReadyForQuery | Preserve SQLSTATE/detail/position when known; accurately report idle/in-transaction/failed state |
| Cancellation | Backend key data mapped to an unguessable authenticated cancellation capability; native interrupt without freeing live objects |
| Terminate/disconnect | Roll back unresolved transactions and release all session objects |
| COPY | Permit only implemented variants with bounded streaming and contained import sources |
| Database selection | Resolve one database during startup; no arbitrary host path or cross-organization alias lookup |

Implementing a Go wire decoder is not implementing PostgreSQL semantics. Every statement still passes through the real native PostgreSQL frontend. Prepared SQL cannot be sent to the SQLite SDK merely because both return rows.

## Observed compatibility areas

At the audited revision, the reference covers substantial SELECT/JOIN/DML, constraints, indexes, schemas, sequences, domains/enums, arrays, UUID/network/custom types, casts, expressions, materialized views, savepoints, and portions of simple/extended wire querying. It also documents partial behavior and rejected features. This table highlights boundaries; [postgres/COMPAT.md](../../postgres/COMPAT.md) remains authoritative for individual entries.

| Area | Boundary to preserve |
|---|---|
| Transactions | Snapshot-isolation behavior; serializable and two-phase commit are not general supported claims |
| ALTER TABLE | Supported subset; do not erase unimplemented clauses |
| JSON/JSONB | Supported type/operators subset differs from full PostgreSQL JSON functionality |
| Catalog | Emulated subset; hardcoded roles are not product role enforcement |
| COPY | Text-file input and text table output have specific support; STDIN/CSV/binary/arbitrary-query variants require additional implementation |
| SQL maintenance | PostgreSQL VACUUM/ANALYZE availability differs from the SQLite engine's administrative maintenance methods |
| Roles/privileges/RLS | Native GRANT/REVOKE and RLS are absent; platform access policy is a separate implementation |
| Extensions | Do not advertise binary PostgreSQL extension compatibility or PostGIS because pgwire exists |
| Replication | PostgreSQL replication protocols are not implied by self-hosted Turso client synchronization |

## Permissions and filesystem effects

Enforce connect, resolved data/schema actions, function/virtual-table access, and imports using the shared policy service and native authorizer. Privileges apply to schema lookup and indirect effects, not just a table name mentioned in the original SQL.

Remote COPY FROM a filename is denied unless an explicit operator-managed import capability resolves an authorized staged asset. The dashboard/CLI/MCP import operation can ingest a file without granting the caller general filesystem access. Schema attachment/creation must remain inside the database bundle. PostgreSQL catalog queries cannot disclose databases or credentials outside the principal's visibility.

## Caching and compatibility testing

Cache plans only with session, dialect, schema, generation, policy epoch, parameter types, and native revision keys. A portal retains the correct native statement and execution state until complete, closed, or expired. Restore invalidates old portals with a precise error.

Test real clients individually: psql, libpq, a Go PostgreSQL driver, and representative language/ORM clients. Record exact client versions, parameters, modes, unsupported statements, and expected errors. Passing a simple SELECT does not establish ORM or pg_dump compatibility. Use upstream PostgreSQL conformance and dump-fuzzer workflows without changing golden tests to match the product.

## Release obligations

Verify independent concurrent sessions, no cross-user settings or transaction leakage, authentication failures, policy revocation, prepared statements, decimal/array encoding, SQLSTATE preservation, cancellation races, idle transaction expiry, file-access rejection, and PG multi-file backup/restore. A missing bridge capability reports unavailable; the UI must not silently downgrade a PostgreSQL database to SQLite.
