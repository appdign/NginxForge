# External module policy

headers-more is downloaded at the commit and SHA-256 recorded in
`config/dependencies.lock.json`, then statically linked with `--add-module`.
No upstream source tree is vendored. The same module is mandatory on every CPU/OS.
Windows compatibility is established by MSVC compilation and the native runtime
suite, not inferred from the module's Linux compatibility list.
