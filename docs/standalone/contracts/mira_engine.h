/* PROPOSED ABI contract v1, not implemented by this documentation.
 * Product API, not an upstream Turso header. Generate/check native+Go FFI layouts.
 * Reuse existing turso_* symbols where equivalent; these declarations illustrate
 * required semantics and do not require redundant wrappers or static linking.
 * One target-native payload shares SQLite+PostgreSQL+sync engine dependencies.
 * All calls serialize a given session/statement except mira_interrupt().
 * Native copies input bytes during the call; it never retains Go pointers.
 * Output buffers are native-owned and freed with mira_buffer_free().
 * Borrowed column views expire on step/reset/finalize; Go must copy first.
 * Every function returns a status; recoverable error details are owned output.
 */
#ifndef MIRA_PROPOSED_ENGINE_H
#define MIRA_PROPOSED_ENGINE_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

#define MIRA_ABI_VERSION 1u
typedef uint64_t mira_handle; /* bridge table index+generation; zero is invalid */
typedef uint32_t mira_status;
enum {
    MIRA_OK=0, MIRA_ROW=1, MIRA_DONE=2, MIRA_NEEDS_IO=3,
    MIRA_BUSY=4, MIRA_BUSY_SNAPSHOT=5, MIRA_INTERRUPTED=6,
    MIRA_DENIED=7, MIRA_INVALID=8, MIRA_STALE_HANDLE=9,
    MIRA_UNSUPPORTED=10, MIRA_IO_ERROR=11, MIRA_CORRUPT=12,
    MIRA_GENERATION_CHANGED=13, MIRA_LIMIT=14, MIRA_ERROR=255
}; /* Product-owned codes; not numeric aliases of upstream enums. */
typedef struct { const uint8_t *data; uint64_t len; } mira_bytes;
typedef struct { uint8_t *data; uint64_t len; uint64_t allocation_id; } mira_buffer;
typedef struct {
    uint32_t size, abi_version;
    uint32_t code, native_code;
    uint32_t commit_state; /* 0 not started, 1 active, 2 rolled back, 3 committed, 4 unknown */
    uint32_t retry_class;  /* 0 no automatic retry, 1 safe before effect, 2 receipt required */
    mira_buffer sqlstate; /* exact native SQLSTATE when available */
    mira_buffer message; /* sanitized; no credentials or hidden object names */
} mira_error;

typedef struct {
    uint32_t size, abi_version;
    uint64_t memory_budget_bytes, io_concurrency;
    mira_bytes expected_build_manifest_sha256;
} mira_engine_config;
typedef struct {
    uint32_t size, abi_version;
    mira_bytes database_id, generation_id;
    mira_bytes canonical_bundle_path; /* supplied only by trusted Go manager */
    mira_bytes dialect; /* sqlite or postgres; immutable for database lifetime */
    mira_bytes options_json; /* versioned, bounded, capability-validated */
    mira_bytes encryption_key_ref; /* resolved by protected key service */
    uint32_t create, persistence;
} mira_database_config;
typedef struct {
    uint32_t size, abi_version;
    mira_bytes principal_id, credential_id;
    uint64_t policy_epoch, schema_revision;
    mira_bytes compiled_policy; /* versioned native-readable immutable bytes */
} mira_policy_config;
typedef struct {
    uint32_t size, abi_version;
    mira_handle policy;
    uint64_t deadline_monotonic_ns, max_result_bytes, max_steps;
    mira_bytes namespace_manifest; /* PG schema identity/reattachment map */
} mira_session_config;
typedef struct {
    uint32_t size, abi_version, tag, flags;
    int64_t integer_value;
    double real_value;
    mira_bytes bytes; /* UTF-8, blob, exact numeric, JSON, array, typed text */
    uint32_t pg_oid;
    int32_t pg_type_modifier;
} mira_value;
enum {
    MIRA_NULL=0, MIRA_INTEGER=1, MIRA_REAL=2, MIRA_TEXT=3,
    MIRA_BLOB=4, MIRA_NUMERIC=5, MIRA_JSON=6, MIRA_ARRAY=7, MIRA_TYPED_TEXT=8
};
typedef struct {
    uint32_t size, abi_version;
    mira_bytes name, type_name;
    uint32_t pg_oid;
    int32_t pg_type_modifier;
} mira_column;
typedef struct {
    uint32_t size, abi_version;
    uint32_t state, reserved;
    uint64_t affected_rows;
    mira_bytes commit_revision;
} mira_transaction_state;

