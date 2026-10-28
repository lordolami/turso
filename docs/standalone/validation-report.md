# Documentation validation report

This package specifies proposed software. Validation checks the documents and contracts; it does not claim the platform is implemented or that native/database acceptance tests have passed.

## Audited baseline

- Date: 2026-10-28.
- Upstream repository: tursodatabase/turso.
- Audited source: 017ea183c2a323a66d515448e4df464b6181bb36.
- Working branch: codex/standalone-platform-docs, based directly on that upstream commit.
- Fork: lordolami/turso, reused because it already existed; fork main was not rewritten.
- Work completed here: source audit, proposed product/implementation documentation, declarations, schemas, inventories, and documentation validation tools.

## Checks performed

| Check | Result |
|---|---|
| Documentation checker | Passed |
| Markdown chapters/index/report | 26 documents; approximately 27,000 words excluding this report |
| Local documentation links | 65 checked, including report links |
| JSON parsing and duplicate-key rejection | 7 JSON files passed |
| Operation contracts | 170 unique operations with HTTP/CLI/MCP/dashboard mappings, permissions, schema references, jobs, and retry contracts |
| Requirements | 124 individual records; ranges agree with product-scope tables and owning documents exist |
| Private catalog syntax | 45 tables parsed by independent SQLite 3.53.1; foreign keys enabled, referenced tables present, empty-catalog FK check passed |
| Configuration example | Passed against the explicitly supported schema keyword subset |
| Invalid configuration cases | 6 rejected: unknown root key, cloud key, cluster key, zero active budget, missing PostgreSQL configuration, invalid operator-count type |
| Query examples and values | Request/result examples validate; JSON-number integers and text masquerading as SQL null rejected; JSON null and empty blobs remain distinct |
| Source evidence | 29 anchored records; source hashes verified with documented LF normalization |
| Complete upstream table inventory | 1,200 status-bearing data rows match the two source compatibility documents, including Not Needed entries and the status legend |
| Proposed C header | gcc C11 and g++ C++17 syntax-only checks passed; no native implementation linked |
| Generated inventory determinism | Regeneration produces identical bytes at the audited source revision |
| Whitespace | git diff --check and staged diff check passed before commit |

The checker is [tools/check_standalone_docs.py](../../tools/check_standalone_docs.py). It uses Python's standard library. Its schema validator implements the keyword subset present in this package; it is not a complete JSON Schema implementation or protocol conformance suite. Format/cross-field checks such as TLS exposure, numeric range by native type, array dimensions, filesystem identity, runtime capability policy, and actual secret custody remain application implementation obligations.

The generator is [tools/generate_standalone_contracts.py](../../tools/generate_standalone_contracts.py). It regenerates operation/requirement/source inventories and source-evidence prose from reviewed definitions and the source tree. Source hashes describe normalized source text so Windows and Unix checkouts can reproduce them.

## Reproduce

~~~text
python tools/generate_standalone_contracts.py
python tools/check_standalone_docs.py
gcc -fsyntax-only -std=c11 -x c docs/standalone/contracts/mira_engine.h
g++ -fsyntax-only -std=c++17 -x c++ docs/standalone/contracts/mira_engine.h
git diff --check
git diff --cached --check
~~~

The documentation checks ran on Windows using the bundled Python runtime. The C/C++ checks used the installed GCC tools. Exact reproducibility of a future product binary requires the separately specified pinned build pipeline; these checks produce no Mira executable.

## Not established by this change

No Go application skeleton, native bridge implementation, engine authorization patch, archive writer, snapshot/COW system, production PostgreSQL endpoint, or full MCP server has been implemented here. No native/Go product build, upstream Rust/Go runtime suite, PostgreSQL differential suite, crash-recovery experiment, security acceptance suite, or performance benchmark is claimed as passed. No binary-size, RAM, throughput, universal PostgreSQL parity, or production-readiness claim is made.

The independently parsed catalog is not a Turso runtime test. The header's valid declarations are not ABI layout/link/lifetime tests. Source compatibility entries are upstream assertions and can disagree with stubs; the audit records important examples. Unresolved engineering decisions remain visible in [decisions](decisions.md) and require implementation evidence under [testing and acceptance](testing-and-acceptance.md).
