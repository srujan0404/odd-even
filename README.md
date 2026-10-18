# Even or Odd

Small Flask app that tells you if a number is even or odd, set up to run on Kubernetes with CI/CD,
monitoring, tracing and basic security. The app is simple on purpose, the work is in how it is
built, deployed and run.

```
$ curl "http://even-odd.localhost:8080/check?number=10"
{"even":true,"number":10}
```

Why things are done the way they are: [docs/DECISIONS.md](docs/DECISIONS.md).
Proof that it works: [docs/EVIDENCE.md](docs/EVIDENCE.md).

## How it fits together

```
user
  │  http://even-odd.localhost:8080
  ▼
┌──────────────────────────── kind cluster (one node, on the laptop) ────────────────────────────┐
│                                                                                                │
│  ingress-nginx  ──/check, /version──▶  Service even-odd  ──▶  pod (gunicorn + flask)           │
│  (ns ingress-nginx)                    (ns even-odd)     ──▶  pod (gunicorn + flask)           │
│                                        HPA 2-5, PDB, NetworkPolicy        │         ▲          │
│                                                                           │ OTLP    │ scrape   │
│                                                                           ▼         │ /metrics │
│                                               Jaeger (ns observability)   Prometheus, Grafana, │
│                                                                           Alertmanager         │
│                                                                           (ns monitoring)      │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Request path: client -> localhost:8080 -> kind node port 80 -> ingress-nginx -> Service -> one of
the ready pods -> gunicorn -> Flask. Only `/check` and `/version` are routed by the ingress.

What can fail and what happens:

| failure | effect |
|---|---|
| one pod crashes / is killed | other pod keeps serving, readiness removes the bad one, k8s replaces it |
| bad release (crash or image missing) | new pod never gets ready, old pods keep serving, rollout stalls -> `helm rollback` |
| Jaeger down | app keeps working, spans are dropped |
| Prometheus down | app keeps working, we are blind (no alerts) |
| ingress down | app is up but unreachable from outside |
| the node (laptop) | everything is down, single node is the main limitation |

Commit to running app:

```
git push -> GitHub Actions: lint, tests, bandit, pip-audit, gitleaks, helm lint
         -> docker build (tag = commit sha) -> trivy scan
         -> deploy into a throwaway kind cluster -> smoke test checks /version == sha
         -> (main, or a manual run, after approval) push image to ghcr.io/srujan0404/even-odd:<sha>
         -> make deploy-release TAG=<sha>  (helm upgrade on the local cluster)
```

## Repo layout

```
app/                    flask app, metrics, tracing setup
tests/                  pytest
Dockerfile              multi stage, non root
helm/even-odd/          chart, values.yaml + values-local.yaml + values-ci.yaml
k8s/                    kind cluster config, namespace with pod security
monitoring/             kube-prometheus-stack values, jaeger
scripts/                cluster setup, deploy, smoke test, evidence
.github/workflows/      pipeline
docs/                   decisions and evidence
```

## Prerequisites

Tested on macOS (Apple silicon) with:

- Docker Desktop (give it at least 4 CPU / 6 GB RAM, the monitoring stack is the heavy part)
- kind 0.33, kubectl 1.34, helm 4.3
- python 3.12+ (only for running tests locally)
- trivy (optional, for `make scan`)

```
brew install kind kubectl helm trivy
```

## Run it

```
make install        # python venv + dev dependencies
make test           # unit tests
make cluster        # kind cluster + ingress-nginx + metrics-server + prometheus/grafana + jaeger (~5 min)
make deploy         # build image tagged with the current commit, load into kind, helm upgrade
make smoke          # end to end checks through the ingress
```

To deploy an image that the pipeline published instead of building locally:

```
make deploy-release TAG=<full commit sha>
```

Open the app at http://even-odd.localhost:8080/check?number=10 (`*.localhost` resolves to
127.0.0.1 in curl and browsers).

Other UIs (`make urls` prints these):

```
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80          # http://localhost:3000
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090  # http://localhost:9090
kubectl -n observability port-forward svc/jaeger 16686                     # http://localhost:16686
```

Grafana user is `admin`, the dashboard is called "Even Odd".

Running only the app, without kubernetes:

```
python -m app.app                          # dev server on 127.0.0.1:5000
docker build -t even-odd . && docker run -p 5000:5000 even-odd
```

## Release and rollback

```
helm -n even-odd history even-odd          # every revision with its image sha
helm -n even-odd rollback even-odd <rev>   # go back
```

Feature flag (no rebuild needed):

```
helm upgrade even-odd helm/even-odd -n even-odd --reuse-values --set config.showMessage=true
```

## Configuration

| value | default | what |
|---|---|---|
| `image.tag` | none, required | commit sha of the image |
| `replicaCount` | 2 | used when hpa is off |
| `autoscaling.enabled` | false (true locally) | hpa 2-5 pods on cpu 70% |
| `config.logLevel` | INFO | |
| `config.showMessage` | "false" | feature flag |
| `tracing.enabled` | false (true locally) | send traces to jaeger |
| `ingress.enabled` | false (true locally) | host even-odd.localhost |
| `networkPolicy.enabled` | true | |
| `serviceMonitor/alerts/dashboard.enabled` | false (true locally) | need kube-prometheus-stack |

## GitHub setup

- Settings -> Environments -> create `production`, add yourself as required reviewer
- After the first publish, set the ghcr package to public (or `docker login ghcr.io` before
  `make deploy-release`)

## Known limitations

- Single node kind cluster, so the two replicas sit on the same node and anti affinity cannot do much.
  A node failure takes everything down.
- CD stops at publishing the image. Deploying to the laptop cluster is one manual command because
  GitHub cannot reach it (see decisions doc).
- Jaeger and Prometheus keep data in memory / emptyDir, it is gone when the cluster is deleted.
- Alertmanager has no receiver configured, alerts are visible in the Prometheus / Alertmanager UI only.
- ingress-nginx is retired upstream; fine for local use, Gateway API would replace it.
- Environment required reviewers only work on public repos (or paid plans).
- No TLS on the local ingress.
- `even-odd.localhost` resolves to 127.0.0.1 on macOS and in browsers. On some Linux setups you may
  need `127.0.0.1 even-odd.localhost` in `/etc/hosts`.
