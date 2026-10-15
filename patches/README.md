# Minimal upstream patch

`0001-remove-error-page-identity.patch` deletes only the identity footer line
from the three built-in special response tails. It does not change request parsing,
TLS, error routing, headers, status codes, or version information in `nginx -v/-V`.
The source copyright and license notices are retained.

The exact-match applicator refuses missing, duplicate or changed deletion lines.
Any upstream drift blocks every release until reviewed. The identical patch hash
is required for Linux AMD64, Linux ARM64 and Windows AMD64.

headers-more implements configurable Server header changes/removal and arbitrary
response header filtering as a static external module. It does not edit error bodies,
which is why this separate three-line patch is needed. Some core-controlled headers,
such as Connection, cannot be removed with headers-more; no such support is claimed.
