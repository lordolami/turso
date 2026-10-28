# Go and native engine bridge

## Decision

Use a product-owned, versioned C ABI and a small cgo adapter. Link the combined native archive into the Go executable. Reuse upstream Rust engine/frontend code directly. Go does not reimplement the SQL parser, PostgreSQL AST translator, B-tree, VDBE, or MVCC engine.

The current Go package is useful reference material but does not expose PostgreSQL or the additional authorization/history boundaries. Its default native loader extracts a shared library. The product requires a build path that meets the single-executable contract without that extraction. Existing staticlib support is a building block, not a proof that the combined product links on every OS.

The proposed declaration is [mira_engine.h](contracts/mira_engine.h). All mira_* names in this chapter are proposed symbols. None is claimed to exist upstream.

## Bridge objects

| Object | Owner | Lifetime |
|---|---|---|
| Engine | Go application | Created after version checks; destroyed after all databases |
| Database | Native handle manager | One immutable provider/dialect/generation object; referenced by connections and snapshot jobs |
| Connection | One Go session | Serialized calls; separate connection for each SQL/PG session |
| Statement | One connection | Prepared, bound, stepped, reset/finalized; cannot outlive its connection |
| Policy | Native immutable allocation | Bound to principal, resource generation, policy epoch, allowed effects |
| Result buffer | Native allocation transferred to Go | Copy/read before explicit native buffer-free call |
| Snapshot/archive operation | Native state machine | Retains generation and storage resources until completed or canceled |

Use generation-checked opaque numeric handles instead of trusting raw client-supplied pointers. Keep the handle table inside the bridge. A released slot changes its handle generation; stale handles return misuse. External HTTP/MCP identifiers never equal native handles.

## Required ABI families

1. Version/build information: ABI version, struct sizes, native revision, compile-time features, supported dialects and format versions.
2. Engine create/destroy and bounded native allocation metrics.
3. Database create/open/close, identity verification, journal mode, encryption references, and generation metadata.
4. SQLite connection and PostgreSQL frontend connection creation; the latter must create a real PgConnection.
5. Trusted principal/policy installation and atomic policy-epoch replacement.
6. Prepare, parameter description, typed binding, step, row metadata, value extraction, reset, finalize.
7. Interrupt, I/O pumping, deadline/budget checks, and transaction state inspection.
8. Catalog/schema/object introspection and resolved action reporting.
9. Snapshot, retained commit stream, checkpoint coordination, recovery replay, and COW storage hooks.
10. Sync protocol operations with dialect/generation identity and immutable snapshot references.
11. Extension registration with ownership, trust, and function-effect metadata.

If upstream exposes a required operation only in Rust, add the smallest wrapper at the existing native boundary. A successful Go build must not hide missing semantics behind a no-op.

## Values and metadata

Preserve NULL, signed int64, finite/non-finite floating-point values, UTF-8 text, and byte strings distinctly. PostgreSQL adds frontend metadata such as OID, type modifier, array element type, and exact textual representation where binary encoding is not implemented. Decimal/numeric values do not travel through float64. JSON null is distinguished from SQL NULL. Empty byte arrays and empty text are not NULL.

A returned row owns or borrows its bytes according to the ABI operation, never according to a guessed pointer lifetime. Borrowed values expire at the next step/reset/finalize; Go copies them before that event. Bind input buffers remain valid until the bridge copies them; the ABI promises to copy during the call. Allocation limits apply before copying a large value.

No Go pointer containing Go pointers is retained by native code. Use cgo.Handle or a native-owned context token for callbacks, and keep release callbacks paired with registration. A callback must not reenter the same connection, call arbitrary application code while holding an engine lock, or block on a Go worker that is waiting for that native call.

## Struct and ABI rules

- Every extensible configuration/result struct starts with size and abi_version.
- Use fixed-width integer fields for wire-independent values; declare pointer/length byte slices explicitly.
- Unknown mandatory flags return unsupported; trailing optional fields can be ignored only under the documented version rule.
- Generate and compare headers; verify sizeof/alignof/offsetof and enum values in native and cgo builds.
- Include a runtime build manifest digest. Refuse loading an incompatible archive/header combination.
- Keep ownership APIs named by action: retain, release, buffer_free. Do not overload close to mean both SQL close and allocation deallocation.

The inspected Go/native status surfaces differ in coverage, so wrappers must map the full linked enum, including busy-snapshot and I/O errors. An unknown native status fails explicitly with the original integer and a sanitized diagnostic.

## I/O and statement state machine

~~~text
new -> prepared -> bound -> stepping
stepping -> row -> stepping
stepping -> needs_io -> io_complete -> stepping
stepping -> done
stepping -> interrupted | busy | conflict | error
done/error -> reset or finalized
~~~

The engine's cooperative I/O can return pending work. The bridge drives it until a row, completion, or terminal error, or returns a resumable operation handle. Never treat an I/O yield as end-of-results. Never repeat a side effect when reentering an operation after a yield. Prefer the engine's established run/step helpers and test every yield boundary.

## Cancellation and commit certainty

Go context cancellation sets a native cancellation signal or calls a thread-safe interrupt entry point. It does not free live native objects. An execution worker observes interruption, completes rollback/cleanup, records outcome, and then releases resources. Native calls that cannot be interrupted receive a bounded worker budget and explicit capability limitation.

Cancellation is not a transaction rollback guarantee after commit. Results report not_started, rolled_back, committed, or unknown_commit_state where applicable. A network disconnect after a durable commit cannot become a safe blind retry. An explicit receipt or idempotency mechanism is required for retryable writes.

## Authorization hooks

Add a generic authorization mechanism to core's resolved compilation/execution boundary. Compile policy from platform grants into native-owned immutable state. Every object/function/file effect carries a resolved resource identity and action. Views, triggers, cascades, virtual tables, functions, ATTACH, schema operations, and statement re-preparation must participate. Policy checks do not depend on matching the first SQL keyword.

The native boundary receives trusted identity from Go; SQL-modifiable custom settings cannot replace it. Prepared programs are valid only for their policy/schema/generation epochs. An invalidated program must be checked or prepared again before execution.

## Panic and failure handling

The selected native release profile currently uses panic=abort. Do not promise catch_unwind can intercept an aborting panic. Recoverable native errors must cross the ABI as status/error objects; integrity-threatening engine failures terminate the process and rely on storage recovery. No exception unwinds across C/Go boundaries. ABI wrapper panics are either caught under a deliberately compatible unwind profile or terminate; document and test the chosen build behavior.

## Qualification

Required tests include repeated open/close; concurrent independent databases; per-client PG state; malformed/stale handles; zero-length and huge buffers; int64 boundaries; exact decimal round trips; embedded NUL text policy; invalid UTF-8; partial I/O; callback unregister; cancellation during prepare/step/I/O/commit; allocation failures; and native/Go race/lifetime stress. A platform is supported only after the entire native+Go executable passes these checks.
