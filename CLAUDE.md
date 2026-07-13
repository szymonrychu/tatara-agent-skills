## CD (semver push-CD)

- Every change declares significance: agents set `change_significance` on
  `submit_outcome` (major = breaking, minor = feature, patch = fix/other);
  humans set it via a `semver:<level>` label on the PR.
- Agents never merge PRs, and no MCP tool exposes merge. Merge is an
  OPERATOR action, triggered by a review agent's accepted approval verdict
  against the reviewed head SHA. Auto-merge is NEVER armed. Once the
  operator has merged, the pipeline cuts the semver tag from the label,
  publishes artifacts at vX.Y.Z, propagates the version pin to the parent
  repo, and tatara-helmfile applies it to the cluster. The operator closes
  the originating issue on apply success.
- Never hand-edit a deploy pin. Never re-run a green release job, tag mode
  is not idempotent.
