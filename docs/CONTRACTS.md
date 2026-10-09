# Contracts and renderer behavior

## Platform v1

The same strict schema is committed here and in infrastructure. It allows only region/cluster/VPC metadata, all 11 ECR repositories, each database's host/name/port/master secret ARN, TLS cache metadata, the AMQPS endpoint, application secret ARNs, the three add-on IRSA roles, Mongo destination CIDRs, and public/admin domain/certificate/zone metadata. Passwords/API keys/arbitrary extra properties are rejected.

The schema fixes `environment=production`, `schema_version=v1` and the initial platform cluster name `badminton-prod`. Changing account/name/region is a deliberate contract migration; update both schema copies and review image transitions separately. The current renderer validates that each ECR URL is exactly the registered component's repository under the same account/region/cluster prefix. IRSA and secret/certificate references must belong to that account and region. App secrets must remain under `badminton/prod/`.

Run the renderer in the later automation phase:

```bash
python -m automation.platform_reconcile.renderer platform-contract-v1.json
```

It updates add-on roles/values, ClusterSecretStore region, CORS/config endpoints, each service's secret references, ALB/ExternalDNS metadata and managed endpoint NetworkPolicies, then saves a stable sorted platform state. It never selects, rewrites or enables a workload image. Reconciliation enables platform Applications only.

RDS/Valkey/MQ DNS names must resolve to IPv4 addresses inside the declared VPC. Their network rules use those endpoint addresses as /32s, rather than allowing all databases to all Pods. MongoDB egress accepts explicit /24 or narrower destination ranges. Reconciliation must run after failover/endpoint/IP changes; the scheduled receiver proposes DNS-refresh PRs every 30 minutes. It does not merge them automatically. Review and merge promptly when managed addresses change. IP changes can block traffic while review is pending; use a supported FQDN-aware policy platform in a later design if automatic failover without IP-policy refresh is required.

Master secret ARNs are metadata; manifests consume per-service runtime connection strings, not master secrets. The operator must align those runtime URLs with rendered endpoint metadata. API credentials never enter the ConfigMaps or platform state.

## Workload release v1

Payload template:

```json
{
  "schema_version": "v1",
  "environment": "production",
  "component": "booking-core",
  "image": {
    "repository": "<exact-platform-ECR-URL>/booking-core",
    "digest": "sha256:<64-lowercase-hex-runtime-digest>",
    "migration_digest": "sha256:<64-lowercase-hex-migration-digest>"
  },
  "source": {
    "repository": "chiendz11/badminton_system",
    "commit": "<40-lowercase-hex-main-commit>"
  }
}
```

Replace every placeholder. `migration_digest` is required by the receiver for identity, booking and commerce. Their migration image uses the same registered ECR repository as the runtime, with a distinct immutable digest. Booking's current Dockerfile `build` target has pnpm/Prisma; its runtime removes npm and production deployment omits the Prisma CLI. AI already contains Alembic and uses the runtime image digest for its migration.

The renderer allow-lists the component and constructs its destination path itself. Callers cannot supply an arbitrary path, namespace, ECR URL, resource fragment or ConfigMap content. It rejects zero/placeholder digests. MongoDB-backed workloads cannot release until actual destination CIDRs exist in platform state.

The receiver verifies that source commit is in app main's history, that the configured main CI workflow succeeded for that commit, and that Cosign's keyless certificate comes from the configured trusted image publisher workflow. The signed `source_commit` annotation must equal the release source commit for every runtime/migration digest. Recovery reuses this same verification.

Then it writes only that component's Kustomize image entries, Application auto-sync setting and release-history state. Edge can become automated after all four routed backend Applications have image pins. The image PR is subject to review and branch protections before Argo CD sees it.

## Dispatch envelope

Both receivers accept `client_payload.contract`, never arbitrary client payload fields as shell commands:

```json
{
  "event_type": "workload-release-v1",
  "client_payload": { "contract": "<the JSON object, not a string>" }
}
```

For platform handoff use event type `platform-contract-v1`. Manual workflow input `contract` is the serialized JSON string. The code loads the GitHub event file and parses it as data; no JSON is interpolated into a shell program. Dispatch sender must equal configured `DISPATCH_SENDER`.
