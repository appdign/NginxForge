# 분할 보안 정책과 site.conf 운영 설정

**기존 38개 정책 파일은 그대로 분리합니다.** 적용할 정책은 conf/site.conf의 각 include
줄로 ON/OFF합니다. 도메인·허용 출처·CSP 목적지·API·WebSocket·backend는 site.conf에서만
설정합니다. nginx.conf와 정책 파일에 운영 도메인을 입력하지 않습니다.

| 위치 | 역할 |
| --- | --- |
| conf/site.conf | 사이트별 도메인 한 줄, 인증서/root, 외부 허용 목록, CSP, API/WS/backend, 제한 값과 정책 include |
| conf/policies/server/*.conf | 목적별 공통 보안 규칙. 각 include 앞에 #을 붙여 해당 사이트에서 OFF |
| conf/policies/location/*.conf | 위치별 REST/WS 보안 규칙 |
| conf/policies/http/tls.conf | nginx.conf에서 한 번 include하는 공유 TLS 설정 |
| conf/nginx.conf | worker·로그·MIME·헤더 상속·공유 TLS와 site.conf 로드 |
| conf/mime.types | js/mjs는 application/javascript, css는 text/css |

## 배포 파일의 취약점 주석과 전체 구성

맞춤형 전체 구성본과 공개 플랫폼 패키지는 분할 정책 **38개 전체**를 제공합니다.
각 정책 파일 상단에서 `[KISA WEB-xx]` 또는 `[추가 강화]` 분류와 함께 다음을 확인할 수 있습니다.
- `[취약점]`: 해당 설정이 줄이는 정보 노출·불필요 메소드·권한/접근·자원 소진 등의 위험.
- `[조치]`: 실제 지시문이 적용하는 동작.
- `[별도 점검]`: 앱/OS/backend 또는 실제 운영 값에서 추가 확인할 부분.

공개 패키지의 `conf/site.conf`는 고객사 도메인/인증서를 담지 않는 초기 비활성 구성입니다.
주석이 있는 전체 사이트 원본은 `security/site-template.conf`에 별도로 포함합니다.
이 원본은 운영 conf에서 자동으로 로드하지 않으며 실제 값을 채워 활성 site.conf를 준비합니다.
템플릿을 그대로 include하거나 @@...@@ 토큰이 남은 파일을 운영 설정으로 사용하지 않습니다.

맞춤형 전체 구성 ZIP에는 conf/policies 38개와 실제 site.conf·공통 conf·오류 HTML을 함께 넣습니다.
이전 r10의 세 파일짜리 최소 업데이트 ZIP과 구분합니다. 기존 운영 도메인/경로/추가 CORS 설정은
유지해 병합하고 같은 prefix/계정으로 nginx -t 후 reload합니다.

## 도메인은 맨 위 한 줄만

각 사이트 구역의 첫 지시문 **server_name**에 실제 도메인을 한 번 입력합니다.
한 server가 HTTP와 HTTPS를 함께 수신하므로 두 블록에 도메인을 반복하지 않습니다.
리다이렉트·동일 출처 검사·현재 사이트의 WSS CSP는 허용된 현재 Host와 포트를 자동 참조합니다.
80/443 기본 포트는 생략 표기와 정규화하고 비표준 포트는 구분합니다.
알 수 없는 Host/SNI는 기본 리스너가 거부합니다.

NGINX의 server_name은 set 변수로 치환할 수 없습니다. 따라서 가짜 배치 변수 대신
server_name 자체를 단일 설정값으로 사용합니다. 실행 시 bat/템플릿 생성기는 필요 없습니다.
인증서 경로와 root에 도메인 이름을 직접 포함했다면 그 파일 경로는 별도의 실제 경로입니다.

가상호스트 추가 시 BEGIN SITE~END SITE 구역을 복사하여 도메인과 인증서/root/backend를
설정하고 site_id만 고유하게 지정합니다. 외부 허용 목록은 site_id로 구분하므로 자체 도메인을
그 목록에 다시 적지 않습니다. 공통 map/zone/기본 리스너는 중복 복사하지 않습니다.

## iframe 임베드 허용은 한 줄만

각 사이트 구역 맨 위에서 다음 **한 줄**만 지정합니다. 실제 운영 도메인은 site.conf에만
입력하며, nginx.conf/분할 정책에는 반복 입력하지 않습니다.

```nginx
set $site_embed_domain "*.example.org";
```

이 값으로 CSP frame-ancestors와 X-Frame-Options가 함께 계산됩니다.
빈값 `""`이면 기존처럼 동일 출처만 허용하고 X-Frame-Options: SAMEORIGIN을 발행합니다.
유효한 도메인이 있으면 동일 출처와 지정한 HTTP/HTTPS 부모만 허용합니다.
부모의 포트는 모두 허용하여 8000 같은 사내 포트도 포함합니다.
와일드카드는 하위 도메인과 그 아래 하위 도메인에 적용하며 최상위 example.org 자체와
example.org.evil 같은 악성 suffix는 허용하지 않습니다. 정확한 호스트 한 개도 지정할 수 있습니다.
형식은 호스트 또는 *.호스트이며 scheme/port/path를 넣지 않습니다. 잘못된 값은 동일 출처로 제한합니다.

외부 임베드 허용 시 충돌하는 X-Frame-Options는 발행하지 않고 upstream 헤더도 숨깁니다.
CSP frame-ancestors가 실제 허용 목록을 적용하며 ALLOW-FROM 같은 폐기된 헤더는 사용하지 않습니다.
중첩 iframe은 모든 상위 페이지의 출처가 허용 목록에 들어야 합니다.

**이 옵션은 iframe 허용만 변경합니다. API 프록시 목적지·CORS·WebSocket Origin·connect-src는
기존 설정 그대로입니다.** 같은 회사 프론트라도 다른 출처의 API 사용이 필요하면 기존 CORS
목록에서 별도로 선택합니다. iframe 로그인은 세션 쿠키의 SameSite와 브라우저 서드파티 쿠키 정책을
따로 확인합니다. 임베드를 허용한다고 인증/인가나 쿠키 정책이 자동 변경되지 않습니다.

사이트별 include와 주요 지시문 옆에 KISA WEB-01~WEB-26 번호/조치 목적을 표시했습니다.
CSP/프레임/추가 헤더는 `[추가 강화]`로 구분하고 KISA에 없는 항목 번호를 붙이지 않습니다.
계정·암호·OS ACL·LDAP·패치/로그처럼 앱 또는 운영에서 확인할 항목도 같은 파일 주석에 남깁니다.

## site.conf에서 찾을 곳

1. 맨 위 사이트 구역: server_name 한 줄, site_embed_domain 한 줄, 인증서, 키, root.
2. 같은 구역의 site_csp: 우리 화면에서 접근할 외부 API/WSS/CDN/SSO의 목적지.
   현재 사이트의 WSS는 자동 반영됩니다. 인라인 CSS만 허용하고 인라인 JS/onclick/eval은 차단합니다.
3. site_cors_mode와 site_ws_mode: 외부에서 우리 API/WS로 오는 브라우저의 출처 허용 방식.
   기본 restricted이며 각자 독립적으로 public을 선택할 수 있습니다.
4. 같은 구역의 location: /api/, /storagewiz/, /process_file/ 경로와 고정 proxy_pass,
   REST 메소드, 전달 헤더, WS timeout, 쿠키, 오류 가림과 요청 크기.
5. 사이트 구역 아래 site_external_origin map: 외부 웹사이트 허용 목록.
   키는 자체 도메인이 아닌 site_id와 허용할 Origin입니다. exact 또는 전체 일치 정규식을 사용합니다.
6. 맨 아래 자동 계산 map: 보통 수정하지 않습니다. API prefix 변경 시 site_api_path 분류도 맞춥니다.

기본은 동일 출처(프로토콜·호스트·포트 동일)입니다. 외부 목록은 API CORS와 WS Origin이
공유합니다. 공개 여부는 독립적이며 API public이 WS를 자동 공개하지 않습니다.
public API는 HTTP(S) Origin에 *를 응답하고 credentials 헤더는 내보내지 않습니다.
쿠키/세션 CORS는 restricted의 검증된 Origin만 응답합니다. null Origin은 거부합니다.
Origin 없는 일반 API 요청은 허용하지만 WS는 기본 거부하며 site_allow_originless_ws를
명시적으로 1로 선택해야 허용됩니다. Origin은 인증·인가·CSRF를 대신하지 않습니다.

외부 허용 목록의 정확한 한 출처 등록 형식은 아래와 같습니다(실제 site_id/외부 출처로 변경).

```nginx
"site_1|https://partner.invalid" $http_origin;
```

하위 도메인 전체를 허용할 때는 예를 들어 다음처럼 protocol/host/port 전체를 고정합니다.
상위 도메인 자체, 다른 scheme/port, 악성 suffix는 포함하지 않습니다.

```nginx
~*^site_1[|]https://([a-z0-9-]+[.])+partner[.]invalid$ $http_origin;
```

우리 화면에서 외부 API를 호출하는 것은 별개 방향입니다. 그 주소는 해당 사이트의
site_csp connect-src에 추가하고 상대 API의 CORS도 확인합니다. CSP는 정규식을 지원하지
않으므로 URL 출처 또는 *.host 형태를 사용합니다. 기본값에 포괄 와일드카드는 없습니다.

## 정책별 ON/OFF

site.conf에서 실제 적용 중인 include 줄 앞에 #을 붙이면 OFF, 제거하면 ON입니다.
CSP 값은 site_csp에서 바꾸고 정책 파일은 그대로 둡니다. csp.conf와 csp-spa.conf는 같은
변수 기반 발행 방식이며 동시에 include하지 않습니다.

```nginx
include policies/server/csp-spa.conf;
# include policies/server/csp-spa.conf;
```

위 두 줄 중 한 가지 상태만 사용합니다. OFF는 그 파일의 지시문을 제외한다는 뜻이며
NGINX 기본값/상위 설정/backend 정책이나 브라우저에 이미 남은 HSTS까지 취소하지 않습니다.
헤더 정책은 upstream 헤더 숨김과 edge 발행을 함께 관리하므로 OFF하면 backend 원본
헤더가 통과할 수 있습니다. CORS 헤더 include와 site.conf의 요청 Origin 검사도 별개입니다.
API/WS 허용 범위는 해당 사이트의 모드/목록으로 조정합니다.

고정 헤더·파일/관리 경로 차단·symlink·캐시·오류 페이지는 분할 정책에서 제공하고,
경로/backend/허용 출처/쿠키·업무 제한·메소드는 site.conf에서 직접 선택합니다.
기존 body-size/upload-body-size, timeout/rate/connection/cookie/proxy 정책 파일도 보존합니다.
필요하면 사이트의 같은 지시문 대신 그 기본값 include를 선택하되 중복 선언하지 않습니다.
methods-static은 정적 location에만 사용합니다. 혼합 server 전체에 넣으면 API POST도 막힙니다.
관리자 경로/CIDR은 site.conf에 작성하고 admin-acl.conf의 deny all을 마지막에 include합니다.

## 파일 서버와 CSS

파일 서버 기본 client_max_body_size는 요청 전체 1 GiB입니다. 파일+폼+multipart 형식과
JSON 본문에 적용하며 다운로드 제한은 아닙니다. 사이트별로 5m/1g 등을 선택합니다.
파일당 50 MiB·일반 폼 파라미터 5 MiB는 실제 Spring MVC/Tomcat에 별도 적용합니다.
[별도 backend 설정 참고](https://github.com/appdign/NginxForge/blob/main/docs/backend/application-upload.yml.example)는
NGINX가 자동 반영하지 않습니다. 실제 고객사 앱의 해당 제한 검증도 별도입니다.
IP 빈도는 초당 10r/s·burst 20, 동시 연결 기본 20이며 하루 접속 횟수 제한은 아닙니다.
WS read/send idle timeout은 3600초이며 총 연결 수명을 보장하지 않습니다.

CSS style 속성/태그/동적 스타일을 허용하고 동일 사이트 js/mjs는 정상 MIME으로 응답합니다.
인라인 JavaScript·onclick·eval은 계속 차단합니다. 외부 CDN은 site_csp의 해당 src에서
선택합니다. 더 엄격한 CSS 정책은 앱의 nonce/hash 연동이 필요하며 고정 nonce는 사용하지 않습니다.

## 배포와 검증

운영 conf에는 nginx.conf·mime.types·site.conf와 기존 38개 분할 정책만 제공합니다.
공개 배포 패키지에는 비활성 참고 원본 security/site-template.conf도 별도로 포함합니다.
샘플·이전 구성·backend YAML·코드 프롬프트는 저장소/별도 참고 묶음에 두며 conf에 섞지 않습니다.
공개 패키지의 초기 site.conf는 127.0.0.1:8080에서 요청을 거부하며 공개 포트를 열지 않습니다.
Windows의 예약된 80포트도 초기 문법 검사에 사용하지 않습니다.
실제 값으로 치환한 site.conf를 설치해야 서비스합니다. 생성용 원본은
[site-template.conf](https://github.com/appdign/NginxForge/blob/main/config/site-template.conf)입니다.
@@...@@ 토큰을 그대로 운영에 설치하지 않습니다.

기존 설치 전환 시 설정을 백업한 뒤 동일 OS 패키지의 conf와 html/__nginxforge_error.html을
함께 설치하고 실제 적용본 site.conf를 사용합니다. 이전 conf.d/map이나 정책을 중복 include하지
않습니다. 기존 NginxForge 1.30.6 실행 파일을 사용할 수 있으며 NGINX C 소스/의존성/패치는
이번 설정 변경으로 달라지지 않습니다. 이후 도메인/외부 출처/API 변경은 site.conf에서만 합니다.
운영 서비스와 같은 prefix/계정/-c 인수로 nginx -t를 통과한 뒤 reload하고 로그인·CSS·API·업로드·WS를 확인합니다.
이 저장소 작업은 실제 고객사 서버에 자동 적용하지 않습니다.

Linux AMD64/ARM64 모두 같은 분할 정책을 사용하며 symlinks.conf만 OS에 맞게 렌더링합니다.
Linux는 disable_symlinks 실행 거부를 검사합니다. Windows는 지원하지 않으므로 NTFS ACL과
reparse point를 운영에서 검토해야 합니다(WEB-12). 기본 실행 계정·키/설정 쓰기 권한·로그 회전·
backend 직접 포트·IPv6·신뢰 LB의 실제 IP 설정도 운영 범위입니다.

기준은 KISA의 2025-12-24 공개 2026 상세가이드 웹 서비스 WEB-01~WEB-26입니다.
[공식 게시물](https://www.kisa.kr/2060204/form?postSeq=22&page=1),
[공식 PDF](https://www.kisa.kr/post/fileDownload?menuSeq=2060204&postSeq=22&attachSeq=1&lang_type=KO).
PDF SHA-256: 44fe393981b244147be6af7423d99dc15633c089fad0bcb296cbe2371dde812d.
실제 인증서·고객사 backend/SSO·서비스·부하 검증과 KISA 점검 판정은 자동 인증하지 않습니다.

## 항목별 적용 범위

아래 이름은 원문 항목을 짧게 정리한 것입니다. ‘미대상’은 **NGINX 단독 구성**에서의
가이드 대상 제품 범위이며, 뒤에 Tomcat/IIS/JEUS나 별도 관리자 앱이 있으면 해당 계층을
별도로 점검해야 합니다. `security/kisa-2026.json`에 기계가 읽을 수 있는 같은 대응표를 제공합니다.

| 항목 | 주제 | NginxForge에서 제공하는 조치 | 별도 확인 |
| --- | --- | --- | --- |
| WEB-01 | 기본 관리자 이름 | NGINX 관리자 콘솔/기본 계정 미제공 | 가이드는 Tomcat/JEUS 대상, backend 관리자 계정 |
| WEB-02 | 관리자 비밀번호 | 기본 비밀번호 미제공, HTTPS 관리자 경로 예시 | Tomcat/IIS/JEUS 및 앱 비밀번호 정책 |
| WEB-03 | 비밀번호 파일 | credential 미배포, 웹 루트와 분리 지침 | 가이드 직접 대상 외, 파일/ACL·해시 관리 |
| WEB-04 | 목록 출력 | autoindex off, 디렉터리 요청 테스트 | 다른 vhost의 override |
| WEB-05 | CGI/ISAPI | CGI 실행 경로 미설정, 스크립트 요청 차단 | 별도 FastCGI/앱 실행 매핑 |
| WEB-06 | 상위 경로 | 독립 document root, 경로 이탈 요청 검사 | alias/rewrite 및 앱 경로 정규화 |
| WEB-07 | 잔여 파일 | dotfile·백업·설정 파일 차단 | 실제 불필요 파일 삭제·배포 정책 |
| WEB-08 | 전송 크기 | site.conf의 1g/5m 선택, 413 동작 검사 | 다운로드 크기/총량은 앱·저장소 |
| WEB-09 | 프로세스 권한 | Linux 비특권 worker 기본값, 운영 계정 지침 | Windows 서비스 계정·OS 권한 |
| WEB-10 | 프록시 | 고정 upstream, CONNECT 금지, 전달 헤더 재작성 | 불필요한 프록시/동적 목적지 설정 제거 |
| WEB-11 | 서비스 루트 | 사이트 public 디렉터리 분리 예시 | 실제 경로·소유자·웹 루트 밖 비밀 |
| WEB-12 | 링크 | Linux disable_symlinks 및 링크 차단 테스트 | Windows NTFS/ACL·재분석 지점 점검 |
| WEB-13 | 설정 노출 | 설정 확장자·경로 요청 차단을 추가 보완으로 제공 | 가이드 직접 대상은 Tomcat/IIS/JEUS |
| WEB-14 | 파일 접근 | 숨김/비밀 경로 차단, 관리자 IP 제한 예시 | 업무별 인증·인가, OS 파일 권한 |
| WEB-15 | 스크립트 매핑 | script/FastCGI 실행 미구성·확장자 차단 보완 | 가이드 직접 대상은 Tomcat/IIS/JEUS |
| WEB-16 | 헤더 정보 | 기존 headers-more 정적 모듈, 버전/Server 제거 | 앱 자체 본문·추가 vhost 설정 |
| WEB-17 | 가상 디렉터리 | 예시에서 alias/불필요한 가상 디렉터리 미사용 | 기존 alias와 앱 라우팅 목록 검토 |
| WEB-18 | WebDAV | DAV 모듈 미포함, 불필요 메소드 차단 | backend의 DAV endpoint |
| WEB-19 | SSI | ssi off, SSI 확장자 차단 | 다른 vhost의 SSI override |
| WEB-20 | TLS | HTTPS 예시, TLS 1.2/1.3와 cipher 설정 | 실제 인증서·갱신·신뢰·도메인 |
| WEB-21 | HTTPS 이동 | 허용된 현재 Host의 308 이동 설정 | 실제 도메인 적용·HTTPS 연결 |
| WEB-22 | 오류 정보 | 일반 오류 페이지와 기존 core 3줄 패치 | 앱/API 오류 스키마·민감 정보 |
| WEB-23 | LDAP | LDAP 인증 모듈/기본 연결 미제공 | 가이드는 Tomcat 대상, LDAP 인증 backend |
| WEB-24 | 업로드 분리 | 직접 uploads 경로 차단·별도 저장소 지침 | 앱 저장 경로, 내용 검증, 실행 금지·ACL |
| WEB-25 | 패치 | 업스트림 추적·공통 소스·전체 플랫폼 release gate | 의존성 업데이트 및 고객사 실제 적용 정책 |
| WEB-26 | 로그 권한 | 웹 루트 밖 로그, 비밀 query/cookie 제외 형식 | OS 파일 권한·umask·회전/보존 정책 |

## 추가 모듈 판단

헤더 제거/변경은 이미 세 플랫폼에서 검증된 headers-more를 계속 정적으로 포함합니다.
나머지 서버 설정은 NGINX Open Source 기본 모듈로 구현할 수 있습니다. 비밀번호 정책,
파일시스템 ACL, 다운로드 총량, LDAP backend 정책을 해결한다는 이유로 WAF를 추가하지 않습니다.
ModSecurity/CRS나 NAXSI 등 별도 WAF는 이 항목들의 운영 조치를 대체하지 않으며,
현재 세 플랫폼 동등 지원에 검증된 기능으로 포함했다고 주장하지 않습니다.

NGINX 근거: [core](https://nginx.org/en/docs/http/ngx_http_core_module.html),
[TLS](https://nginx.org/en/docs/http/ngx_http_ssl_module.html),
[proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html),
[headers-more](https://github.com/openresty/headers-more-nginx-module).
