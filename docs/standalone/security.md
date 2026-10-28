# Identity, authorization, and local security

## Scope

Security controls protect the database platform and its data across the dashboard, CLI, HTTP SQL, PostgreSQL, MCP, imports, sync, subscriptions, and background jobs. The operating-system account/root administrator remains the trust boundary for a self-hosted process. Platform controls do not claim to protect data from an administrator who can read process memory or replace binaries and files.

These controls implement the user's account/permission requirements. They do not introduce a separate mandatory approval workflow for every agent action.

## Principals and credentials

Principals are human, agent, or service. Each has an immutable ID, display label, enabled/disabled state, membership/role assignments, and credential records. Agents should have distinct identities so audit and revocation are attributable, but an owner may grant an agent the same effective owner authority as a human.

Local human passwords use a modern password-hash implementation selected and pinned during implementation, with a versioned parameter record and constant-time verification. PostgreSQL service credentials use a separate SCRAM verifier record. Random opaque tokens are stored hashed; signed database tokens carry an issuer, audience, principal ID, credential ID, resource scope, expiry, and policy version binding. Raw secrets are returned only by explicit credential-issuance/rotation operations and excluded from ordinary list/get/audit results.

Secret issuance needs a delivery contract distinct from ordinary resource idempotency. Generate the secret once, store its verifier/hash, and retain an encrypted issuance envelope under a protected local delivery key for a short bounded retry window. Bind retrieval to the original principal, credential scope, operation, and idempotency key; exclude the envelope from general job/audit/catalog exports. The same request can retrieve the same envelope during that window. After expiry, return the existing credential metadata with secret_delivery_expired and require explicit rotation if delivery was lost; never recover an old secret from a hash or issue duplicate active credentials silently. Backups preserve key references and credential hashes according to the selected recovery policy, not plaintext delivery envelopes.

Browser sessions use protected cookies, CSRF defenses, origin validation, and explicit expiry/revocation. MCP/API use their configured credential mechanisms; they do not inherit an ambient browser cookie. The local control transport authenticates both OS endpoint access and a configured application credential. First-owner bootstrap is one-time and local.

## Roles and scopes

Built-in platform roles are owner, admin, member, and viewer with documented action sets. Custom grants may narrow organization, group, database, schema, table, action, and optionally function/extension scope. Credentials cannot grant more authority than their principal. A credential's database ID is immutable even if a slug is reused.

The [operation registry](contracts/operations.json) declares the required service permission per operation. User SQL requires a second native-level check against resolved effects. Administrative database.delete and SQL DELETE FROM are distinct permissions. Managing a token is not equivalent to knowing an existing raw token.

Recommended primitive data actions are data.read, data.insert, data.update, data.delete; schema.create, schema.alter, schema.drop; query.connect; and separate platform actions for history, backup, recovery, sync, maintenance, accounts, settings, and extensions. Permission strings and their exact scopes are versioned in the operation registry and native policy compiler.

Built-in role defaults are concrete and scope-bound:

| Role | Default authority |
|---|---|
| Installation owner | Every registered application action and native data/schema action; can delegate owner-equivalent authority to an agent; still obeys deliberate deletion protection until changing it explicitly |
| Organization admin | Administration, credentials, data/schema, lifecycle, recovery, and observability for that organization; cannot configure/stop/recover the installation or cross into another organization |
| Member | Viewer capabilities in assigned scopes and permission to create databases in permitted groups; receives explicit creator grants on new databases rather than authority over other members' data |
| Viewer | Resource/schema inspection, query.connect, and data.read in assigned database/group/organization scopes; no writes, file import, credential issuance, physical sync download, or administrative changes |

Custom roles use explicit permission sets. Effective authority is the intersection of active principal grants, credential scope, resource scope, and current native action policy. Additive grants must not defeat database read/write blocks or immutable generation boundaries. There is no implicit deny-precedence language in version 1: a narrower credential restricts authority, while an explicit resource block is a separate mandatory gate. A role change advances policy epochs. All final-owner updates serialize and verify that at least one enabled installation owner remains; a database creator cannot issue a credential broader than the authority they actually received.

## Native enforcement is required

The audited core lacks a working prepare-time authorizer. An application-only whitelist of SELECT/INSERT keywords is insufficient for the promised table/action permissions. Implement generic hooks after name resolution and before execution, plus runtime checks for effects whose target is determined later.

