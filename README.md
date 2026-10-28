# Mira

A standalone, self-hosted SQL database platform built in Go around Turso's native engine, with SQLite and PostgreSQL frontends and complete MCP access.

**Current status:** product specification and source audit. The application executable has not been implemented yet.

**[Read the full specification](docs/standalone/README.md).**

This repository contains our documentation, proposed contracts, and two documentation maintenance tools. The Turso source checkout is separate; its engine code, tests, examples, other language bindings, and build tooling do not belong in this project folder.

## Folder layout

~~~text
mira/
  README.md
  THIRD_PARTY_NOTICES.md
  docs/standalone/       product design, implementation details, contracts, examples
  tools/                documentation checker and contract generator
~~~

The local engine checkout is a sibling folder named `turso-engine`. Documentation links to upstream source use immutable GitHub URLs, so reading these documents does not require that checkout.

## Check the documentation

~~~text
python tools/check_standalone_docs.py
~~~

The checker validates the documentation alone. It also verifies source hashes and the compatibility inventory when a Turso checkout is available. It discovers `../turso-engine` automatically; set `MIRA_TURSO_SOURCE` to use another location. When the source is absent, the report explicitly marks source verification skipped.

Regenerating source-derived evidence requires that checkout:

~~~text
python tools/generate_standalone_contracts.py
~~~

The design inventories are proposals. Passing their checks does not prove a working server, native compatibility, security, or a lightweight executable.
