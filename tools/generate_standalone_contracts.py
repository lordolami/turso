"""Generate the proposed standalone design inventories; does not build Mira.

Run from any directory. Output is deterministic for the audited source tree.
Keep operation definitions here and review generated JSON in the same change.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "standalone"
OUT = DOCS / "contracts"
REVISION = "017ea183c2a323a66d515448e4df464b6181bb36"


def find_source_root() -> Path | None:
    configured = os.environ.get("MIRA_TURSO_SOURCE")
    if configured:
        return Path(configured).expanduser().resolve()
    for candidate in (ROOT, ROOT.parent / "turso-engine"):
        if (candidate / "core" / "database.rs").is_file():
            return candidate
    return None


SOURCE_ROOT = find_source_root()


def require_source_root() -> Path:
    if SOURCE_ROOT is None:
        raise ValueError("Source regeneration requires ../turso-engine or MIRA_TURSO_SOURCE pointing to the audited checkout")
    return SOURCE_ROOT

# id | method | path | permission | execution | input fields | result | purpose
# R=read, M=synchronous mutation, J=durable job. ! marks required input.
# Transport authentication always supplies principal identity out of band.
OPERATIONS = """
instance.get|GET|/api/v1/instance|instance.read|R||instance|Inspect installation identity, versions, listeners, and state
instance.capabilities|GET|/api/v1/capabilities|instance.read|R||capabilities|Discover compiled and enabled features with dialect-specific status
instance.setup|POST|/api/v1/setup|bootstrap.redeem|M|bootstrap_code:secret! owner_name:text! password:secret!|principal|Atomically establish the first owner using the local bootstrap credential
instance.config_get|GET|/api/v1/config|instance.configure|R||configuration|Read effective configuration with secret references and override sources
instance.config_validate|POST|/api/v1/config/validate|instance.configure|R|configuration:object!|validation|Validate a complete candidate configuration and classify reload effects
instance.config_update|PUT|/api/v1/config|instance.configure|M|configuration:object! expected_revision:revision!|configuration|Publish a validated revision of installation settings
instance.drain|POST|/api/v1/instance/drain|instance.operate|J|deadline_ms:positive!|job|Stop new work and drain active sessions safely
instance.shutdown|POST|/api/v1/instance/shutdown|instance.operate|J|deadline_ms:positive!|job|Persist shutdown intent and stop after safe draining
instance.service_instructions|GET|/api/v1/instance/service-instructions|instance.operate|R|platform:platform!|artifact|Generate service registration instructions for the selected operating system
organizations.list|GET|/api/v1/organizations|organization.read|R|cursor:text limit:limit|organizations[]|List visible organizations
organizations.create|POST|/api/v1/organizations|organization.create|M|name:text! slug:slug!|organizations|Create an organization with explicit initial ownership
organizations.get|GET|/api/v1/organizations/{organization_id}|organization.read|R||organizations|Inspect one organization and its revision
organizations.update|PATCH|/api/v1/organizations/{organization_id}|organization.update|M|name:text slug:slug expected_revision:revision!|organizations|Update organization labels with revision checking
organizations.delete|DELETE|/api/v1/organizations/{organization_id}|organization.delete|J|expected_revision:revision!|job|Delete an empty organization or return its remaining dependencies
groups.list|GET|/api/v1/organizations/{organization_id}/groups|group.read|R|cursor:text limit:limit|groups[]|List groups and inherited policy defaults
groups.create|POST|/api/v1/organizations/{organization_id}/groups|group.create|M|name:text! slug:slug! defaults:object|groups|Create a database group
groups.get|GET|/api/v1/groups/{group_id}|group.read|R||groups|Inspect a group and policy inheritance
groups.update|PATCH|/api/v1/groups/{group_id}|group.update|M|name:text defaults:object expected_revision:revision!|groups|Update group labels and defaults
groups.delete|DELETE|/api/v1/groups/{group_id}|group.delete|J|expected_revision:revision!|job|Delete an empty group with dependency checks
principals.list|GET|/api/v1/principals|principal.read|R|cursor:text limit:limit|principal[]|List visible platform users and service or agent principals
principals.create|POST|/api/v1/principals|principal.create|M|kind:principal_kind! name:text!|principal|Create a platform identity without issuing broad credentials implicitly
principals.get|GET|/api/v1/principals/{principal_id}|principal.read|R||principal|Inspect a principal and current status
principals.update|PATCH|/api/v1/principals/{principal_id}|principal.update|M|name:text enabled:bool expected_revision:revision!|principal|Rename or disable a principal and invalidate affected authority
principals.password_set|PUT|/api/v1/principals/{principal_id}/password|principal.credentials|M|password:secret! expected_revision:revision!|receipt|Replace a local password through an encrypted authenticated channel
principals.delete|DELETE|/api/v1/principals/{principal_id}|principal.delete|M|expected_revision:revision!|receipt|Tombstone a principal while preserving audit attribution and owner invariants
memberships.list|GET|/api/v1/organizations/{organization_id}/memberships|membership.read|R|cursor:text limit:limit|membership[]|List organization memberships
memberships.set|PUT|/api/v1/organizations/{organization_id}/memberships/{principal_id}|membership.manage|M|role_id:uuid! expected_revision:revision!|membership|Assign an organization role without removing the final owner
memberships.remove|DELETE|/api/v1/organizations/{organization_id}/memberships/{principal_id}|membership.manage|M|expected_revision:revision!|receipt|Remove membership and advance policy epochs
invitations.create|POST|/api/v1/organizations/{organization_id}/invitations|membership.manage|M|role_id:uuid! expires_at:timestamp!|issued_secret|Create a locally redeemable invitation and return its code once
invitations.list|GET|/api/v1/organizations/{organization_id}/invitations|membership.read|R|cursor:text limit:limit|invitation[]|List invitation status without raw codes
invitations.redeem|POST|/api/v1/invitations/redeem|invitation.redeem|M|code:secret!|membership|Redeem an unexpired one-use invitation as the authenticated identity
invitations.revoke|DELETE|/api/v1/invitations/{invitation_id}|membership.manage|M|expected_revision:revision!|receipt|Revoke an outstanding invitation
roles.list|GET|/api/v1/roles|role.read|R|organization_id:uuid cursor:text limit:limit|role[]|List built-in and custom roles
roles.create|POST|/api/v1/roles|role.manage|M|organization_id:uuid name:text! permissions:texts!|role|Create a role from known primitive permissions
roles.update|PATCH|/api/v1/roles/{role_id}|role.manage|M|name:text permissions:texts expected_revision:revision!|role|Update a role and invalidate compiled policies
roles.delete|DELETE|/api/v1/roles/{role_id}|role.manage|M|expected_revision:revision!|receipt|Delete an unreferenced custom role
credentials.list|GET|/api/v1/credentials|credential.read|R|principal_id:uuid cursor:text limit:limit|credential[]|List credential metadata and expiry without exposing secrets
credentials.issue|POST|/api/v1/credentials|credential.issue|M|principal_id:uuid! name:text! kind:credential_kind! scopes:objects! expires_at:timestamp!|issued_secret|Issue a scoped opaque, signed, or PostgreSQL SCRAM credential for a user, service, or agent
credentials.get|GET|/api/v1/credentials/{credential_id}|credential.read|R||credential|Inspect a credential fingerprint and permitted scopes
credentials.revoke|DELETE|/api/v1/credentials/{credential_id}|credential.revoke|M|expected_revision:revision!|receipt|Revoke a credential and invalidate active sessions and streams
credentials.rotate|POST|/api/v1/credentials/{credential_id}/rotate|credential.issue|M|expected_revision:revision! overlap_ms:positive|issued_secret|Issue a replacement secret with a bounded explicit overlap window
auth.login|POST|/api/v1/auth/login|auth.authenticate|M|name:text! password:secret!|issued_secret|Authenticate a local platform user under rate limits
auth.logout|POST|/api/v1/auth/logout|auth.session|M||receipt|Revoke the current application login session
auth.whoami|GET|/api/v1/auth/whoami|auth.session|R||principal|Inspect the authenticated principal and credential scope
auth.sessions|GET|/api/v1/auth/sessions|auth.session|R|cursor:text limit:limit|login_session[]|List the caller's login sessions or those permitted by administration authority
auth.session_revoke|DELETE|/api/v1/auth/sessions/{login_session_id}|auth.session|M||receipt|Revoke one permitted login session
identity_providers.list|GET|/api/v1/identity-providers|identity_provider.manage|R||identity_provider[]|Inspect configured external JWT issuers and key-cache health
identity_providers.put|PUT|/api/v1/identity-providers/{identity_provider_id}|identity_provider.manage|M|issuer:text! audience:texts! jwks_url:text! mapping:object! expected_revision:revision!|identity_provider|Configure a validated external identity issuer with network policy
identity_providers.delete|DELETE|/api/v1/identity-providers/{identity_provider_id}|identity_provider.manage|M|expected_revision:revision!|receipt|Remove an external identity provider and invalidate its derived sessions
grants.list|GET|/api/v1/grants|grant.read|R|resource_id:uuid principal_id:uuid cursor:text limit:limit|grant[]|List visible grants and inheritance sources
grants.create|POST|/api/v1/grants|grant.manage|M|principal_id:uuid! resource_type:text! resource_id:uuid! actions:texts! selector:object|grant|Grant resolved actions within the grantor's authority
grants.revoke|DELETE|/api/v1/grants/{grant_id}|grant.manage|M|expected_revision:revision!|receipt|Revoke a grant and advance policy epochs
grants.explain|POST|/api/v1/grants/explain|grant.read|R|principal_id:uuid! resource_id:uuid! action:text!|authorization|Explain an effective permission without leaking inaccessible objects
databases.list|GET|/api/v1/databases|database.read|R|organization_id:uuid group_id:uuid cursor:text limit:limit|database[]|List cataloged databases without opening dormant engine handles
databases.create|POST|/api/v1/databases|database.create|J|organization_id:uuid! group_id:uuid name:text! slug:slug! dialect:dialect! provider:provider! persistence:persistence! template_id:uuid snapshot_id:uuid native_options:object limits:object encryption_key_ref:text history_policy:object sync_policy:object|job|Create and verify an independent database generation with explicit native options and source dependencies
databases.get|GET|/api/v1/databases/{database_id}|database.read|R||database|Inspect immutable identity, state, generation, and resource usage
databases.update|PATCH|/api/v1/databases/{database_id}|database.update|M|name:text slug:slug group_id:nullable_uuid expected_revision:revision!|database|Change labels or group placement without renaming storage files
databases.capabilities|GET|/api/v1/databases/{database_id}/capabilities|database.read|R||capabilities|Inspect the exact provider, dialect, build, and generation capabilities
databases.policy_set|PUT|/api/v1/databases/{database_id}/policy|database.policy|M|read_blocked:bool! write_blocked:bool! deletion_protected:bool! limits:object! expected_revision:revision!|database|Set operator resource controls and deletion protection
databases.move|POST|/api/v1/databases/{database_id}/move|database.update|M|organization_id:uuid! group_id:nullable_uuid expected_revision:revision!|database|Transfer catalog ownership after checking both source and destination authority
databases.delete|DELETE|/api/v1/databases/{database_id}|database.delete|J|expected_revision:revision! expected_generation_id:uuid!|job|Drain a database and move its retained bundle to trash
databases.connections|GET|/api/v1/databases/{database_id}/connections|database.connect|R||connection_info|Return authenticated endpoint templates and supported client modes
databases.sessions|GET|/api/v1/databases/{database_id}/sessions|database.inspect|R|cursor:text limit:limit|execution_session[]|Inspect authorized active sessions without raw credentials
databases.session_terminate|DELETE|/api/v1/databases/{database_id}/sessions/{session_id}|database.operate|J|expected_generation_id:uuid!|job|Interrupt and drain an owned execution session safely
query.execute|POST|/db/{database_id}/query|query.connect|M|sql:sql! parameters:values mode:query_mode! expected_generation_id:uuid! timeout_ms:positive max_rows:positive max_bytes:positive session_id:uuid|query_result|Execute parameterized dialect-specific SQL under resolved native action grants
query.script|POST|/db/{database_id}/script|query.connect|M|statements:statements! atomic:bool! failure_policy:failure_policy! expected_generation_id:uuid! timeout_ms:positive|script_result|Execute an explicit bounded statement list with per-statement binds and declared transaction semantics
query.explain|POST|/db/{database_id}/explain|query.connect|M|sql:sql! parameters:values expected_generation_id:uuid! analyze:bool|query_plan|Explain a statement; execution analysis additionally requires its actual effects
query.cancel|POST|/api/v1/queries/{query_id}/cancel|query.cancel|M||receipt|Signal native cancellation without freeing running state
query.cursor_fetch|POST|/api/v1/query-cursors/{cursor_id}/fetch|query.connect|R|limit:limit!|query_result|Fetch a bounded page from the principal- and generation-bound cursor
query.cursor_close|DELETE|/api/v1/query-cursors/{cursor_id}|query.connect|M||receipt|Release a query cursor and its retained native references
sessions.begin|POST|/db/{database_id}/sessions|query.connect|M|expected_generation_id:uuid! transaction_mode:transaction_mode! timeout_ms:positive|execution_session|Create a principal-bound explicit SQL transaction session
sessions.get|GET|/api/v1/execution-sessions/{session_id}|query.connect|R||execution_session|Inspect transaction state and commit certainty
sessions.commit|POST|/api/v1/execution-sessions/{session_id}/commit|query.connect|M||receipt|Commit a transaction and report its known or uncertain durable outcome
sessions.rollback|POST|/api/v1/execution-sessions/{session_id}/rollback|query.connect|M||receipt|Roll back a live transaction session and release resources
sessions.close|DELETE|/api/v1/execution-sessions/{session_id}|query.connect|M||receipt|Close a session after safe transaction cleanup
schema.inspect|GET|/api/v1/databases/{database_id}/schema|schema.read|R|namespace:text kind:text cursor:text limit:limit|schema_object[]|Inspect resolved tables, views, indexes, triggers, types, and namespaces
schema.object_get|GET|/api/v1/databases/{database_id}/schema/{object_id}|schema.read|R||schema_object|Read object DDL, columns, constraints, dependencies, and native identity
schema.apply|POST|/api/v1/databases/{database_id}/schema/apply|schema.manage|J|sql:sql! expected_schema_revision:revision! expected_generation_id:uuid! atomic:bool!|job|Apply authorized DDL with explicit atomicity and capability checks
schema.diff|POST|/api/v1/schema/diff|schema.read|R|source_database_id:uuid! target_database_id:uuid!|schema_diff|Compare compatible schemas and return explicit unsupported conversions
templates.list|GET|/api/v1/templates|template.read|R|cursor:text limit:limit|template[]|List reusable dialect-specific schema templates
templates.create|POST|/api/v1/templates|template.manage|M|organization_id:uuid name:text! dialect:dialect! sql:sql!|template|Create a versioned template with checksum and required capabilities
templates.get|GET|/api/v1/templates/{template_id}|template.read|R||template|Inspect template SQL and compatibility requirements
templates.update|PUT|/api/v1/templates/{template_id}|template.manage|M|sql:sql! expected_revision:revision!|template|Publish a checked new template revision
templates.delete|DELETE|/api/v1/templates/{template_id}|template.manage|M|expected_revision:revision!|receipt|Delete an unused template while retaining applied migration evidence
migrations.list|GET|/api/v1/databases/{database_id}/migrations|migration.read|R|cursor:text limit:limit|migration[]|List migration checksums, outcomes, and schema revisions
migrations.plan|POST|/api/v1/databases/{database_id}/migrations/plan|migration.read|R|asset_id:uuid!|migration_plan|Validate migration ordering, checksums, dependencies, and capabilities
migrations.apply|POST|/api/v1/databases/{database_id}/migrations/apply|migration.apply|J|asset_id:uuid! expected_generation_id:uuid! expected_schema_revision:revision! atomic:bool!|job|Apply an immutable migration bundle with target-database receipts
migrations.group_apply|POST|/api/v1/groups/{group_id}/migrations/apply|migration.apply|J|asset_id:uuid! database_ids:uuids! failure_policy:failure_policy!|job|Apply a migration to selected databases with individual outcomes and bounded concurrency
search.capabilities|GET|/api/v1/databases/{database_id}/search/capabilities|schema.read|R||capabilities|Inspect JSON, array, vector, indexed-vector, and text-search support
search.index_create|POST|/api/v1/databases/{database_id}/search/indexes|schema.manage|J|definition:object! expected_schema_revision:revision! expected_generation_id:uuid!|job|Create a supported vector or full-text index through dialect-specific DDL
search.index_get|GET|/api/v1/databases/{database_id}/search/indexes/{index_id}|schema.read|R||schema_object|Inspect index configuration, readiness, and dependencies
search.index_drop|DELETE|/api/v1/databases/{database_id}/search/indexes/{index_id}|schema.manage|J|expected_schema_revision:revision! expected_generation_id:uuid!|job|Drop a permitted search index with native dependency checks
extensions.list|GET|/api/v1/extensions|extension.read|R|database_id:uuid|extension[]|List compiled and operator-approved extension capabilities
extensions.enable|POST|/api/v1/databases/{database_id}/extensions|extension.manage|J|extension_id:text! configuration:object expected_generation_id:uuid!|job|Enable an approved extension with explicit function and file-effect policy
extensions.disable|DELETE|/api/v1/databases/{database_id}/extensions/{extension_id}|extension.manage|J|expected_generation_id:uuid!|job|Disable an extension only after checking dependent schema and snapshots
assets.create_upload|POST|/api/v1/assets|asset.write|M|media_type:text! size_bytes:revision! sha256:digest intended_operation:text!|asset|Allocate a bounded staged upload
assets.write_chunk|PUT|/api/v1/assets/{asset_id}/chunks/{chunk_index}|asset.write|M|content:base64! sha256:digest!|asset|Append a checked upload chunk with strict offset and principal binding
assets.complete|POST|/api/v1/assets/{asset_id}/complete|asset.write|M|sha256:digest! size_bytes:revision!|asset|Validate and publish a completed immutable input asset
assets.get|GET|/api/v1/assets/{asset_id}|asset.read|R||asset|Inspect authorized asset state and digest
assets.read_chunk|GET|/api/v1/assets/{asset_id}/chunks/{chunk_index}|asset.read|R|limit:limit|asset_chunk|Download an authorized bounded chunk; HTTP may use raw binary framing
assets.delete|DELETE|/api/v1/assets/{asset_id}|asset.write|M||receipt|Expire an unreferenced staged or exported asset
imports.validate|POST|/api/v1/databases/{database_id}/imports/validate|data.import|J|asset_id:uuid! format:transfer_format! mapping:object expected_generation_id:uuid!|job|Inspect import data and report dialect, format, and schema errors
imports.run|POST|/api/v1/databases/{database_id}/imports|data.import|J|asset_id:uuid! format:transfer_format! mapping:object atomic:bool! expected_generation_id:uuid!|job|Import a validated SQLite file, SQL, CSV, or tabular JSON asset under native grants
exports.run|POST|/api/v1/databases/{database_id}/exports|data.export|J|format:transfer_format! selection:object! expected_generation_id:uuid!|job|Export authorized data or a consistent database bundle to an immutable asset
history.get|GET|/api/v1/databases/{database_id}/history|history.read|R|cursor:text limit:limit|history_revision[]|Inspect retained commit ranges, gaps, and timestamps
history.policy_set|PUT|/api/v1/databases/{database_id}/history/policy|history.manage|M|enabled:bool! retention:object! expected_revision:revision!|database|Configure explicit retained-history guarantees and resource budgets
history.resolve|POST|/api/v1/databases/{database_id}/history/resolve|history.read|R|timestamp:timestamp commit_revision:text|history_revision|Resolve a retained timestamp or revision to a complete native commit
history.verify|POST|/api/v1/databases/{database_id}/history/verify|history.manage|J|from_revision:text to_revision:text|job|Verify archive ordering, checksums, coverage, and required keys
history.expire|POST|/api/v1/databases/{database_id}/history/expire|history.manage|J|before_revision:text! expected_revision:revision!|job|Explicitly shorten retention after reporting affected recovery and sync roots
snapshots.list|GET|/api/v1/databases/{database_id}/snapshots|snapshot.read|R|cursor:text limit:limit|snapshot[]|List completed and in-progress consistent snapshots
snapshots.create|POST|/api/v1/databases/{database_id}/snapshots|snapshot.create|J|expected_generation_id:uuid! name:text|job|Capture a native-consistent complete file bundle
snapshots.get|GET|/api/v1/snapshots/{snapshot_id}|snapshot.read|R||snapshot|Inspect snapshot manifest, revision, dependencies, and checksums
snapshots.delete|DELETE|/api/v1/snapshots/{snapshot_id}|snapshot.delete|J|expected_revision:revision!|job|Remove a snapshot root only when dependent references permit it
snapshots.verify|POST|/api/v1/snapshots/{snapshot_id}/verify|snapshot.read|J||job|Verify a snapshot's complete bundle and native readability
branches.list|GET|/api/v1/databases/{database_id}/branches|branch.read|R|cursor:text limit:limit|branch[]|List branch lineage and shared base references
branches.create|POST|/api/v1/databases/{database_id}/branches|branch.create|J|name:text! slug:slug! source_revision:text expected_generation_id:uuid!|job|Create an independent COW database branch from a verified current or historical revision
branches.get|GET|/api/v1/branches/{branch_id}|branch.read|R||branch|Inspect a branch's database identity and immutable base manifest
branches.compare|POST|/api/v1/branches/{branch_id}/compare|branch.read|J|target_database_id:uuid! selection:object!|job|Compare authorized schema or selected data without promising an automatic merge
backup_policies.list|GET|/api/v1/backup-policies|backup.read|R|cursor:text limit:limit|backup_policy[]|List local backup schedules and destinations
backup_policies.create|POST|/api/v1/backup-policies|backup.manage|M|name:text! database_ids:uuids! destination_id:uuid! schedule:text! timezone:text! retention:object! verify:bool!|backup_policy|Create a local or mounted-storage backup policy
backup_policies.update|PATCH|/api/v1/backup-policies/{backup_policy_id}|backup.manage|M|schedule:text retention:object verify:bool enabled:bool expected_revision:revision!|backup_policy|Update policy timing, retention, or verification
backup_policies.delete|DELETE|/api/v1/backup-policies/{backup_policy_id}|backup.manage|M|expected_revision:revision!|receipt|Remove a schedule while retaining existing backup artifacts
backups.list|GET|/api/v1/backups|backup.read|R|database_id:uuid cursor:text limit:limit|backup[]|List authorized complete or failed backup artifacts
backups.create|POST|/api/v1/backups|backup.create|J|database_ids:uuids! destination_id:uuid! include_history:bool!|job|Create checksummed local backup artifacts at recorded per-database boundaries
backups.get|GET|/api/v1/backups/{backup_id}|backup.read|R||backup|Inspect backup manifest, keys, coverage, and verification state
backups.verify|POST|/api/v1/backups/{backup_id}/verify|backup.read|J||job|Restore into verification staging and check the artifact without replacing live data
backups.delete|DELETE|/api/v1/backups/{backup_id}|backup.delete|J|expected_revision:revision!|job|Delete a backup root and reclaim unreferenced objects safely
backup_destinations.list|GET|/api/v1/backup-destinations|backup.manage|R||backup_destination[]|List operator-authorized local backup roots
backup_destinations.create|POST|/api/v1/backup-destinations|instance.configure|M|name:text! local_path:text!|backup_destination|Authorize a canonical local backup root under installation-owner authority
backup_destinations.delete|DELETE|/api/v1/backup-destinations/{destination_id}|instance.configure|M|expected_revision:revision!|receipt|Remove an unused authorized destination without deleting arbitrary paths
recovery.plan|POST|/api/v1/recovery/plan|recovery.restore|R|database_id:uuid backup_id:uuid snapshot_id:uuid target_timestamp:timestamp target_revision:text mode:restore_mode!|recovery_plan|Resolve required bundle, archive, keys, capacity, and target revision before restore
recovery.restore|POST|/api/v1/recovery/restore|recovery.restore|J|plan_id:uuid! expected_revision:revision! expected_generation_id:uuid|job|Reconstruct and verify a generation before publishing a new database or replacement
recovery.installation_backup|POST|/api/v1/recovery/installation-backup|instance.recover|J|destination_id:uuid! include_databases:bool!|job|Coordinate private catalog and database manifests for installation recovery
recovery.installation_plan|POST|/api/v1/recovery/installation-plan|instance.recover|R|asset_id:uuid!|recovery_plan|Validate installation restore requirements and explicit credential identity handling
recovery.installation_restore|POST|/api/v1/recovery/installation-restore|instance.recover|J|plan_id:uuid! expected_instance_id:uuid! credential_policy:credential_policy!|job|Stage a verified whole-installation restore and hand off to a serialized same-executable recovery mode
trash.list|GET|/api/v1/trash|recovery.read|R|cursor:text limit:limit|trash[]|List recoverable deleted resources and retention deadlines
trash.restore|POST|/api/v1/trash/{trash_id}/restore|recovery.restore|J|name:text slug:slug expected_revision:revision!|job|Recover a retained database after checking current ownership and name conflicts
trash.purge|DELETE|/api/v1/trash/{trash_id}|recovery.purge|J|expected_revision:revision!|job|Permanently expire a retained root after checking branch and backup dependencies
sync.status|GET|/api/v1/databases/{database_id}/sync|sync.read|R||sync_status|Inspect protocol modes, retention, bootstrap limits, and generation identity
sync.configure|PUT|/api/v1/databases/{database_id}/sync|sync.manage|M|enabled:bool! retention:object! expected_revision:revision!|sync_status|Configure authenticated self-hosted synchronization
sync.clients|GET|/api/v1/databases/{database_id}/sync/clients|sync.read|R|cursor:text limit:limit|sync_client[]|List registered sync clients and acknowledged revisions
sync.client_revoke|DELETE|/api/v1/databases/{database_id}/sync/clients/{client_id}|sync.manage|M||receipt|Revoke a client and release its retention root according to policy
sync.bootstrap|POST|/api/v1/databases/{database_id}/sync/bootstrap|sync.download_generation|J|expected_generation_id:uuid! client_id:uuid! selection:object|job|Create a generation-bound consistent client bootstrap with whole-generation download authority
sync.pull|POST|/db/{database_id}/sync/pull|sync.download_generation|R|client_id:uuid! cursor:text! expected_generation_id:uuid! limit:limit|sync_batch|Read bounded authorized native sync updates
sync.push|POST|/db/{database_id}/sync/push|sync.write|M|client_id:uuid! batch_id:uuid! asset_id:uuid! expected_generation_id:uuid!|sync_receipt|Apply a dialect-compatible client batch with native grants and deduplication
sync.checkpoint|POST|/api/v1/databases/{database_id}/sync/checkpoint|sync.manage|J|expected_generation_id:uuid!|job|Coordinate client-safe native checkpoint and archive retention
changes.configure|PUT|/api/v1/databases/{database_id}/changes|changes.manage|M|enabled:bool! mode:cdc_mode! retention:object! expected_revision:revision!|database|Install managed CDC on every permitted connection
changes.read|GET|/db/{database_id}/changes|changes.read|R|cursor:text tables:texts limit:limit expected_generation_id:uuid!|change_batch|Read authorized committed changes with resumable bounded cursors
subscriptions.create|POST|/api/v1/databases/{database_id}/subscriptions|changes.read|M|kind:subscription_kind! sql:sql parameters:values tables:texts cursor:text expected_generation_id:uuid!|subscription|Create an authorized commit or supported live-query subscription
subscriptions.get|GET|/api/v1/subscriptions/{subscription_id}|changes.read|R||subscription|Inspect subscription cursor, policy epoch, and queue state
subscriptions.poll|POST|/api/v1/subscriptions/{subscription_id}/poll|changes.read|R|cursor:text timeout_ms:positive limit:limit|change_batch|Long-poll bounded events and signal gaps or required resynchronization
subscriptions.delete|DELETE|/api/v1/subscriptions/{subscription_id}|changes.read|M||receipt|Cancel a subscription and release retained cursors
maintenance.integrity_check|POST|/api/v1/databases/{database_id}/maintenance/integrity-check|database.maintain|J|expected_generation_id:uuid!|job|Run native integrity validation against the intended generation
maintenance.checkpoint|POST|/api/v1/databases/{database_id}/maintenance/checkpoint|database.maintain|J|expected_generation_id:uuid!|job|Checkpoint while preserving snapshots, history, and active readers
maintenance.compact|POST|/api/v1/databases/{database_id}/maintenance/compact|database.maintain|J|expected_generation_id:uuid!|job|Perform capability-supported compaction with correct generation semantics
maintenance.analyze|POST|/api/v1/databases/{database_id}/maintenance/analyze|database.maintain|J|tables:texts expected_generation_id:uuid!|job|Refresh native query statistics for authorized objects
maintenance.reindex|POST|/api/v1/databases/{database_id}/maintenance/reindex|database.maintain|J|index_ids:uuids expected_generation_id:uuid!|job|Rebuild supported indexes through native schema authorization and artifact coordination
maintenance.gc|POST|/api/v1/maintenance/gc|instance.operate|J|verify_only:bool!|job|Trace retained roots and reclaim only unreferenced local objects
maintenance.key_rotate|POST|/api/v1/databases/{database_id}/maintenance/key-rotate|database.encrypt|J|new_key_ref:text! expected_generation_id:uuid!|job|Rewrite and verify encrypted artifacts through an explicit recoverable transformation
metrics.get|GET|/api/v1/metrics|metrics.read|R|database_id:uuid|metrics|Read bounded Go, native, database, job, and resource measurements
metrics.queries|GET|/api/v1/databases/{database_id}/query-statistics|database.inspect|R|cursor:text limit:limit|query_statistic[]|Inspect authorized query statistics under SQL-redaction policy
audit.list|GET|/api/v1/audit|audit.read|R|resource_id:uuid principal_id:uuid cursor:text limit:limit|audit_event[]|Read redacted append-only audit records
logs.read|GET|/api/v1/logs|logs.read|R|cursor:text limit:limit|log_batch|Read bounded sanitized operational log records
diagnostics.create|POST|/api/v1/diagnostics|diagnostics.create|J|include_sql:bool! database_ids:uuids|job|Produce a redacted diagnostic asset with explicit sensitive-data scope
jobs.list|GET|/api/v1/jobs|job.read|R|resource_id:uuid state:text cursor:text limit:limit|job[]|List authorized durable operations
jobs.get|GET|/api/v1/jobs/{job_id}|job.read|R||job|Inspect progress, commit state, result references, and errors
jobs.events|GET|/api/v1/jobs/{job_id}/events|job.read|R|cursor:text limit:limit|job_event[]|Read resumable job progress events
jobs.cancel|POST|/api/v1/jobs/{job_id}/cancel|job.cancel|M||job|Request safe cancellation and report the worker's actual boundary
jobs.retry|POST|/api/v1/jobs/{job_id}/retry|job.retry|M||job|Retry only an operation whose durable receipt and recovery rules permit retry
jobs.result|GET|/api/v1/jobs/{job_id}/result|job.read|R||job_result|Read typed result or authorized artifact references
""".strip()

# Every range in product-scope.md expands to individual, testable obligations.
REQUIREMENTS = {
    "SCOPE": ("product-scope.md", [
        "Write product services in Go with compiled engine dependencies",
        "Deliver one executable per qualified platform",
        "Expose SQLite and PostgreSQL as explicit dialects",
        "Implement the full standalone scope without substituting an MVP",
        "Operate locally without vendor account or quota service",
        "Allow catalog count to grow without a vendor database-count cap",
        "Give authorized MCP agents complete operation parity",
        "Keep NoSQL and cloud/distributed operations outside this scope",
        "Retain JSON, arrays, vectors, and text search in SQL",
        "Support synchronization to the self-hosted installation"]),
    "INST": ("configuration-and-deployment.md", [
        "Establish exactly one initial owner through protected bootstrap",
        "Validate versioned configuration and listener exposure",
        "Enforce one process owner per installation and reconcile startup state",
        "Drain sessions and durable work safely during shutdown"]),
    "DB": ("database-lifecycle.md", [
        "Create independent persistent and in-memory databases",
        "List and inspect dormant databases without opening engine handles",
        "Persist immutable provider and dialect with stable database identity",
        "Rename and move catalog resources without unsafe file renames",
        "Apply resource policies and read/write blocking consistently",
        "Enforce deletion protection and expected-generation checks",
        "Delete through draining and recoverable trash publication",
        "Evict only unpinned active handles without limiting catalog count"]),
    "ORG": ("security.md", [
        "Create and manage organizations and database groups",
        "Maintain memberships and final-owner invariants",
        "Redeem and revoke bounded local invitations",
        "Apply group defaults and custom roles with explicit inheritance"]),
    "CAT": ("catalog-and-storage.md", [
        "Persist stable IDs, revisions, and paginated resource lookup",
        "Reconcile catalog and filesystem lifecycle intents after crashes",
        "Bind active sessions and artifacts to explicit generations",
        "Back up and recover private catalog metadata with key references"]),
    "SQL": ("capability-matrix.md", [
        "Advertise audited SQLite SQL and file compatibility precisely",
        "Preserve supported constraints, indexes, views, and triggers",
        "Expose functions, PRAGMA controls, and introspection under policy",
        "Gate experimental features without silently changing semantics"]),
    "PG": ("postgresql.md", [
        "Parse and execute through the actual PostgreSQL frontend",
        "Persist and reattach schema namespaces consistently across sessions",
        "Serve authenticated encrypted PostgreSQL wire connections",
        "Isolate transaction, setting, prepared-statement, and portal state per client",
        "Preserve typed parameters, results, and native SQLSTATE where available",
        "Publish tested PostgreSQL compatibility and reject unsupported behavior"]),
    "QUERY": ("query-protocols.md", [
        "Execute bound SQL with exact typed values and native action authorization",
        "Maintain principal- and generation-bound explicit transactions",
        "Bound result buffers, cursors, and session lifetimes",
        "Cancel native work without freeing live state or inventing rollback",
        "Return stable errors and explicit commit certainty",
        "Expose query plans and permitted connection diagnostics"]),
    "SCHEMA": ("query-protocols.md", [
        "Inspect resolved objects, dependencies, and dialect-native DDL",
        "Apply schema edits with native policy and schema revision checks",
        "Store checksummed versioned templates and migrations",
        "Run bounded group migrations with independent durable outcomes"]),
    "SEARCH": ("capability-matrix.md", [
        "Retain supported JSON, JSONB, array, and structured SQL values",
        "Expose exact vector operations and complete indexed-vector integration",
        "Expose full-text indexes, matching, ranking, and highlighting by capability",
        "Manage compatible custom types and approved extensions with effect policy"]),
    "DATA": ("api-and-cli.md", [
        "Validate and import dialect-compatible SQLite files or SQL dumps",
        "Transfer CSV and tabular JSON with exact mappings and native grants",
        "Stream bounded checksummed uploads and authorized export artifacts"]),
    "AUTH": ("security.md", [
        "Authenticate local people, service principals, and agents",
        "Issue scoped database, group, and platform credentials",
        "Expire, rotate, and revoke credentials without plaintext catalog storage",
        "Bound and invalidate login and execution sessions",
        "Verify configured external JWT issuer, audience, signature, and key policy"]),
    "AUTHZ": ("security.md", [
        "Enforce resolved table and data-action grants in native execution",
        "Enforce schema, role, and organization permissions",
        "Check indirect effects through triggers, views, cascades, and functions",
        "Revalidate programs and streams on policy, schema, or generation changes",
        "Enforce equivalent authority through HTTP, PG, CLI, dashboard, and MCP"]),
    "SEC": ("security.md", [
        "Require validated TLS and authentication for configured remote exposure",
        "Apply origin, proxy, network, and rate-limit rules",
        "Contain files, attachments, COPY, and extension access to approved resources",
        "Protect secret references and verify encryption across every artifact type",
        "Audit sensitive effects without leaking secrets or unauthorized data"]),
    "HIST": ("history-and-recovery.md", [
        "Retain native commit history before checkpoint truncation can lose it",
        "Capture native-consistent complete multi-file snapshots",
        "Publish immutable checksummed archive objects and manifests",
        "Resolve times to retained complete revisions and expose gaps"]),
    "BRANCH": ("history-and-recovery.md", [
        "Create independent current and historical database clones",
        "Implement portable COW storage with immutable shared roots",
        "Preserve lineage and compare branches without promising automatic merge"]),
    "REC": ("history-and-recovery.md", [
        "Schedule and verify local or mounted-storage backups",
        "Reconstruct a retained timestamp or revision without replaying incomplete commits",
        "Verify staged restores before atomic generation publication",
        "Recover retained deleted databases under current policy",
        "Recover installation catalog and database metadata with explicit key custody",
        "Collect only unreachable objects and report retention expiry effects"]),
    "SYNC": ("sync-and-changes.md", [
        "Serve authenticated multi-database self-hosted sync",
        "Bootstrap from consistent generation-bound snapshots",
        "Push and pull compatible native changes with deduplication and conflicts",
        "Resume cursors and handle generation changes and retention gaps",
        "Treat sparse pages as bandwidth selection and require whole-generation download authority",
        "Qualify PostgreSQL and legacy-client compatibility rather than assuming it"]),
    "CHANGE": ("sync-and-changes.md", [
        "Install managed CDC on every permitted connection",
        "Publish authorized committed-change notifications",
        "Resume bounded subscriptions with explicit gap signaling",
        "Advertise live-query support only for verified query/dialect combinations"]),
    "OPS": ("operations.md", [
        "Persist jobs with leases, state transitions, events, and restart reconciliation",
        "Retry or cancel only at defined safe operation boundaries",
        "Expose integrity, checkpoint, compaction, analyze, and GC operations",
        "Measure Go and native resources, logs, queries, and audit activity",
        "Enforce fair admission and operator budgets without vendor database quotas",
        "Document upgrades, disk pressure, diagnostics, and whole-installation recovery"]),
    "IFACE": ("dashboard.md", [
        "Provide complete browser administration through common services",
        "Provide a CLI client and machine-readable output",
        "Provide versioned administration and typed SQL-over-HTTP",
        "Provide a qualified PostgreSQL endpoint and client guidance",
        "Provide MCP HTTP and an authenticated stdio proxy to the owner process",
        "Publish client integration examples and capability negotiation"]),
    "MCP": ("mcp.md", [
        "Expose every public application operation as a named typed tool",
        "Filter discovery by principal scope and current capabilities",
        "Return useful typed bounded results and authorized resources",
        "Expose durable jobs, result artifacts, events, and cancellation",
        "Allow owner agents full workflows without an additional mandatory approval gate",
        "Attribute all agent effects and follow the pinned MCP protocol semantics"]),
    "BUILD": ("build-and-release.md", [
        "Embed dashboard and docs in the application executable",
        "Bundle the complete matching native engine with automatic verified loading and no separate installation",
        "Qualify each OS and architecture with exact native dependencies",
        "Publish reproducible build manifest, digests, licenses, and capability evidence",
        "Test offline operation, upgrades, and storage-format recovery boundaries"]),
    "TEST": ("testing-and-acceptance.md", [
        "Compare SQL behavior against pristine SQLite and PostgreSQL oracles",
        "Test authorization bypasses and dynamic policy invalidation",
        "Test ABI layout, lifetime, values, cancellation, and I/O yields",
        "Test independent concurrent sessions and many dormant/active databases",
        "Inject crashes and storage failures into lifecycle, history, backup, and restore",
        "Verify interface parity, footprint, client compatibility, and release evidence"]),
}

# file | search expression | observation; anchors are calculated from this tree.
EVIDENCE = [
    ("core/dialect/mod.rs", "pub trait Dialect", "Dialect abstraction owns parsing and frontend-dependent behavior."),
    ("core/database.rs", "fn check_registry_dialect", "The registry rejects opening an existing database with a different dialect."),
    ("postgres/frontend/session.rs", "pub fn open_database", "The PostgreSQL frontend opens a real PostgresDialect database."),
    ("postgres/frontend/session.rs", "fn schema_file_path", "PostgreSQL namespaces may use separate schema files."),
    ("postgres/server/lib.rs", "NoopHandler", "The bundled wire server does not provide the platform authentication boundary."),
    ("postgres/server/lib.rs", "Mutex<PgConnection>", "The sample server stores a shared PostgreSQL connection; product sessions require isolation."),
    ("postgres/frontend/auth_functions.rs", "request.jwt.claims", "SQL settings supply auth helper claims and cannot be trusted as platform principal identity."),
    ("postgres/COMPAT.md", "Status legend", "PostgreSQL compatibility is explicitly partial; syntax acceptance is not semantic completeness."),
    ("bindings/go/go.mod", "purego", "The existing Go binding uses a dynamic native integration dependency."),
    ("bindings/go/driver_db.go", "BeginTx", "Existing transaction handling is reference code to audit rather than an assumed product contract."),
    ("sdk-kit/src/rsapi.rs", "SqliteDialect", "The inspected SDK open path chooses the SQLite dialect."),
    ("sdk-kit/turso.h", "BUSY_SNAPSHOT", "The native status set includes statuses the product must map explicitly."),
    ("sdk-kit/Cargo.toml", "staticlib", "The SDK declares a static archive target; combined product linking still needs qualification."),
    ("sync/sdk-kit/Cargo.toml", "staticlib", "The sync SDK can build a native static archive."),
    ("bindings/c/src/lib.rs", "fn sqlite3_set_authorizer", "The C authorizer is unimplemented and returns an error."),
    ("bindings/c/src/lib.rs", "fn sqlite3_backup_init", "SQLite backup API entry points are stubs in the audited C binding."),
    ("core/connection_hooks.rs", "trait ConnectionHooks", "Connection hooks are not a resolved native authorization mechanism."),
    ("core/storage/wal.rs", "checkpoint", "Physical WAL/checkpoint code must participate in retained-history integration."),
    ("core/mvcc/persistent_storage/logical_log.rs", "truncate", "MVCC logical-log checkpoint/truncation ordering differs from the page WAL path."),
    ("core/cdc.rs", "CaptureDataChangesMode", "CDC capture modes exist; all-connection management and retention remain product work."),
    ("cli/sync_server.rs", "max_open", "The bundled sync server supports bounded directory-based database handles."),
    ("cli/sync_server.rs", "pull-updates", "Self-hosted sync route primitives exist in the CLI server."),
    ("sync/engine/src/database_replay_generator.rs", "rowid", "Client replay has SQLite identity semantics that require explicit frontend qualification."),
    ("sync/engine/src/database_sync_engine.rs", "apply_transformation", "Client transformation hooks support keep, skip, and rewrite paths; SDK exposure must be qualified separately."),
    ("cli/mcp_server.rs", "tools/list", "A CLI MCP implementation exists but does not supply full platform operation parity."),
    ("sdk-kit/README.md", "codec", "Page codecs transform bytes and do not alone provide complete COW filesystem semantics."),
    ("core/Cargo.toml", "tantivy", "FTS is an optional native dependency with packaging and footprint implications."),
    ("Cargo.toml", 'panic = "abort"', "The release profile aborts on panic; catch_unwind cannot promise recovery from it."),
    ("COMPAT.md", "sqlite3_set_authorizer", "The compatibility inventory must be checked against actual source implementation."),
]


def dump(name: str, data: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def primitive_types() -> dict:
    text = {"type": "string", "maxLength": 4096}
    types = {"text": text, "secret": {"type": "string", "minLength": 1, "maxLength": 65536, "writeOnly": True},
             "sql": {"type": "string", "minLength": 1, "maxLength": 1048576},
             "uuid": {"type": "string", "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"},
             "revision": {"type": "string", "pattern": "^[0-9]+$", "maxLength": 20},
             "timestamp": {"type": "string", "pattern": "^[0-9]+$", "description": "UTC Unix microseconds as an exact decimal string"},
             "digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
             "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,127}$"},
             "bool": {"type": "boolean"}, "positive": {"type": "integer", "minimum": 1, "maximum": 2147483647},
             "nonnegative": {"type": "integer", "minimum": 0, "maximum": 2147483647},
             "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
             "object": {"type": "object", "description": "Operation-specific versioned policy/definition object; validate against the selected capability schema before effects"},
             "base64": {"type": "string", "contentEncoding": "base64", "maxLength": 1048576}}
    for name, values in {
        "dialect": ["sqlite", "postgres"], "provider": ["turso"], "persistence": ["persistent", "memory"],
        "principal_kind": ["user", "service", "agent"], "platform": ["linux", "windows", "macos"],
        "credential_kind": ["opaque_token", "signed_token", "postgres_scram"],
        "query_mode": ["read", "write", "schema"],
        "transaction_mode": ["deferred", "immediate", "concurrent"],
        "failure_policy": ["stop", "continue"], "transfer_format": ["sqlite", "sql", "csv", "json_rows"],
        "restore_mode": ["new_database", "replace_generation"],
        "credential_policy": ["revoke_restored", "preserve_same_instance"],
        "cdc_mode": ["id", "before", "after", "full"], "subscription_kind": ["commits", "changes", "live_query"],
    }.items():
        types[name] = {"type": "string", "enum": values}
    types["nullable_uuid"] = {"anyOf": [{"$ref": "#/$defs/uuid"}, {"type": "null"}]}
    types["texts"] = {"type": "array", "items": {"$ref": "#/$defs/text"}, "maxItems": 1000}
    types["uuids"] = {"type": "array", "items": {"$ref": "#/$defs/uuid"}, "maxItems": 10000}
    types["objects"] = {"type": "array", "items": {"$ref": "#/$defs/object"}, "maxItems": 1000}
    types["sql_value"] = {"type": "object", "required": ["type", "value"], "additionalProperties": False,
        "properties": {"type": {"enum": ["null", "integer", "real", "text", "blob", "numeric", "json", "array", "typed_text"]},
                       "value": {"description": "Tag-specific exact payload; integer/numeric as decimal strings, blob as base64, SQL null as null"},
                       "pg_oid": {"type": "integer", "minimum": 0}, "type_name": text},
        "description": "Native capabilities additionally validate int64 range, array dimensions, base64, and dialect metadata; never coerce numeric to float64"}
    payloads = {
        "null": {"type": "null"},
        "integer": {"type": "string", "pattern": "^-?(0|[1-9][0-9]*)$", "maxLength": 20},
        "real": {"anyOf": [{"type": "number"}, {"enum": ["NaN", "+Infinity", "-Infinity"]}]},
        "text": {"type": "string"}, "blob": {"type": "string", "contentEncoding": "base64"},
        "numeric": {"type": "string", "minLength": 1, "maxLength": 65536},
        "json": {},
        "array": {"type": "object", "required": ["element_type", "dimensions", "lower_bounds", "elements"], "additionalProperties": False,
            "properties": {"element_type": {"type": "string"}, "dimensions": {"type": "array", "items": {"type": "integer", "minimum": 0}},
                "lower_bounds": {"type": "array", "items": {"type": "integer"}}, "elements": {"$ref": "#/$defs/values"}}},
        "typed_text": {"type": "string"}}
    types["sql_value"]["oneOf"] = [{"properties": {"type": {"const": tag}, "value": payload}} for tag, payload in payloads.items()]
    types["values"] = {"type": "array", "items": {"$ref": "#/$defs/sql_value"}, "maxItems": 65535}
    types["statements"] = {"type": "array", "minItems": 1, "maxItems": 1000,
        "items": {"type": "object", "required": ["sql", "parameters", "mode"], "additionalProperties": False,
            "properties": {"sql": {"$ref": "#/$defs/sql"}, "parameters": {"$ref": "#/$defs/values"}, "mode": {"$ref": "#/$defs/query_mode"}}}}
    return types


def make_operations() -> None:
    types = primitive_types()
    records = []
    for line in OPERATIONS.splitlines():
        op, method, path, permission, execution, fields, result, description = line.split("|")
        properties, required = {}, []
        for selector in re.findall(r"{([^}]+)}", path):
            properties[selector] = {"$ref": "#/$defs/nonnegative" if selector == "chunk_index" else "#/$defs/text" if selector == "extension_id" else "#/$defs/uuid"}
            required.append(selector)
        for field in fields.split():
            name, kind = field.rstrip("!").split(":")
            properties[name] = {"$ref": f"#/$defs/{kind}"}
            if field.endswith("!"):
                required.append(name)
        if execution != "R":
            properties["idempotency_key"] = {"type": "string", "minLength": 16, "maxLength": 128}
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "type": "object", "properties": properties, "required": required, "additionalProperties": False}
        read = execution == "R"
        records.append({"id": op, "description": description, "domain": op.split(".")[0],
            "permission": permission, "resource_selectors": [x for x in properties if x.endswith("_id")],
            "http": {"method": method, "path": path}, "cli": op.replace("_", "-").split("."),
            "mcp": {"name": "mira_" + op.replace(".", "_"), "annotations": {
                "readOnlyHint": read and op != "query.explain", "destructiveHint": not read,
                "idempotentHint": read and op != "query.explain", "openWorldHint": op.startswith("identity_providers.")}},
            "input_schema": schema, "output_schema": output_schema(result, types),
            "result_type": result, "job": execution == "J", "execution": {"R": "read", "M": "synchronous", "J": "durable_job"}[execution],
            "idempotency": "read" if read else "native_write_receipt_required" if op in {"query.execute", "query.script", "query.explain", "sessions.commit", "sync.push"} else "durable_service_receipt",
            "authorization": "service permission plus resolved native effects and current policy epoch",
            "capability_gate": capability_gate(op), "audit_event": op,
            "interfaces": ["http", "cli", "mcp", "dashboard"]})
    dump("operations.json", {"status": "proposed; no endpoints implemented by this documentation", "version": 1,
        "schema_dialect": "https://json-schema.org/draft/2020-12/schema", "$defs": types,
        "notes": ["Shared $defs are document-root definitions. Materialize them into each extracted input/output schema before passing that schema to an MCP SDK or standalone validator.",
                  "Operation inputs include path/query selectors; HTTP bindings remove path selectors from bodies.",
                  "Versioned extension, policy, and search-definition objects are validated by their selected capability schema; this inventory is not a complete OpenAPI document.",
                  "One-time secrets must bypass logs, audit payloads, caches, and general job results.",
                  "Primitive data/schema grants are checked inside native execution in addition to these service permissions.",
                  "Offline recovery and process startup are local lifecycle controls, not remotely invocable application operations."],
        "primitive_permissions": ["data.read", "data.insert", "data.update", "data.delete", "schema.read", "schema.create", "schema.alter", "schema.drop", "query.connect"],
        "permissions": sorted({r["permission"] for r in records}), "operations": records})


def output_schema(kind: str, types: dict) -> dict:
    # Common envelopes are fully declared. Native/provider-specific object details
    # stay in a versioned payload and must not be misrepresented as a frozen ABI.
    props = {"id": {"$ref": "#/$defs/uuid"}, "revision": {"$ref": "#/$defs/revision"},
             "type": {"type": "string"}, "state": {"type": "string"},
             "created_at": {"$ref": "#/$defs/timestamp"}, "updated_at": {"$ref": "#/$defs/timestamp"},
             "attributes": {"type": "object", "description": "Versioned resource payload defined by owning chapter and catalog schema; secret values prohibited"}}
    base = {"type": "object", "properties": props, "required": ["id", "revision", "type", "attributes"], "additionalProperties": False}
    if kind.endswith("[]"):
        base = {"type": "object", "required": ["items", "next_cursor"], "additionalProperties": False,
                "properties": {"items": {"type": "array", "items": base, "maxItems": 1000}, "next_cursor": {"type": ["string", "null"]}}}
    elif kind == "issued_secret":
        base = {"type": "object", "required": ["resource", "secret", "expires_at"], "additionalProperties": False,
                "properties": {"resource": base, "secret": {"type": "string", "minLength": 1, "maxLength": 65536, "description": "Explicit issuance delivery only; never expose through ordinary reads"}, "expires_at": {"$ref": "#/$defs/timestamp"}}}
    elif kind == "query_result":
        base = {"type": "object", "required": ["request_id", "query_id", "database_id", "generation_id", "columns", "rows", "commit_state", "cursor", "has_more"], "additionalProperties": False,
                "properties": {"request_id": {"$ref": "#/$defs/uuid"}, "query_id": {"$ref": "#/$defs/uuid"}, "database_id": {"$ref": "#/$defs/uuid"}, "generation_id": {"$ref": "#/$defs/uuid"},
                    "columns": {"type": "array", "items": {"type": "object", "required": ["name", "type_name"], "properties": {"name": {"type": "string"}, "type_name": {"type": "string"}, "pg_oid": {"type": "integer"}}, "additionalProperties": False}},
                    "rows": {"type": "array", "items": {"$ref": "#/$defs/values"}},
                    "commit_state": {"enum": ["not_started", "in_transaction", "rolled_back", "committed", "unknown_commit_state"]},
                    "cursor": {"type": ["string", "null"]}, "has_more": {"type": "boolean"}, "affected_rows": {"$ref": "#/$defs/revision"}}}
    elif kind == "script_result":
        query = {key: value for key, value in output_schema("query_result", types).items() if key not in {"$schema", "$defs", "title"}}
        base = {"type": "object", "required": ["request_id", "generation_id", "atomic", "commit_state", "results"], "additionalProperties": False,
                "properties": {"request_id": {"$ref": "#/$defs/uuid"}, "generation_id": {"$ref": "#/$defs/uuid"}, "atomic": {"type": "boolean"},
                    "commit_state": {"enum": ["not_started", "rolled_back", "committed", "partially_committed", "unknown_commit_state"]},
                    "results": {"type": "array", "maxItems": 1000, "items": {"type": "object", "required": ["index", "state"], "additionalProperties": False,
                        "properties": {"index": {"type": "integer", "minimum": 0}, "state": {"enum": ["succeeded", "failed", "skipped"]}, "result": query, "error": {"type": "object"}}}}}}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": kind, **base}


def capability_gate(op: str) -> list[str]:
    for prefix, caps in [("branches.", ["snapshot", "cow_storage"]), ("history.", ["retained_native_history"]),
                         ("snapshots.", ["consistent_bundle_snapshot"]), ("sync.", ["dialect_qualified_sync"]),
                         ("changes.", ["managed_all_connection_cdc"]), ("subscriptions.", ["authorized_change_stream"]),
                         ("search.", ["dialect_search_capabilities"]), ("extensions.", ["approved_native_extensions"]),
                         ("maintenance.", ["native_maintenance"]), ("recovery.", ["verified_native_replay"]),
                         ("query.", ["dialect_execution", "resolved_native_authorization"])]:
        if op.startswith(prefix):
            return caps
    return []


def make_requirements() -> None:
    records = []
    for area, (owner, obligations) in REQUIREMENTS.items():
        for n, obligation in enumerate(obligations, 1):
            records.append({"id": f"{area}-{n:03}", "area": area, "requirement": obligation,
                "owner_document": owner, "status": "required; not verified by documentation",
                "acceptance": f"Demonstrate: {obligation.lower()}. Record normal, denied/unsupported, concurrent, and failure/restart outcomes where applicable; verify interface parity and retain evidence.",
                "acceptance_document": "testing-and-acceptance.md"})
    dump("requirements.json", {"version": 1, "requirements": records})


def extract_capabilities() -> list[dict]:
    rows = []
    for path, dialect in [("COMPAT.md", "sqlite"), ("postgres/COMPAT.md", "postgres")]:
        section, headers = [], []
        for number, raw in enumerate((require_source_root() / path).read_text(encoding="utf-8").splitlines(), 1):
            heading = re.match(r"^(#{1,6}) (.+)", raw)
            if heading:
                level = len(heading[1])
                section = section[:level-1] + [heading[2]]
                headers = []
            if not raw.startswith("|"):
                headers = []
                continue
            cells = re.split(r"(?<!\\)\|", raw.strip().strip("|"))
            cells = [x.strip() for x in cells]
            if cells and set("".join(cells)) <= set("-: "):
                continue
            if any(x.lower() == "status" for x in cells):
                headers = cells
                continue
            if not headers or not cells:
                continue
            rows.append({"dialect": dialect, "source_path": path, "line": number,
                "section": " / ".join(section), "headers": headers, "cells": cells,
                "raw": raw, "source_url": f"https://github.com/tursodatabase/turso/blob/{REVISION}/{path}#L{number}"})
    return rows


def make_evidence() -> None:
    records = []
    for n, (path, pattern, observation) in enumerate(EVIDENCE, 1):
        data = (require_source_root() / path).read_text(encoding="utf-8").encode("utf-8")
        lines = data.decode("utf-8").splitlines()
        matches = [i for i, line in enumerate(lines, 1) if re.search(pattern, line)]
        if not matches:
            raise ValueError(f"Evidence anchor not found: {path}: {pattern}")
        line = matches[0]
        records.append({"id": f"SRC-{n:03}", "path": path, "sha256": hashlib.sha256(data).hexdigest(),
                        "pattern": pattern, "line": line, "observation": observation,
                        "url": f"https://github.com/tursodatabase/turso/blob/{REVISION}/{path}#L{line}"})
    dump("source-evidence.json", {"upstream": "https://github.com/tursodatabase/turso", "revision": REVISION,
        "hash_normalization": "UTF-8 text with CRLF/CR normalized to LF, for cross-platform checkout verification",
        "method": "source inspection; not a runtime test", "records": records,
        "external_sources": [
            {"url": "https://github.com/tursodatabase/turso-go-platform-libs/blob/57d6c2f7db38/load_turso.go", "observation": "Loader pinned by the audited Go module bundles/extracts a native library and verifies SHA-256; checked through the GitHub contents API. External source is not covered by local checkout hashes."},
            {"url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports", "observation": "Versioned MCP transport semantics; use a qualified SDK rather than copying the CLI server."},
            {"url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools", "observation": "Versioned tool schema and result semantics."},
            {"url": "https://github.com/modelcontextprotocol/go-sdk", "observation": "Official Go SDK; exact implementation dependency must be pinned and qualified."},
            {"url": "https://turso.tech/blog/building-local-first-apps-the-complete-guide-to-offline-first-database-sync", "observation": "Official client documentation describes last-push-wins and client-side mutation transform hooks, distinct from server-side arbitrary code."}]})
    rows = extract_capabilities()
    dump("upstream-capabilities.json", {"revision": REVISION, "status": "upstream authors' compatibility table assertions, not verified product support",
        "extraction": "All data rows in tables with a Status header in the two compatibility documents, including Not Needed and the status legend. Prose-only qualifications remain authoritative in the originals.",
        "attribution": "Turso contributors, upstream MIT license; see THIRD_PARTY_NOTICES.md and the pinned upstream LICENSE.md", "rows": rows})
    intro = """# Source evidence and complete upstream table inventory

