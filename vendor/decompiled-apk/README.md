# Decompiled APK libraries (arm64-v8a)

These shared objects were extracted from a user-supplied APK and are kept as
**analysis/reference inputs only**.

They are deliberately not copied into the APK and do not replace the libraries
built from this repository's source. The Android CI workflow runs
`tools/inspect_apk_elf.py` to record ELF architecture, SONAME, build ID,
DT_NEEDED dependencies, exported dynamic symbols, SHA-256 hashes, and
same-name comparisons against the native build.

## Files

- `libdm.so`
- `libmain_hook.so`
- `libfile_redirect_hook.so`
- `libgsl_alloc_hook.so`
- `libhook_impl.so`

ABI directory: `arm64-v8a`.

Do not package or load any of these files until their origin, licensing,
dependencies, JNI contract, and compatibility with the current app have been
reviewed. In particular, a matching filename does not establish ABI or API
compatibility.
