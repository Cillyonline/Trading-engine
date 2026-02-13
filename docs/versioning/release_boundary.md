# Release Boundary Model

## 1. Definition of a Release

A release is a formally declared, versioned state of the repository.
A release corresponds to exactly one version number.
A release is immutable once declared.

Not every merge or commit is a release.
Releases are discrete, intentional events.

## 2. Commit → Version → Tag Relationship

A release corresponds to a specific commit.
The commit is identified by a version tag.
The tag format is `vX.Y.Z`, and the tag must match the project version exactly.
A version increment is finalized at the moment of release tagging.

Multiple commits may precede a release.
Only the tagged commit represents the release boundary.

## 3. Version Increment Timing

Version increments are determined before release.
The increment type (MAJOR/MINOR/PATCH) is derived from `change_enforcement.md`.
The new version becomes authoritative only at release declaration.

Commits may exist between releases without changing the official version.
The version number represents the latest released state, not HEAD.

## 4. Release Boundary Expectations

A release must satisfy Definition of Done for included changes.
All included changes must comply with enforcement rules.
The release boundary freezes externally observable behavior for that version.

## 5. Non-Goals

No automation is defined.
No CI-based tagging enforcement.
No GitHub release workflow defined.
No runtime version resolution defined.
