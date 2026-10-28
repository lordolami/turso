# Single-executable build and release design

## What is shipped

One Mira application executable for each qualified OS/architecture. It contains the Go application, compiled native database/frontend bridge, dashboard assets, static help, schema/operation metadata, and bundled compatible extensions. Client SDKs and an embedding library are separate developer artifacts. User data, backups, certificates, configuration, and runtime logs remain separate files.

This is a packaging requirement, not a claim of a pure-Go database implementation. The engine and PostgreSQL parser/frontend are existing native code. Keep the application's platform services in Go.

## Static native integration

The core and sync SDK kits declare staticlib outputs. postgres/frontend is a Rust library and the reference PostgreSQL server is not the desired Go product server. Add a combined product bridge crate depending on pinned engine/frontend code, exporting the versioned C ABI, and build it into a native archive. Link through cgo using the generated header.

Do not independently link multiple archives that each contain conflicting copies of the engine, runtime, allocator, or exported C symbols. Build a coordinated native dependency graph and export only the product ABI plus explicitly required compatibility symbols. Choose one native allocator strategy and measure it alongside Go's allocator. Preserve unwind/abort behavior at the ABI boundary.

The upstream Go purego loader extracts its embedded shared library at runtime. It does not satisfy the stricter no-extracted-engine-runtime contract without changes. A convenience single-download build using extraction must be labeled separately and cannot silently replace the strict product target.

## Build inputs

- Exact upstream revision and reviewed patch series.
- Native header/ABI version and generation-tool version.
- Pinned Go toolchain and Go dependency graph.
- Repository-compatible Rust toolchain, Cargo.lock, C/C++ compiler/linker, and PostgreSQL grammar build prerequisites.
- Pinned official MCP Go SDK and protocol compatibility evidence.
- Dashboard lockfile/toolchain and deterministic compiled assets.
- Enabled native build features, database runtime experimental options, codec/extension implementations, and licenses.

Do not copy the existing Go platform-libs binary into a current source build without verifying revision/ABI compatibility. A Go source version, native binary version, and generated header can differ.

## Native feature set

Record explicit inclusion of filesystem I/O, JSON, UUID, time, series, percentile/statistical functions, encryption implementation, vector operations, FTS/Tantivy, supported codecs/extensions, PostgreSQL frontend/parser, and sync primitives. Optional compile-time flags and runtime experimental flags are distinct. The CLI's default feature set is not automatically the SDK's feature set.

If a target cannot build a required native frontend or feature, report the target unqualified or the capability gap. Do not solve the binary-size target by quietly removing a required product feature.

## Platform qualification

| Target family | Work required |
|---|---|
| Linux amd64/arm64 | Static/native linking strategy, libc policy, CPU feature baseline, io_uring optional fallback, dependency inspection |
| macOS amd64/arm64 | Native archive/framework dependencies, deployment target, executable signing/notarization policy, separate architecture qualification |
| Windows amd64 | MSVC/native runtime policy, PostgreSQL parser compiler prerequisites, static linkage, Windows service/ACL/control-pipe behavior |
| Additional targets | Explicit engine/frontend/compiler support and complete acceptance evidence before advertising |

The above is a qualification plan, not a statement that every target currently builds. Bundling both engines for exact legacy libSQL parity, if selected under DEC-014, adds another native dependency and qualification obligation.

## Proposed build pipeline

1. Fetch pinned dependencies and verify the source lock/manifest.
2. Generate/check the native header and ABI layout assertions.
3. Build the combined native archive with reproducible features and release profile.
4. Build the dashboard from locked dependencies, compress assets, and embed assets/help/contracts.
5. Compile the Go application with path trimming and appropriate symbol handling for release and separate debug artifacts.
6. Inspect executable dependencies with target-native tools; confirm no separate application engine daemon/shared library is required.
7. Run offline startup/setup, both dialects, MCP, persistence, authentication, resource, backup/restore, and platform integration tests.
8. Generate the runtime capability/build manifest, checksums, SBOM/notices, and release evidence.
9. Sign/package the artifact under the operator's release policy and publish only qualified targets.

Actual commands must be derived from the implemented build graph and CI environment. The product/native source tree does not yet exist, so this specification deliberately does not present a fictional go build command as a working release recipe.

## Lightweight optimization

Strip/compress eligible assets and symbols, use suitable native LTO/codegen settings, avoid bundling developer toolchains, and lazily allocate runtime working sets. Preserve required functionality and observability. Upstream profiles deliberately make different size/build-time tradeoffs; measure the final Go+native artifact rather than assuming maximum LTO always produces the smallest successful cross-platform binary.

Publish compressed download size, executable size, startup time, idle RSS, native/Go memory breakdown, and the benchmark environment. PocketBase's footprint is a comparison target, not a number established here.

## Upstream maintenance

Retain upstream remote and preserve a small, documented patch series. Separate generic authorizer/history improvements from platform code and PostgreSQL-specific behavior. Update source evidence/capability records when advancing the engine revision. Re-run compatibility, ABI, storage/recovery, and policy tests before accepting a new source revision. Format/sidecar compatibility follows the upstream invariant; raise incompatibilities explicitly.

## Licenses and branding

Preserve the upstream MIT notice and all dependency notices required by the actual linked artifact. Review the compiled dependency graph, including libpg_query and extensions, rather than assuming every component has the top-level license. No third-party runtime dependency is added by this documentation-only change. Mira is a working name; distribution must not imply it is an official Turso Cloud service.

## Upgrade and downgrade

Back up catalog/data/key references and verify artifact provenance before upgrade. Use migration intents, format checks, and graceful connection drain. Catalog and native storage compatibility have separate version gates. A binary rollback is permitted only when both old catalog/storage readers support the current formats. Otherwise recover a verified pre-upgrade installation into an explicit recovery directory. No multi-node rolling-upgrade system is included in this standalone scope.