This audit is fixed to upstream commit `""" + REVISION + """`. Each record below links to an immutable source location. The machine-readable records include SHA-256 hashes of the local audited files. Source inspection establishes implementation facts and gaps; it does not establish a passed runtime test.

The [complete extracted compatibility-table inventory](contracts/upstream-capabilities.json) preserves every status-bearing row from both upstream compatibility documents, with dialect, section, headers, notes, original text, and immutable line link. This covers individual SQL statements, expressions, functions, C APIs, opcodes, types, extensions, and PostgreSQL feature rows rather than substituting a short marketing feature list. Upstream prose qualifications still apply. In particular, declarations and optimistic compatibility rows can disagree with implementation stubs; the inspected source wins.

The [product capability matrix](capability-matrix.md) maps these engine facilities to the standalone product. Unsupported upstream features are recorded as gaps, not advertised as existing product support. The required product capabilities remain governed by [scope](product-scope.md) and [decisions](decisions.md).

## Inspected implementation boundaries

| Record | Source | Observation |
|---|---|---|
"""
    for r in records:
        intro += f"| {r['id']} | [{r['path']}:{r['line']}]({r['url']}) | {r['observation']} |\n"
    intro += "\n## Evidence limits\n\nThe audit followed the engine, frontend, SDK, durability, sync, and CLI entry points and the repository's contributor/agent guides. It does not claim every source line in this large repository was read. The compatibility inventory preserves upstream assertions, including limitations, without treating them as our own executed conformance results. External sources are listed separately in the JSON and are not covered by local source hashes. The upstream revision predates the proposed product contracts; none of the new Mira interfaces is attributed to upstream.\n"
    (DOCS / "source-evidence.md").write_text(intro, encoding="utf-8", newline="\n")


def main() -> None:
    require_source_root()
    make_operations()
    make_requirements()
    make_evidence()
    print("Generated proposed operation, requirement, source-evidence, and upstream-capability inventories.")


if __name__ == "__main__":
    main()
