# Configuration and self-hosted deployment

## Delivery contract

Distribute one executable per qualified OS/architecture. The operator does not install Go, Cargo, Node, an external database daemon, or downloaded engine libraries to run it. Build tools are developer/release inputs. Persistent data and optional certificate/key files are ordinary installation files created or supplied after download.

The default binding integration can automatically extract its bundled native library into a private, versioned cache before loading it in process. This is not a separate engine installation or a second server. Cache contents can be recreated from the executable; live engine handles must be closed before deleting/replacing an in-use library, particularly on Windows. Startup requires a qualified writable cache location. Document and measure this runtime disk footprint instead of promising literal zero additional files.

The product can run on a laptop, bare metal, dedicated server, or VPS. A single instance may serve remote applications, multiple teammates, and many databases. It remains one server process owning one installation directory.

## Configuration source and precedence

Use JSON configuration with a published schema. Precedence is explicit command-line options, explicitly named environment overrides, configuration file, then compiled defaults. Secret material is loaded through protected references rather than ordinary command-line strings. Unknown keys fail validation. Overrides are reported by source without printing raw secrets.

The example and schema are [mira.config.json](examples/mira.config.json) and [config.schema.json](contracts/config.schema.json). These are proposed configuration contracts.

## Default decisions

| Setting | Proposed default/meaning |
|---|---|
| HTTP listener | 127.0.0.1:8090 |
| PostgreSQL listener | 127.0.0.1:5433; explicit enable/authentication policy |
| Data directory | Explicit --data-dir or documented OS application-data directory |
| Public exposure | Operator opt-in; validate TLS/auth policy before non-loopback admission |
| Database-count quota | Unset; no vendor quota |
| Active handles/connections | Bounded operator-tunable budgets, separate from catalog count |
| Statement/result limits | Bounded; proposed values in example are configuration examples, not performance guarantees |
| External identity/email | Optional; local credentials and redeem-code invitations remain functional |
| Backups | Local configured root; no provider provisioning |
| MCP | Bundled; authenticated HTTP endpoint and explicit stdio proxy mode |
| Experimental features | Off unless individually enabled for a database/provider capability |

## Configuration groups

instance: data directory, identity/lock behavior, environment label, logging source.

http: listen address, origin/Host validation, trusted proxy addresses, request and streaming budgets, TLS references.

postgres: enable/listen, TLS policy, credential methods, message size, connections, session/portal/transaction deadlines, tested protocol modes.

security: signing-key references, password/SCRAM parameters, credential/session expiry, rate limits, network allow rules, external JWKS configuration, trusted extension roots.

resources: global native/Go memory budgets, active databases, connections, active queries, queue length, per-database cache budget, file-descriptor reserve, background concurrency, query/result limits. No fixed commercial database-count field is introduced.

history/backups: enabled policies, archive root, retention, disk reserve, checkpoint coordination, local backup roots/schedules, verification, snapshot/client retention budgets.

sync/changes: protocol/encoding capabilities, maximum bootstrap size/concurrency, client retention, long-poll limits, subscription queues, CDC retention.

mcp: endpoint/transport settings, supported protocol revisions, discovery pagination and result limits. Application permissions are configured through the same identity/grant service.

observability: metrics access, audit/log retention, SQL text capture policy, diagnostics limits.

## Reload behavior

Validate the entire proposed configuration before publication. Classify fields as live-reload, new-session-only, database-reopen, or process-restart. Report required actions before applying incompatible changes. Apply one revisioned configuration snapshot; avoid half-updating listeners and authorization state.

Secrets can be replaced through protected references with identity checks. Changing an encryption key reference does not automatically re-encrypt existing data. Changing a data root is an explicit offline migration, not a live configuration tweak.

## OS integration

On Unix, the process runs under a dedicated operator account, with a private data root, OS lock, and local Unix socket/control permission rules. On Windows, use a dedicated service/user account, ACL-protected paths, an OS lock, and a named pipe with restrictive ACLs. Public network listeners are configured independently of local control.

Document systemd and Windows Service registration through supported product helpers or operator service configuration. Service helpers must state permissions and paths clearly. They do not silently install a visible background console. Signals/control requests map to the application's draining/shutdown protocol.

The filesystem must support the durability, locking, and rename behavior qualified by the release. A mounted network filesystem is not automatically safe merely because it has a path. Record tested local filesystems and reject/flag unsupported deployment combinations precisely.

## Bare-metal/VPS operation

The operator supplies CPU, memory, persistent storage, DNS/network routing if desired, and TLS references. Bind endpoints to the intended interfaces. Configure firewall/reverse proxy rules, then validate authentication through each exposed protocol. Public exposure does not create an additional cloud product or cluster.

The product serves many databases through the same configured endpoints, selecting immutable database identity through authenticated routes or PostgreSQL startup database selection. A separate listening port/process for every database is not required.

## Offline and agent operation

Local administration, SQL, dashboard assets/help, credentials, snapshots, backups, and native engine loading work without an external service account or runtime download. Self-hosted synchronization requires connectivity between client and installation. External JWT verification needs the configured key-fetch/cache behavior; failure does not silently disable verification. Agents connect using credentials authorized by the installation owner.

## Deployment verification

Verify bootstrap, first-owner race prevention, restart with persistent data, concurrent independent databases, remote SQL/PG/MCP authentication, graceful shutdown, backups, full restore, disk pressure, limits, and configuration reload. Publish exact tested OS/architecture/filesystem/client versions; unsupported combinations remain explicit.
