# Retry an existing npm release without changing its tag

`npm publish pkg/name.tgz` treats the unqualified path as a GitHub shorthand.
Use `npm publish ./pkg/name.tgz` to publish the tested local tarball.

An existing release tag must remain immutable even when its original workflow
contains a publication bug. The types workflow can therefore be dispatched from
protected `main` with `release_tag=ts-types-v1.4.0` after the repaired workflow's
required PR and main checks pass.

The retry validates an existing annotated tag, requires the complete `typescript`
Git tree to equal the running workflow's tree, and requires the original shared
gate and required-check list to be byte-identical. It runs that same gate against
the tag's exact source commit: the version, main ancestry, and every original
required release check must pass. Downstream jobs check out only that verified
ref, rebuild/test/pack it, and publish the tested artifact with provenance.

Normal publication retains the existing `npm` environment restricted to release
tags. Before dispatching a retry, an administrator must configure `npm-retry`
with the same required human reviewer and selected deployment branch `main`.
The retry requires human approval after its own successful gate and tested build;
it cannot run from feature branches. The normal environment's rules stay intact.

```sh
gh workflow run publish-ts-types.yml -R Actenon/actenon-protocol --ref main \
  -f release_tag=ts-types-v1.4.0
```

Compare the retry's tested tarball with the frozen release rehearsal before
approving its deployment. Verify npm's public tarball and post-publish registry
import before continuing the ecosystem release graph. Do not move an existing
tag, bypass review, create an off-graph tag, or advance past a failed publication.