/* Discover build/dialect/features and exact ABI sizes before creating objects. */
mira_status mira_build_manifest(mira_buffer *json, mira_error *error);
mira_status mira_engine_create(const mira_engine_config *, mira_handle *, mira_error *);
mira_status mira_engine_metrics(mira_handle engine, mira_buffer *json, mira_error *);
mira_status mira_engine_release(mira_handle engine, mira_error *);
mira_status mira_database_open(mira_handle engine, const mira_database_config *, mira_handle *, mira_error *);
mira_status mira_database_manifest(mira_handle database, mira_buffer *json, mira_error *);
mira_status mira_database_release(mira_handle database, mira_error *);
mira_status mira_policy_create(mira_handle engine, const mira_policy_config *, mira_handle *, mira_error *);
mira_status mira_policy_release(mira_handle policy, mira_error *);
/* Opening a postgres database must construct a real PgConnection, not raw core Connection. */
mira_status mira_session_open(mira_handle database, const mira_session_config *, mira_handle *, mira_error *);
mira_status mira_session_replace_policy(mira_handle session, mira_handle policy, mira_error *);
mira_status mira_session_transaction_state(mira_handle session, mira_transaction_state *, mira_error *);
mira_status mira_session_release(mira_handle session, mira_error *);

/* Prepare one statement; tail_offset allows the caller to reject unwanted scripts. */
mira_status mira_prepare(mira_handle session, mira_bytes sql, mira_handle *statement, uint64_t *tail_offset, mira_error *);
mira_status mira_statement_parameters(mira_handle statement, mira_buffer *json, mira_error *);
mira_status mira_statement_actions(mira_handle statement, mira_buffer *resolved_actions_json, mira_error *);
mira_status mira_bind(mira_handle statement, uint32_t index, const mira_value *, mira_error *);
mira_status mira_step(mira_handle statement, mira_error *); /* ROW/DONE/NEEDS_IO or error */
mira_status mira_pump_io(mira_handle session, uint64_t deadline_monotonic_ns, mira_error *);
mira_status mira_column_count(mira_handle statement, uint32_t *count, mira_error *);
mira_status mira_column_metadata(mira_handle statement, uint32_t index, mira_column *, mira_error *);
mira_status mira_column_value(mira_handle statement, uint32_t index, mira_value *, mira_error *);
mira_status mira_statement_reset(mira_handle statement, mira_error *);
mira_status mira_statement_release(mira_handle statement, mira_error *);
mira_status mira_interrupt(mira_handle session, mira_error *); /* thread safe; no free */
mira_status mira_schema_manifest(mira_handle session, mira_buffer *json, mira_error *);

/* Snapshot/history/COW are additional native integration, not existing SDK promises.
 * Async operation handles retain their database generation until release.
 * options/results are size-bounded versioned JSON manifests, never host paths
 * accepted directly from public clients. Checkpoints obey retained-history rules.
 */
mira_status mira_snapshot_begin(mira_handle database, mira_bytes options_json, mira_handle *operation, mira_error *);
mira_status mira_history_configure(mira_handle database, mira_bytes policy_json, mira_error *);
mira_status mira_history_read(mira_handle database, mira_bytes cursor, uint64_t max_bytes, mira_buffer *, mira_error *);
mira_status mira_checkpoint_begin(mira_handle database, mira_bytes options_json, mira_handle *operation, mira_error *);
mira_status mira_replay_begin(mira_handle engine, mira_bytes verified_manifest, mira_handle *operation, mira_error *);
mira_status mira_branch_begin(mira_handle engine, mira_bytes verified_base_manifest, mira_bytes target_config, mira_handle *operation, mira_error *);
mira_status mira_sync_request(mira_handle session, mira_bytes request_envelope, mira_handle *operation, mira_error *);
mira_status mira_extension_register(mira_handle engine, mira_bytes approved_manifest, mira_error *);
mira_status mira_operation_poll(mira_handle operation, mira_buffer *progress_or_result_json, mira_error *);
mira_status mira_operation_cancel(mira_handle operation, mira_error *);
mira_status mira_operation_release(mira_handle operation, mira_error *);

/* Parent release returns busy while children exist; it never destroys live work.
 * Releasing an already released handle returns stale_handle. Output error/buffer
 * free is safe for zero-initialized outputs. Error outputs own their buffers.
 */
void mira_buffer_free(mira_buffer *);
void mira_error_free(mira_error *);

#ifdef __cplusplus
}
#endif
#endif
