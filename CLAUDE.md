## CD (semver push-CD)

- Every change declares significance: agents set `change_significance` on
  `change_summary` (major = breaking, minor = feature, patch = fix/other);
  humans set it via a `semver:<level>` label on the PR.
- Agents never merge PRs. The pipeline merges bot-authored PRs on green
  required checks, cuts the semver tag from the label, publishes artifacts
  at vX.Y.Z, propagates the version pin to the parent repo, and
  tatara-helmfile auto-applies it to the cluster. The operator closes the
  originating issue on apply success.
- Never hand-edit a deploy pin. Never re-run a green release job, tag mode
  is not idempotent.
