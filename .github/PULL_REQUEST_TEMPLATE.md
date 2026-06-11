# Summary

<!-- What does this change and why? -->

## Type
- [ ] New agent / reasoning step
- [ ] New MCP tool or data source
- [ ] New incident scenario
- [ ] Bug fix
- [ ] Docs / chore

## Checklist
- [ ] `PYTHONPATH=src python tests/test_pipeline.py` passes
- [ ] Both scenarios still resolve to their correct, distinct root causes
- [ ] No secrets or keys committed (`.env` stays untracked)
- [ ] Reasoning stays grounded — new findings tag the hypotheses they support/refute

## Notes for reviewers
<!-- Trace output, screenshots, or anything that helps review -->
