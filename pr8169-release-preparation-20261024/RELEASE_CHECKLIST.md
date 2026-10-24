# PR #8169: checks after the LibRI release

The PR remains a draft. ABACUS preparation commit: `1bd79c473134b366fa45f422e0efd0c54491c43c`.
Development dependency: upstream LibRI `a0661cbb4b4f89ceeb23e040d49accb00943093f`, DDLA `v0.0.4` (`9c404ac65148ec1b48977b846f38ba6ef9e134f7`).

1. Resolve the official LibRI release tag to its commit and confirm it contains the merged #15 and #16 fixes. Check the actual tag tree; publishing a release against `master` is not sufficient evidence.
2. Inspect the release's `include/RI/version.h` before adding the minimum GPU version check in `cmake/modules/FindLibRI.cmake`. Do not assume the tag's four-part numbering maps directly to the three version macros. Keep the existing compile/link probe.
3. Limit the new minimum version requirement to GPU RI. Verify that the established CPU dependency remains usable, old GPU dependencies are rejected with an actionable message, and the supported release is accepted.
4. Replace the pending-release notice in `docs/advanced/install.md` with the official tag and reproducible installation instructions. Keep the DDLA release explicit. Remove obsolete branch/patch recipes.
5. Run the prepared CPU/GPU input, dependency, CLI and HSE checks with the exact release sources. Preserve complete command/build/run logs and source checksums. Existing reference files and tolerances must remain unchanged.
6. Update the PR description with the release and results. Keep the PR a draft until the user authorizes marking it ready.

The current verification scripts and source manifest are in this directory. They use an isolated build and require no patch to ABACUS or LibRI.
