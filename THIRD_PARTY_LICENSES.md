# Third-party software notices

NginxForge is an unofficial community build and is not an official NGINX distribution.
The MIT license covers NginxForge scripts, configuration and documentation only.
The upstream server and linked components retain their respective terms.

| Component | Upstream | License |
| --- | --- | --- |
| NGINX Open Source | https://github.com/nginx/nginx | BSD 2-Clause |
| headers-more | https://github.com/openresty/headers-more-nginx-module | BSD 2-Clause |
| OpenSSL 3.5 | https://github.com/openssl/openssl | Apache License 2.0 |
| PCRE2 | https://github.com/PCRE2Project/pcre2 | BSD 3-Clause; bundled notices also apply |
| zlib | https://github.com/madler/zlib | zlib license |
| musl libc | https://musl.libc.org | MIT with notices for incorporated code |
| GCC runtime, including libgcc if linked | https://gcc.gnu.org | GPLv3 with GCC Runtime Library Exception |

Each package includes unmodified source license files under `licenses/`.
zlib's license is in the packaged `zlib-zlib.h`; OpenSSL NOTICE is copied when present.
Linux build scripts also collect musl and GCC runtime notices from the build environment.
MSVC redistributable runtime is statically linked under the Visual Studio distribution terms;
Windows system DLLs are supplied by the operating system and are not redistributed.

Exact versions, commits, archive SHA-256 values and build options are recorded in
`build-info.json` and the release `build-manifest.json`. Source URLs are included so
the exact patched source can be reconstructed. See `patches/README.md` for modifications.
NGINX trademarks belong to their respective owners; no endorsement is implied.
