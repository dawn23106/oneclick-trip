# ChromaDB 1.5.9 security advisory handling

## Status

GitHub reported four upstream ChromaDB vulnerabilities on 2026-09-02:

| GHSA | Severity | Project exposure |
| --- | --- | --- |
| GHSA-36p7-vc44-83pf | Critical | Collection update endpoint code injection |
| GHSA-f4j7-r4q5-qw2c | Critical | Pre-authentication collection creation code injection |
| GHSA-2wm9-hf6c-p5cr | High | Cross-tenant authorization bypass |
| GHSA-xph7-9rjv-w5fr | High | RBAC resource-scope validation bypass |

The newest published PyPI and container release is `1.5.9`, and GitHub lists no
patched version for these advisories. Removing the package without replacing the
vector store would disable the reviewed travel knowledge base and RAG retrieval.

## Compensating controls

- Production does not publish Chroma's port to the host or the public network.
- Chroma is attached only to Docker's `vector_internal` network.
- `vector_internal` is marked `internal: true` and is shared only by `ai` and
  `chroma`; backend, admin, MySQL, Redis and the reverse proxy cannot call the
  Chroma API directly.
- End users access retrieval through the authenticated Spring Boot and FastAPI
  business flow. No generic Chroma endpoint is proxied by Nginx.
- The development binding remains loopback-only (`127.0.0.1:8001`).

These controls substantially reduce reachability while retaining current RAG
functionality. They do not claim to patch the upstream implementation.

## Follow-up

When Chroma publishes a release outside the affected ranges, update both the
Python dependency and container image together, regenerate `uv.lock`, run the
vector-store and knowledge-pipeline tests, rebuild the AI image, and remove this
temporary risk acceptance after verifying the GitHub alerts are closed.
