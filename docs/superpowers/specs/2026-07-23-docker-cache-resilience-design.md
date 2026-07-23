# Docker Cache Resilience Design

## Context

The Docker Publish workflow builds multi-platform images and exports BuildKit
layers to the GitHub Actions cache with `mode=max`. A cache reservation or
upload failure currently fails the entire build step, even when the image
build and registry publication are otherwise successful. The repository has
accumulated substantial GitHub Actions cache usage, making this failure mode
likely during release publication.

## Design

Keep GitHub Actions caching as an optimization, but make it smaller, isolated,
and non-blocking:

- Assign cache entries an explicit scope based on the workflow event so pull
  request and release builds do not share the default `buildkit` scope.
- Use `mode=min` to export only the layers needed to reuse the final image,
  reducing cache storage and reservation size.
- Set `ignore-error=true` on cache export so cache service failures do not
  block image construction or publication.
- Use the same scope for cache import and export.

No image tags, platforms, registry authentication, signing, or release
metadata behavior changes.

## Error handling

Build, push, signing, and release metadata remain fail-fast. Only the
best-effort cache export is allowed to fail, because cache availability does
not affect the correctness of the published image.

## Verification

Run the repository pre-commit hooks against the workflow and design document,
then inspect the final diff. A subsequent Docker Publish run should confirm
that cache reservation failures no longer fail the job.
