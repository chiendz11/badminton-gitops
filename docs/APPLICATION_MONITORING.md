# Application-owned monitoring

The app repository owns the application ServiceMonitor templates, Prometheus rule files and Grafana dashboard JSON in `monitoring/chart`. GitOps installs kube-prometheus-stack and reconciles an explicitly pinned version of that chart through `applications/application-monitoring.yaml`. There are no per-workload ServiceMonitor/PrometheusRule copies in this repository.

## First release

1. Review, commit and publish the chart in `chiendz11/badminton_system`.
2. Set `spec.source.targetRevision` in `applications/application-monitoring.yaml` to that full 40-character app commit SHA. The initial `UNCONFIGURED_MONITORING_COMMIT` marker cannot be synced and automated sync remains disabled.
3. Review environment Helm values. The default enables Booking Core, API Gateway and AI only. Enable future service monitoring only after real images, runtime secrets and compatible metrics exist.
4. Confirm kube-prometheus-stack CRDs, target Services and monitoring secrets are available before manually syncing application monitoring. Secret names remain `<service>-secrets`, key `METRICS_TOKEN`; no token values live in this chart.
5. Check targets, rule evaluation and the **Badminton — Backend overview** dashboard in Grafana before enabling automated sync in a reviewed GitOps change.

The source revision is deliberately unconfigured until the first reviewed chart release exists. A moving branch such as `main` is rejected by the GitOps policy for this Application.

## Ownership

| Resource | Source |
| --- | --- |
| Application metrics instrumentation, rules and dashboards | App repository |
| Application ServiceMonitor/PrometheusRule and dashboard ConfigMap templates | App repository's Helm chart |
| Chosen app commit, environment labels/namespaces, enabled services | This GitOps Application's source/Helm values |
| Prometheus/Grafana/Alertmanager platform chart, storage and platform/Argo monitoring | GitOps repository |
| AWS resources | Infrastructure repository |

Compose reads the same canonical rule/dashboard files from the app checkout. Kubernetes discovery and credentials are rendered as ServiceMonitor references; GitOps does not import the local `prometheus.yml` with Docker DNS targets.

## Adoption and rollback

If a cluster already contains monitoring resources from the old workload Applications, review resource tracking and transfer ownership to `application-monitoring` before pruning the previous owner. The new Application uses the existing resource names. Roll back application monitoring by pinning a previous reviewed app commit with compatible metric contracts, independently of the platform chart version.

Six future services keep disabled, proposed rule definitions in the app chart. Placeholder metrics are not runtime evidence. HTTP rule thresholds are now defined once in the app sources; no manually maintained production copy remains here.
