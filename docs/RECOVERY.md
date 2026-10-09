# Recovery through reviewed state

For an image regression, use the recovery workflow on main with an allowed component, a full historical GitOps commit SHA and a reason. That commit must be in current main history and contain `state/<component>-release.yaml`. The workflow fetches that known release, verifies its app-main provenance/CI/signatures, restores runtime/migration digest entries and proposes a PR. It never force-syncs the cluster or trusts a caller-supplied arbitrary image repository.

The referenced images and Cosign signature artifacts must still exist in ECR. Infrastructure retains tagged history; do not manually remove image tags/digests needed by recovery. Older releases signed by a retired workflow identity require an explicit trusted verifier-policy change before recovery, not silently bypassed verification.

Review compatibility before merging. Prisma/Alembic hooks run on sync, including a rollback PR. Expand/deploy/contract schema discipline is required so an older runtime does not misread a newer database. Never treat an image rollback as reversal of a destructive migration; restore/fix data through the approved database recovery plan.

Config regressions use a normal ConfigMap revert/fix PR. Secrets rotate in AWS with controlled Pod restart where necessary. Infrastructure faults belong to `badminton-infras`; restored/failover endpoints require platform reconcile and runtime URL updates. An AI/social/notification fault should be handled within its own Application instead of rolling back unrelated Booking workloads.

For private managed endpoint IP changes, run platform reconcile immediately and merge its network-rule update after review. The 30-minute scheduler proposes updates but does not guarantee automatic recovery: the PR must still be adopted. Avoid broadening AI egress to every database to hide stale IP rules.