Check direct tables, views/base tables, triggers, cascading actions, indexes/schema changes, virtual tables, functions, attached namespaces, and host file effects. The initial policy is invoker-based: accessing a view does not silently grant access to its underlying tables or a trigger's write targets. Definer-security semantics require a distinct later decision and cannot be implied by a view grant.

Every native session carries trusted principal, credential, database/generation, policy epoch, and capability context. Re-preparation and schema changes recheck authorization. Cached programs cannot retain an obsolete grant after revocation. Native internal operations are narrowly identified service operations rather than a global bypass flag exposed to user SQL.

## Revocation and long operations

Increment relevant policy/credential epochs atomically in the catalog. Admission and each new statement/continuation verify those epochs. Revoke active sessions and interrupt affected in-flight statements when required by policy. Already transmitted data cannot be retracted; already committed writes remain committed. Report those boundaries accurately.

Jobs record the initiating principal/credential and reauthorize at execution and before destructive publication. Removing a principal's permission while a restore is queued must not leave the restore running indefinitely with forgotten privilege. Owner-scheduled recurring maintenance uses an explicitly delegated service authority with attributable ownership.

## File and code execution boundaries

- User-provided identifiers are not paths.
- Public APIs use uploaded asset IDs, snapshot IDs, database IDs, and configured root IDs.
- Restrict COPY, ATTACH, CSV virtual tables, extension loading, file-capable functions, diagnostics export, and backup paths.
- Treat arbitrary native extensions as operator-trusted code. Provide compatible extension registration without claiming a sandbox.
- Restricted SQL cannot create an extension/function that bypasses its policy.
- Do not add arbitrary operating-system shell execution to MCP under the phrase full platform control.

The owner may configure additional local directories through explicit platform settings. These changes require owner authority and audit, not an automatic per-command interactive confirmation requirement. OS canonicalization and opened-file identity checks prevent traversal and reparse races.

Bundled native loading uses a protected per-account cache with full build/digest identity, atomic extraction and digest verification, safe concurrent initialization, and explicit native ABI matching. User SQL/MCP cannot choose an arbitrary library path or switch loading to a system search path. Test cache corruption, symlink/reparse substitution, interrupted extraction, concurrent starts, DLL search behavior, and permission failures. The source loader is a starting point; its presence is not evidence these product hardening requirements have passed.

## Network exposure

Default application and PostgreSQL addresses are loopback. Operators may expose them on bare metal/VPS/private networks using explicit configuration. Validate listen addresses, trusted reverse proxies, TLS certificates, origin rules, and IP allow rules at startup/reload. Host/Origin headers cannot select an unauthorized instance or bypass MCP authentication.

HTTP dashboard sessions, SQL connections, MCP credentials, sync page access, downloads, and health/diagnostic endpoints have separate declared access policies. Liveness may be minimal public information; readiness and detailed diagnostics do not reveal database names or keys to unauthenticated callers.

## Encryption

Encryption support is capability-aware and experimental where upstream marks it so. A key reference resolves through protected local storage or an operator-configured provider. Never include a raw encryption key in URLs, SQL logs, process arguments, audit entries, or downloadable connection examples.

Determine coverage separately for base pages, WAL, MVCC logs, PG schema files, FTS indexes, history objects, snapshots, catalog, and diagnostics. Encrypt archive objects independently when native encryption does not cover them. Key rotation, if exposed, is a controlled generation transformation with verification; do not invent an unimplemented native PRAGMA.

## Auditing and logging

Record actor, credential ID, interface, operation ID, database/generation, request/job IDs, outcome, commit certainty, counts, durations, and policy revision. Redact passwords, raw tokens, key bytes, bind values by default, and result payloads. Operator opt-in SQL capture has explicit retention and access controls.

Use ordered event IDs. A local hash chain detects accidental modification/gaps but is not tamper proof against a root administrator who can rewrite the chain. Durable lifecycle intents provide crash reconciliation; an audit row alone is not a transaction receipt for target-database writes.

## Adversarial acceptance cases

Test multi-statement smuggling, CTE mutations, view/trigger/cascade effects, schema races, prepared-plan reuse after revoke, cross-organization IDs, alias reuse, leaked batons, forged JWT settings, COPY/ATTACH traversal, CSV/native extension access, symlink/reparse races, compressed-body bombs, result backpressure, malformed protocol packets, and disconnected clients during commit. All interfaces must produce equivalent permission outcomes.
