## Summary

Describe the change.

## Testing

List the checks that were run.

- [ ] `ruff format --check src tests`
- [ ] `ruff check src tests`
- [ ] `pytest`

## Safety

- [ ] The change does not allow arbitrary privileged commands.
- [ ] Protected package checks remain enforced.
- [ ] Filesystem deletion remains restricted to approved locations.
- [ ] New removal behavior includes tests.
