# KISA 2026 보안 설정과 도메인 샘플

기준은 KISA의 2025-12-24 공개 「2026 주요정보통신기반시설 기술적 취약점 분석·평가 방법
상세가이드」 웹 서비스 편입니다. 공식 표 p.272~273은 **WEB-01~WEB-26 총 26개**입니다.
[공식 게시물](https://www.kisa.kr/2060204/form?postSeq=22&page=1)과
[공식 PDF](https://www.kisa.kr/post/fileDownload?menuSeq=2060204&postSeq=22&attachSeq=1&lang_type=KO)를 참고하세요.
원본 PDF SHA-256: `44fe393981b244147be6af7423d99dc15633c089fad0bcb296cbe2371dde812d`.
이 배포는 KISA 인증 또는 고객사 점검 통과를 의미하지 않습니다. 적용 환경의 실제 설정,
계정·파일 권한·인증서·업스트림 애플리케이션을 함께 점검해야 합니다.

## site.conf에서 정책별 ON/OFF

정책은 **설정 목적별 파일 하나**로 나누고, 적용 목록은 한 `site.conf`에서 관리합니다.
기본값은 모든 정책 ON입니다. 각 include 앞에 `#`을 붙이면 해당 도메인에서 OFF,
제거하면 ON입니다. 프론트/API server 블록의 스위치를 각각 바꿀 수 있습니다.

```nginx
# ON
include policies/server/csp.conf; # ON: CSP 콘텐츠 출처 제한

# OFF: 실제 적용 줄을 아래처럼 바꾸며 두 줄을 동시에 남기지 않습니다.
# include policies/server/csp.conf;
```

| 위치 | 역할 |
| --- | --- |
| `conf/nginx.conf` | HTTP 공통 기반: 로그, MIME, CORS map, 요청 제한 zone, 헤더 상속 |
| `conf/conf.d/site.conf.example` → `site.conf` | 도메인·인증서·root·고정 backend와 정책별 include 스위치 |
| `conf/policies/server/*.conf` | server 정책. methods-static은 정적 location에서도 사용. wildcard 자동 로드 없음 |
| `conf/policies/location/*.conf` | REST 메소드·WebSocket처럼 해당 proxy location에서 선택하는 정책 |
| `conf/policies/http/tls.conf` | HTTP 문맥의 공유 TLS 정책. nginx.conf의 include로 ON/OFF |
| `conf/policies/http/default-listeners.conf` | 기본 Host/SNI 거부 리스너. site.conf 최상단에서 ON/OFF |

NGINX include 경로는 **conf 디렉터리 기준**입니다. 정책 파일은 `conf.d` 바깥에 두어
`conf.d/*.conf`에 의해 잘못된 문맥에서 자동으로 로드되지 않습니다.
CORS map과 요청/연결 zone은 nginx.conf에 항상 정의하지만, 선언만으로 거부/제한하지는 않습니다.
실제 적용은 해당 도메인의 `cors.conf`, `request-rate.conf`, `connection-limit.conf`가 담당합니다.
해당 정책을 꺼도 변수/zone을 찾지 못하는 문법 오류가 나지 않도록 선언을 보존합니다.

### 정책 파일과 OFF 의미

다음 파일은 `conf/policies/server/`에 있습니다. 두 프론트/API 블록에 같은 파일을
include하면 값은 공유되고 적용 여부는 도메인별로 선택합니다. 서로 다른 값이 필요하면
파일을 별도 이름으로 복사하고 해당 도메인의 include만 바꿉니다.

| 파일 | 기본 ON 동작 |
| --- | --- |
| `identity.conf` | Server/제품·버전 정보 헤더 숨김 |
| `directory-listing.conf` | 디렉터리 목록 비활성화 |
| `ssi.conf` | SSI 비활성화 |
| `compression.conf` | 민감 응답의 gzip 압축 비활성화 |
| `body-size.conf` | 요청 본문 5 MiB 제한 |
| `timeouts.conf` | 클라이언트 시간·헤더 제한 |
| `request-rate.conf` | IP당 10r/s·burst 20, 초과 429 |
| `connection-limit.conf` | IP당 동시 연결 20, 초과 429 |
| `generic-errors.conf` | 일반 오류 본문과 upstream 오류 가림 |
| `symlinks.conf` | Linux 링크 접근 차단, Windows OS 권한 점검 안내 |
| `nosniff.conf` | X-Content-Type-Options |
| `frame-options.conf` | X-Frame-Options SAMEORIGIN |
| `referrer-policy.conf` | strict-origin-when-cross-origin |
| `csp.conf` | CSP 출처 제한 |
| `permissions-policy.conf` | 카메라·마이크·위치 제한 |
| `hsts.conf` | HTTPS 도메인의 1년 HSTS |
| `methods-static.conf` | 프론트 GET/HEAD 허용 |
| `methods-api.conf` | API GET/HEAD/POST/OPTIONS 허용 |
| `secret-files.conf` | 숨김·설정·키·백업 파일 차단 |
| `script-files.conf` | 스크립트·실행 파일 URL 차단 |
| `uploads.conf` | 업로드 경로 직접 접근 차단 |
| `management-paths.conf` | Actuator·Swagger·H2 공개 경로 차단 |
| `sourcemaps.conf` | 소스맵 공개 차단 |
| `admin-acl.conf` | 관리자/VPN CIDR 제한 |
| `cors.conf` | 정확한 origin 검증·CORS 응답·preflight 처리 |
| `private-cache.conf` | private API no-store |
| `session-cookies.conf` | 지정 세션 쿠키 Secure/HttpOnly/SameSite |
| `proxy-headers.conf` | 전달 헤더를 검증된 연결 정보로 덮어쓰기 |
| `proxy-timeouts.conf` | backend 연결·응답 시간 제한 |
| `https-redirect.conf` | HTTP에서 고정 server_name의 HTTPS로 308 이동 |

OFF는 **그 파일의 지시문을 적용하지 않는 것**입니다. NGINX 기본값이나 상위 설정,
backend가 같은 정책을 발행하면 그 동작은 남을 수 있습니다. 예를 들어 autoindex/SSI/gzip은
NGINX 기본값도 off라서 include를 껐다고 기능이 켜지지 않습니다. 이미 브라우저가 받은
HSTS는 include를 꺼도 만료 전까지 남습니다. CSP의 frame-ancestors와 X-Frame-Options는
각각 프레임 삽입을 제한하므로 한쪽만 꺼도 다른 쪽은 계속 적용됩니다.

각 헤더 정책 파일에 backend 헤더 숨김과 edge 헤더 발행을 함께 넣었습니다.
CSP/CORS/no-store 정책을 OFF하면 **backend 원본 헤더가 다시 통과할 수 있습니다**.
애플리케이션에도 같은 설정이 있으면 함께 대조하세요. CORS OFF 시 OPTIONS도 backend에
전달하며, HTTPS 이동 OFF 시에는 샘플의 명시적인 HTTP 404가 남습니다.
관리자 ACL OFF 시 기본 API 프록시로 연결되므로 Spring Boot 인증·인가는 항상 유지합니다.
오류 가림 OFF 시 backend 원본 오류 본문이 전달됩니다.

### 실제 환경에 맞춰 바꿀 값

- `site.conf`: 프론트/API 도메인, 인증서/개인키 경로, 프론트 root와
  `upstream forge_spring`의 실제 고정 backend 주소를 바꿉니다. 기본은 127.0.0.1:9000입니다.
  server_name은 literal 도메인으로 사용하며 HTTP 이동은 첫 configured name을 사용합니다.
  샘플은 두 도메인이고, 같은 도메인의 /api/ 구조라면 기존 라우팅에 맞춰 조정합니다.
- 인증서 경로는 conf 기준입니다. 예: `conf/certs/example.test/fullchain.pem`.
  프론트 root는 prefix 기준 `sites/example.test/public`입니다.
- `nginx.conf`의 map: 실제 CORS origin을 scheme/host/port까지 정확히 지정합니다.
  사용하지 않는 example/portal origin은 지웁니다. wildcard를 허용하지 않습니다.
- `policies/server/csp.conf`: 실제 API/자산/SSO 출처만 허용합니다. nonce/hash 렌더링은
  앱/빌드와 연동하며 고정 nonce를 쓰지 않습니다.
- `policies/server/admin-acl.conf`: 실제 관리자/VPN CIDR과 관리자 경로를 지정합니다.
  기본은 loopback만 허용하고 /admin 및 /api/admin을 함께 제한합니다.
- `policies/server/session-cookies.conf`: 실제 쿠키 이름과 인증/SSO에 맞는 SameSite를 정합니다.
  XSRF-TOKEN은 JS가 읽어야 하므로 HttpOnly로 바꾸지 않습니다.
- PUT/PATCH/DELETE가 필요하면 `methods-api.conf`, `cors.conf`의 Allow-Methods와
  nginx.conf의 preflight map을 함께 맞춥니다.
- 각 제한 정책의 본문 크기, rate/연결 수, timeout은 실제 업무 트래픽에 맞춥니다.
  제한을 끄는 것과 수치를 조정하는 것은 별개입니다.

### 활성화와 기존 서버 반영

1. 서버 OS에 맞는 릴리즈의 conf 전체와 `html/__nginxforge_error.html`을 준비합니다.
   정책 파일을 빠뜨리지 않습니다. Linux AMD64/ARM64 정책은 같고 Windows 링크 파일은
   지원하지 않는 disable_symlinks 지시문 없이 OS 검토 필요성을 명시합니다.
2. 운영 값·인증서·정적 파일·backend를 준비하고 각 include의 ON/OFF를 선택합니다.
   실제 인증서·개인키·기본 비밀번호는 배포하지 않습니다.
3. `conf/conf.d/site.conf.example`을 `site.conf`로 한 번 이름을 바꿉니다.
   인증서 없는 첫 시작은 기존처럼 loopback 127.0.0.1:8080이며 사이트는 비활성 상태입니다.
4. 기존 라우팅·서비스 계정·실행 인수를 보존하고, 예전 설정이나 같은
   listen/server_name/default_server를 중복으로 남기지 않습니다.
5. 기존 서비스와 같은 prefix/계정으로 `nginx -p <prefix>/ -c conf/nginx.conf -t`를
   통과시킨 뒤 서비스의 reload 절차로 적용합니다. 로그인·API·업로드 등 업무 동작을 확인합니다.

헤더 정책의 독립적 선택과 오류 location 상속에는 `add_header_inherit merge`를 사용하므로
**NGINX 1.29.3 이상**이 필요합니다. 기존 NginxForge 1.30.6 r2/r3/r4 바이너리도 사용할 수 있습니다.
이번 변경은 NGINX C 소스·의존성·핵심 패치를 바꾸지 않으며 운영 서버에 자동 적용하지 않습니다.
TLS 정책은 핸드셰이크와 기본 리스너에 공유되어 nginx.conf의 HTTP 문맥에서 제어합니다.
하위 location에서 add_header/proxy_set_header를 다시 정의하면 중복/상속이 달라질 수 있으므로
추가 정책을 대조하고 기존 전달 헤더 전체를 유지합니다.

### 적용 범위와 검증

모든 정책 ON의 기존 보안 동작을 검사하고, **32개 정책을 하나씩 OFF한 설정과 모두 OFF한
설정의 문법 검사**, CSP/보안 헤더/CORS/캐시/쿠키/관리자 ACL/오류 가림/정보 헤더/파일 제한/
요청 빈도의 실제 OFF 동작과 다른 정책의 유지 여부를 실행 검사합니다.
이 검사는 고객사 실제 브라우저·SSO 호환성이나 Spring Boot 코드 점검 완료를 의미하지 않습니다.
끄기로 선택한 보안 통제가 여전히 충족된다고 판정하지 않습니다.

CORS/IP 제한은 앱의 인증·객체별 인가·CSRF를 대체하지 않고, CSP는 XSS 코드를 수정하지 않습니다.
요청 크기/속도 제한은 다운로드 총량·계정별 저장 용량이 아닙니다. 응답 오류 가림은
API 오류 스키마에 영향을 줄 수 있으며 앱의 200 응답이나 로그의 비밀정보를 제거하지 않습니다.
관리 포트/backend 직접 접근, 신뢰 LB의 real-IP CIDR, 원격 upstream의 TLS·CA·hostname 검증과
OS 계정·파일 권한은 별도로 적용합니다. IPv6 리스너와 방화벽도 같은 범위로 검토합니다.

[보안 담당 범위](SECURITY-OWNERSHIP.md), [프론트 코드 전용 프롬프트](prompts/FRONTEND-CODE-REVIEW.md),
[Spring Boot 코드 전용 프롬프트](prompts/SPRING-BOOT-CODE-REVIEW.md)를 함께 제공합니다.
앱/OS/인증 서버 설정과 코드로 고쳐야 하는 결함은 해당 담당 범위에 남깁니다.

## 단일 도메인 SPA + REST + WebSocket

`conf/examples/spa-api-websocket.conf.example`을 `conf/conf.d/site.conf`로 복사하면
프론트와 API를 한 HTTPS 도메인에서 제공합니다. 기존 두 도메인 샘플과 동시에 같은
listen/server_name/default_server를 중복 활성화하지 않습니다. 새 샘플도 개별 include 앞에
#을 붙여 정책을 끌 수 있습니다.

| 경로 | 동작 |
| --- | --- |
| /api/... | 127.0.0.1:9090, URI prefix/query 유지 |
| /storagewiz/... | 127.0.0.1:9080, URI prefix/query 유지 |
| /process_file/... | 127.0.0.1:9090, 일반 HTTP와 WebSocket upgrade |
| 그 외 화면 경로 | 정적 파일 우선, 없으면 /index.html SPA fallback |

운영 도메인·인증서·root·포트를 사이트 파일에서 맞추고,
`conf/maps/spa-api-websocket.conf`의 HTTPS origin과
`conf/policies/server/csp-spa.conf`의 WSS origin도 같은 도메인으로 바꿉니다.
Windows에서는 D:/... 절대 경로를 사용할 수 있습니다.
실제 인증서/개인키·운영 파일·backend는 배포 묶음에 포함하지 않습니다.

- map은 HTTP 문맥에서만 유효합니다. 사이트 파일 최상단의 `include maps/spa-api-websocket.conf;`가
  server 밖에 있으므로 주어진 Upgrade/Connection map을 따로 server 안에 복사하지 않습니다.
- `proxy_pass` 끝에 /를 넣지 않아 /api, /storagewiz, /process_file prefix와 query를 유지합니다.
  슬래시 없는 정확한 prefix는 308로 슬래시를 붙여 SPA HTML 응답으로 빠지지 않게 합니다.
- `methods-static.conf`는 정적 location과 /index.html에만 둡니다. server 전체에 넣으면
  POST/PUT/PATCH/DELETE가 차단됩니다. API는 `policies/location/methods-rest.conf`로
  GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS를 허용합니다.
- `policies/location/websocket.conf`에 Upgrade/Connection과 Host·실제 IP·전달 헤더 전체를
  명시합니다. 하위 proxy_set_header는 상위 목록을 상속하지 않으므로 WS 헤더 두 줄만
  추가하고 나머지를 상속받는다고 가정하지 않습니다.
- WebSocket idle read/send timeout은 3600초입니다. 총 연결 수명을 보장하는 값이 아니며
  backend ping, 세션 만료, 인증·인가와 재접속 처리는 앱에서 유지합니다.
- `policies/location/websocket-origin.conf`는 정확한 HTTPS origin의 upgrade만 허용합니다.
  잘못된 origin, null, Origin 없는 WebSocket은 기본 거부합니다. native 클라이언트가
  필요하면 Origin/토큰 인증 요구사항을 확인하고 map을 명시적으로 조정합니다.
  Origin 없는 일반 HTTP는 허용합니다. 이 검사는 로그인·객체별 인가를 대체하지 않습니다.
- CSP connect-src에는 self와 실제 wss://도메인을 지정합니다. 실제 JS/CSS/이미지·SSO 출처를
  확인하고 필요한 항목만 추가합니다. 같은 origin SPA/API라 NGINX CORS 응답은 추가하지 않습니다.
- `private-cache-spa.conf`는 API 경로와 일반 오류 응답에 no-store를 적용하고 정적 정상
  응답에는 Cache-Control을 추가하지 않습니다. normalized URI를 map으로 검사하므로
  인코딩된 /api prefix도 검사하며, 내부 오류 페이지로 바뀐 API 500에도 no-store가 남습니다.
  헤더 정책과 같은 server 수준에서 backend cache/CSP 등의 소유권을 유지합니다.
- proxy location에 ^~를 붙이면 정규식 보안 location을 건너뛸 수 있으므로 샘플에는 넣지 않습니다.
  비밀 파일·스크립트·관리 경로·소스맵은 SPA fallback이나 backend보다 먼저 차단합니다.
- 기존 `admin-acl.conf`는 두 도메인 샘플의 forge_spring upstream용입니다. 이 샘플에
  그대로 복사하지 않습니다. 실제 관리자 URI·VPN CIDR·목적지에 맞는 제한을 별도로 구성하고
  Spring Boot 인증/인가를 유지합니다.

기본 요청 본문 5 MiB, IP당 10r/s·burst 20, 연결 20은 이 사이트에도 적용됩니다.
파일 업로드 크기와 NAT 뒤 사용자 수/장기 WebSocket 수에 맞게 해당 정책을 조정합니다.
generic-errors는 backend 오류 본문을 HTML로 가릴 수 있으므로 업무 JSON 오류 처리를 확인합니다.

실행 검사는 SPA history fallback, 정적 메소드 제한과 REST POST/PUT/PATCH/DELETE,
서로 다른 두 backend/경로/query, 전달 헤더와 보안 헤더 상속, API/정적 캐시 구분,
보안 정규식 우선순위, 실제 101 handshake와 마스킹된 WebSocket 텍스트 프레임 왕복,
잘못된 origin 거부, 정책 OFF, index.html 부재 시 404를 확인합니다.
운영 인증서나 고객사 실제 backend/브라우저까지 검증한 의미는 아닙니다.

[NGINX WebSocket](https://nginx.org/en/docs/http/websocket.html)과
[proxy_set_header](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header)를 참고하세요.

## 운영체제별 권한과 링크

Linux 패키지는 `conf/policies/server/symlinks.conf`에 `disable_symlinks on;`을 넣고
site.conf의 include로 선택합니다. 링크를 사용하는
기존 배포 구조는 영향을 검토하세요. 운영 전용 비특권 계정을 사용하고 실제 서비스가 필요로 하는
최소 권한만 부여합니다. 예시 정책은 개인키/비밀번호 파일 600, 로그 파일 640, 로그 디렉터리
750입니다. master/worker의 읽기·쓰기 요구사항을 확인하여 소유자와 그룹을 정합니다.
root로 설치한 뒤 worker에 설정·실행 파일 쓰기 권한을 주지 않습니다. umask 027도 검토합니다.

Windows NGINX에는 `disable_symlinks` 지원이 없으므로 해당 지시문을 넣지 않습니다.
이를 플러그인으로 충족했다고 표시하지 않습니다. NTFS junction/symlink/reparse point와
바로가기를 점검하고 웹 루트에 링크 생성/파일 쓰기 권한을 제한해야 합니다.

```powershell
# 읽기 전용 확인 예시. 실제 prefix와 운영 계정에 맞게 실행합니다.
Get-Item -LiteralPath C:\nginxforge\sites\example.test\public | Select-Object FullName,Attributes,LinkType,Target
Get-ChildItem -LiteralPath C:\nginxforge\sites\example.test\public -Force -Recurse -Attributes ReparsePoint
icacls C:\nginxforge\conf
icacls C:\nginxforge\logs
icacls C:\nginxforge\conf\certs\example.test\privkey.pem
```

서비스 실행 계정의 최소 권한, Administrators/SYSTEM 권한, Everyone/Users/Authenticated Users의
불필요한 권한 및 상속 ACL을 검토합니다. 이 배포는 고객사 ACL이나 서비스 계정을 자동 변경하지 않습니다.

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
| WEB-08 | 전송 크기 | client_max_body_size 5m, 413 동작 검사 | 다운로드 크기/총량은 앱·저장소 |
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
| WEB-21 | HTTPS 이동 | 고정 canonical 도메인의 308 이동 예시 | 실제 도메인 적용·HTTPS 연결 |
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
