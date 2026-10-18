# Evidence

| | |
|---|---|
| tested commit | `09a8567d6b7fe945ecea5b4662f0881919a5b96c` |
| pipeline run | https://github.com/srujan0404/odd-even/actions/runs/39106762514 |
| published image | `ghcr.io/srujan0404/even-odd:09a8567d6b7fe945ecea5b4662f0881919a5b96c` |
| runtime proof | [docs/evidence/09a8567d6b7fe945ecea5b4662f0881919a5b96c.txt](evidence/09a8567d6b7fe945ecea5b4662f0881919a5b96c.txt) |

## What the runtime proof shows

1. **Source -> pipeline:** the Actions run for the commit passes all checks, and the CI smoke test checks `/version` equals the sha.
2. **Pipeline -> image:** the publish job pushes `even-odd:<sha>` to ghcr.
3. **Image -> cluster:** `helm history` shows `image <sha>`, and all pods run that image with the same version label.
4. **Cluster -> user:** smoke test through the ingress (even, odd, negative, bad input, missing input, version).
5. **Signals:** Prometheus scraping every pod, requests by status, success ratio and p95, alert states, log lines, Jaeger traces.
6. **Security:** PSA rejects a non compliant pod, NetworkPolicy blocks other namespaces, the container is uid 10001 with a read only filesystem, `/metrics` is 404 from outside.

## Limitations
- Single node kind cluster, so a node failure takes everything down.
- Deploying to the laptop cluster is a manual command after publish.
- Prometheus and Jaeger data is lost when the cluster is deleted.
