## Summary

<!-- One-paragraph summary of the change. -->

## Protocol impact

- [ ] No wire-format change (PATCH only)
- [ ] Compatible addition (MINOR bump — new optional field, new refusal code, new identifier prefix)
- [ ] Breaking change (MAJOR bump — see VERSIONING.md § "What counts as a breaking change")

If a MINOR or MAJOR bump: link to the CHANGELOG.md entry.

## Conformance

- [ ] All existing conformance vectors still pass (`python -m pytest conformance/python/`)
- [ ] New conformance vectors added for any new code/field/prefix
- [ ] TypeScript typecheck still passes (`cd typescript && bun run typecheck`)
- [ ] ruff lint clean (`python -m ruff check python/ conformance/python/`)

## Compatibility

- [ ] No existing identifier prefix removed or redefined
- [ ] No existing refusal code removed (deprecation is allowed with `deprecated_since`)
- [ ] No canonicalisation profile change
- [ ] Existing `FailureCode` enum aliases preserved (see `refusals/catalogue.v1.yaml`)

## Documentation

- [ ] Protocol specs updated (`protocol/*.md`)
- [ ] JSON Schemas updated (`schemas/*.v1.json`)
- [ ] CHANGELOG.md entry added
- [ ] No doc-implementation contradictions introduced (see audit finding DC-01..DC-16)

## Reviewer checklist

- [ ] Wire format is the source of truth (schemas/*.v1.json), not the markdown
- [ ] No policy/approval/budget/tenant/credential/adapter/persistence concerns introduced into the protocol repo
- [ ] `execution_mode` remains explicit on every artefact (no inference from deployment location)
- [ ] Disclosure policy preserved: `SIGNATURE_INVALID` etc. never appear as `disclosed_code` under public policy
