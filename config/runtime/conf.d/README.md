Only files ending in .conf are loaded.
site.conf.example is ONE COMPLETE frontend/Spring Boot site with its security policies active.
Edit the deployment values in nginx.conf and site.conf.example, provide real certificates,
then rename site.conf.example to site.conf. No per-option files need to be selected.
Install its default listeners once per address/port. See SECURITY-CONFIG.md.
