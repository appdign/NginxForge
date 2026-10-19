Only files ending in .conf are loaded here.
Edit deployment values and provide real certificates, then rename site.conf.example to site.conf.
Each include in site.conf is an ON/OFF switch: add # to disable, remove # to enable.
Policies are in conf/policies, outside this directory, and never loaded by a wildcard.
Frontend/API switches are independent. HTTP-only TLS policy is in nginx.conf.
Keep shared maps/zones and add_header_inherit merge. See SECURITY-CONFIG.md.
