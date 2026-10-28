# Standalone operation and recovery runbooks

All Mira commands and operations here are proposed product interfaces. They are not currently implemented upstream commands. Execute the equivalent dashboard/API/CLI/MCP operation after implementation and qualification. The same permissions and lifecycle invariants apply.

## Install and start

1. Obtain the artifact for a qualified OS/architecture and verify its published digest/signature.
2. Choose a dedicated local data directory/account and persistent storage.
3. Validate configuration, local control endpoint, listener addresses, and certificate/key references.
4. Start the executable and complete local owner bootstrap through setup CLI or dashboard.
5. Create a database with explicit dialect and persistence mode; obtain the supported connection details.
6. Verify restart persistence, access controls, backup destination, and diagnostic visibility before relying on the installation.

Do not require a managed-cloud account or runtime dependency download. Local data can be used offline. Remote app connectivity uses the operator's own networking.

## Operate many databases

Use the paginated catalog to list/search databases. Inspect catalog count separately from open native handles and active connections. When resource pressure occurs, inspect pinned transactions/jobs, idle-eviction state, native memory, file descriptors, storage reserve, and per-principal budgets. Increase hardware/configured capacity or reduce active workload; a database-count license upgrade is not part of this product.

## Create restricted application/agent access

Create a distinct principal, grant its organization/group/database/object actions, issue an expiring supported credential, and return connection instructions through an explicit credential-creation result. Test allowed and denied operations through the actual client interface. An owner can grant complete agent authority. Ordinary list/get/diagnostic operations do not reveal existing raw credentials.

Invitations support a local one-time redeem code and expiry. External delivery is an optional operator integration; do not block local team administration on an email service.

## Back up and verify

Choose a configured local/mounted destination, select databases or installation scope, and start a backup job. Follow snapshot/flush/archive steps and verify the completed manifest, hashes, keys/format references, and integrity result. Schedule retention only after a restoration test. A backup file marked complete must survive abrupt process exit under its declared durability contract.

## Restore without replacing current data

Choose a retained backup/revision, restore-as-new, a new display name/slug, and required key references. The job reconstructs a staged generation, verifies it, and publishes a new database identity. Query expected data and schema under the correct dialect. Preserve the original until the user explicitly chooses to delete it.

## Replace a database generation

Authorize replacement and supply expected database/generation revisions. Resolve retained snapshot/history dependencies, reconstruct and verify a staged generation, block new sessions, drain/cancel active work, publish the new generation through the durable lifecycle protocol, and invalidate old cursors/sync sessions. Preserve the previous generation according to policy. A failed verification never becomes the active database.

## Recover a deleted database

List recoverable resources, inspect name conflicts and required objects/keys, and restore the selected identity through a lifecycle job. If the original slug was reused, choose a new slug without granting old credentials access to the unrelated resource. Expired/purged history returns an explicit non-recoverable result.

## Recover after a crash

Restart the same qualified binary or a compatible newer binary against the installation. Let catalog/file reconciliation finish before readiness. Inspect incomplete jobs and commit certainty. Verify history boundaries and native integrity for affected databases. Do not manually delete WAL/MVCC logs to clear a startup error. A diagnostic bundle identifies exact files/versions/generations without publishing secrets.

## Disk full or archive failure

Stop admitting writes that cannot meet their durability/history promises. Preserve committed history and recovery roots. Inspect staging, expired unreferenced artifacts, active retention pins, and configured reserve. Use the platform cleanup operation for eligible objects. Do not delete live logs, encryption references, or branch bases by hand. Resume only after reconciliation verifies the required archive and storage state.

## Lost owner credentials

Provide an explicit local recovery operation requiring the operating-system account authorized to administer the installation and access to its protected recovery material. Record the recovery and revoke affected old sessions/credentials. A public HTTP endpoint cannot reset the owner merely because the requester knows an instance ID. The exact recovery mechanism/key custody is DEC-011 and must be implemented before qualification.

## Replace the whole installation

An authenticated owner or owner-authorized agent can submit installation_restore against a verified recovery plan. This operation stages the replacement and records a protected recovery intent outside the catalog being replaced. It acknowledges its durable job before draining. A same-executable recovery mode acquires the installation lock only after the old server releases it; two database owners never overlap. It verifies staged content again, publishes through a recoverable pointer/directory protocol, then restarts normal service. The protected recovery record retains the outcome even if the restored catalog predates the initiating job.

The request chooses credential handling explicitly. preserve_same_instance requires a proven same-instance recovery and retained signing/key references; revoke_restored invalidates restored network credentials and uses protected local recovery material to establish access. A cloned installation receives a new identity and cannot silently preserve old authority. The client reconnects after the planned outage using the selected credential policy. Process/service startup and recovering a completely non-running installation remain local OS operations. This handoff needs crash tests at every stop, lock, pointer, catalog, and restart boundary before advertisement.

## Rotate access credentials or certificates

Create a replacement access credential, update the consuming application, verify access, then revoke the old credential. Certificate reload validates the full configuration before replacement. At-rest encryption key changes are a separate generation transformation; editing a key reference is not a valid re-encryption operation.

## Inspect synchronization problems

Check client database/generation, negotiated protocol/dialect, last acknowledged revision, retained-history floor, pending bootstrap, policy/credential state, and server resource pressure. If history or generation changed, use the supported rebootstrap path. Do not reset a cursor to zero and pretend it is a valid incremental continuation.

## Upgrade

Capture a verified pre-upgrade backup, build/capability versions, and key references. Validate the new artifact and catalog/storage compatibility. Drain the server, complete or stop bounded jobs, install the new executable through the operator's service mechanism, and allow migration/recovery. Verify readiness, both SQL interfaces, MCP, permissions, and backup restoration. Follow documented downgrade compatibility; replacing a binary alone cannot undo a storage/catalog migration.

## Graceful stop

Issue the owner-authorized instance stop operation or the configured OS signal/service stop. The server records and acknowledges the request, drains, cleans sessions, flushes required state, and releases the instance lock. A client disconnect does not prove shutdown completed; inspect the service/process and operation outcome through the supported local mechanism.
