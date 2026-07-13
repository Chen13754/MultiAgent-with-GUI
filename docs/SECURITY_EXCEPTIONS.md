# Security exceptions

Security exceptions are machine-checked by `scripts/audit_dependencies.py` and
must have an expiry date. An expired exception fails CI and release builds.

## PYSEC-2026-311 / CVE-2026-45829

- Affected transitive package: `chromadb`, installed by CrewAI.
- Upstream issue: pre-authentication code injection in the ChromaDB FastAPI
  server's model-loading path.
- Product exposure: Multiagent Studio does not start a ChromaDB server and does
  not use CrewAI memory or knowledge. `memory=False` is explicit. The current
  desktop bundle still contains the transitive package because excluding it
  breaks CrewAI's import graph during packaged startup.
- Residual exposure: both the desktop bundle and the advanced-user CLI wheel
  contain the transitive dependency, so consumers must not enable ChromaDB
  server, memory, or knowledge features from this application environment.
- Owner action: update CrewAI/ChromaDB and remove the exception as soon as an
  unaffected compatible release exists.
- Expiry: 2026-08-15.

Reference: <https://osv.dev/vulnerability/PYSEC-2026-311>
