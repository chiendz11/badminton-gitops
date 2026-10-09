# Application producer integration

The current app repository has CI but no ECR publisher/repository_dispatch producer. This task implements the receiving infrastructure/GitOps side and does not modify that repo. Before first release, implement a trusted app main-branch publisher using the infrastructure output `app_publisher_role_arn` and a protected `production` environment.

## Producer responsibilities

1. Detect deployable changes in the monorepo. A Booking pricing module change selects `booking-core`, not a separate pricing image.
2. Require app CI success, build the actual deployable Dockerfile and push a unique immutable ECR tag. Obtain the registry digest, not just the local image ID.
3. For Booking, also publish the existing Dockerfile's `build` target as a separately tagged migration image in the same component repository. Supply its registry digest as `migration_digest`. Identity/Commerce publishers must supply migration images containing their Prisma CLI/schema as those app implementations become available.
4. Sign each digest with Cosign keyless GitHub OIDC and bind the source commit:

```bash
cosign sign --yes -a source_commit="$GITHUB_SHA" "$ECR_REPOSITORY@$RUNTIME_DIGEST"
cosign sign --yes -a source_commit="$GITHUB_SHA" "$ECR_REPOSITORY@$MIGRATION_DIGEST"
```

The second command applies to Node database components only. Keep the trusted signing workflow path/branch stable and register its exact certificate identity in GitOps.

5. Dispatch a strict v1 release contract with component, runtime/migration digests and the app main commit. Use a scoped short-lived GitHub App token installed on GitOps; do not give the app publisher EKS credentials.

## Runtime assumptions

| Component | Existing image/runtime contract |
| --- | --- |
| web/admin | nginx image from current Dockerfiles; GitOps bypasses Docker-only template entrypoint and supplies a non-root 8080 configuration |
| api-gateway | port 8081, BOOKING_CORE_URL, AI_SERVICE_URL, JWT/metrics configuration; /health/live and /health/ready |
| booking-core | port 3000, production mode, demo auth disabled, runtime DB/JWT/metrics secret; /health/live and /health/ready |
| ai-service | port 8000, own PostgreSQL URL, Groq-compatible provider config, JWT/metrics/LLM secret; /health/live and /health/ready; Alembic + app migration hook |
| identity/commerce/social/content/notification/storage | future image contract: port 3000, /health and /ready, per-service secrets, authenticated /metrics |

Gateway ConfigMap includes future service origin URLs and the guide's deployable boundaries. The current gateway only consumes Booking/AI origins; adding auth/commerce/social/etc. routes requires app source changes. The receiver does not invent route code inside GitOps.

Social's two replicas require an actual Socket.IO Redis adapter implementation. Notification consumers need idempotency and retry/DLQ behavior in app code. AI must enforce allowed read-only Booking tools at the API layer in addition to the network/credential restrictions here. No Pod manifest can supply those application guarantees.

The initial frontend nginx configuration serves static SPA assets and `/health`; ALB routes `/api`, `/graphql`, and `/socket.io` directly. `/admin` on the public domain redirects to a separate admin host, whose root renders the existing admin SPA. This keeps its root-relative asset/router paths valid without modifying app builds.

Metrics names for Booking, Gateway and AI are aligned with their current instrumentation. Some guide-inspired PayOS/social/queue/fallback alerts are reserved contracts whose metrics/exporters are not present yet; implement them in app/platform monitoring before expecting those alerts to produce data.
