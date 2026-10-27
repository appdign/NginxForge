"""Render a single site.conf for deployment/tests; no runtime helper is required."""
from pathlib import Path
import re
from urllib.parse import urlsplit
from common import ROOT

def quoted(value):
    value=str(value).replace('\\','/')
    if any(c in value for c in ['"','\n','\r','$',';','{','}']):
        raise ValueError('Unsafe configuration path')
    return '"'+value+'"'

def external_rule(site_id, origin):
    if not re.fullmatch(r'[A-Za-z0-9_]+',site_id):
        raise ValueError('Literal site ID required')
    value=urlsplit(origin)
    if value.scheme not in ('http','https') or not value.hostname or value.username or value.password or value.path or value.query or value.fragment:
        raise ValueError('Exact HTTP(S) origin or leading subdomain wildcard required')
    name=value.hostname
    if name.startswith('*.'):
        base=name[2:]
        if not re.fullmatch(r'[A-Za-z0-9.-]+',base): raise ValueError('Invalid wildcard')
        authority=r'([a-z0-9-]+[.])+'+re.escape(base)
    else:
        if not re.fullmatch(r'[A-Za-z0-9.-]+',name): raise ValueError('Invalid origin host')
        authority=re.escape(name)
    if value.port is not None: authority+=':'+str(value.port)
    return '    ~*^'+re.escape(site_id)+'[|]'+value.scheme+'://'+authority+'$ $http_origin;'

def embed_domain(value):
    value=str(value)
    if value and not re.fullmatch(r'(?:\*\.)?[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*',value):
        raise ValueError('Embedding domain must be a hostname or leading *. wildcard; no scheme, port or path')
    return quoted(value.lower())

def render_sites(sites, rules=()):
    if not sites: raise ValueError('At least one site is required')
    source=(ROOT/'config/site-template.conf').read_text(encoding='utf-8')
    prefix,block=source.split('# BEGIN SITE\n',1)
    block,end=block.split('# END SITE',1)
    sites=[dict(spec,site_id='site_'+str(index+1)) for index,spec in enumerate(sites)]
    first=sites[0]
    ids={spec['host']:spec['site_id'] for spec in sites}
    if len(ids)!=len(sites): raise ValueError('Duplicate virtual host')
    def values(spec):
        host=spec['host']
        if not re.fullmatch(r'[A-Za-z0-9.-]+',host): raise ValueError('Literal host required')
        for field in ['spring','storage']:
            if not re.fullmatch(r'[A-Za-z0-9.:-]+',spec[field]): raise ValueError('Fixed backend required')
        return {'HOST':host,'SITE_ID':spec['site_id'],'EMBED_DOMAIN':embed_domain(spec.get('embed_domain','')),'CERT':quoted(spec['cert']),'KEY':quoted(spec['key']),'ROOT':quoted(spec['root']),
                'SPRING':spec['spring'],'STORAGE':spec['storage'],'BODY':spec.get('body','1g'),
                'HTTP_LISTEN':spec.get('http_listen','80'),'HTTPS_LISTEN':spec.get('https_listen','443'),
                'HTTPS_AUTH_PORT':spec.get('https_auth_port','')}
    def replace(text,spec):
        for name,value in values(spec).items(): text=text.replace('@@'+name+'@@',value)
        if '@@' in text: raise ValueError('Unresolved deployment values')
        return text
    prefix=replace(prefix,first)
    prefix=prefix.replace('    # EXTERNAL_ORIGIN_RULES','\n'.join(external_rule(ids[host],origin) for host,origin in rules) or '    # 현재 외부 허용 목록은 비어 있습니다.')
    return '\n'.join('# BEGIN SITE: '+spec['site_id']+'\n'+replace(block,spec)+'# END SITE: '+spec['site_id']+'\n' for spec in sites)+'\n'+prefix+end
