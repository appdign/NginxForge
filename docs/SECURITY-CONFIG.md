# 운영 설정: site.conf 한 파일에서 관리

평소 수정하는 파일은 **conf/site.conf 하나**입니다. 가상호스트가 여러 개여도 같은
파일에 사이트 구역을 추가합니다. API/WS/backend나 외부 허용 범위 때문에 다른 파일을
찾아 수정하지 않습니다.

| 파일 | 역할 |
| --- | --- |
| conf/nginx.conf | worker·로그·MIME·공통 TLS·site.conf include. 도메인/backend 없음 |
| conf/policy.conf | 고정 보안 헤더·정보 노출 방지·위험 파일/관리 경로 차단. 도메인/backend 없음 |
| conf/site.conf | 모든 실제 도메인·인증서·root·CSP·외부 허용 목록·API·WS·backend·제한 값 |
| conf/mime.types | 공통 MIME 데이터. js/mjs는 JavaScript, css는 text/css |

운영 conf에는 위 네 파일만 있습니다. 예제·이전 정책별 파일·backend YAML·코드 점검
프롬프트는 운영 패키지와 분리하여 저장소/별도 참고 ZIP으로 제공합니다.
공개 바이너리의 초기 site.conf는 고객사 값/인증서를 담지 않고 모든 요청을 거부합니다.
실제 적용본의 site.conf를 설치해야 서비스를 제공합니다. 데모 사이트/8080 미리보기는 없습니다.

## site.conf에서 수정할 위치

1. **외부 웹사이트 허용 목록**: 파일 상단 site_external_origin map. 키는 대상 server_name과
   허용할 Origin의 쌍입니다. 목록이 비어 있어도 현재 접속 사이트는 자동 허용됩니다.
2. **사이트 구역**: BEGIN SITE~END SITE 사이의 server_name·인증서·root를 맞춥니다.
   가상호스트를 추가할 때 이 구역만 복사하며 공통 map/zone/기본 listener는 복사하지 않습니다.
3. **사이트별 선택**: site_cors_mode, site_ws_mode, site_allow_originless_ws,
   site_cors_credentials, site_csp를 조정합니다.
4. **업무 동작**: location /api/, /storagewiz/, /process_file/의 고정 proxy_pass,
   허용 메소드, timeout, client_max_body_size, 쿠키와 오류 가림을 조정합니다.
5. **자동 계산 구역**: 파일 맨 아래의 map들은 현재 접속 호스트/포트와 위 선택값을 계산합니다.
   보통 수정하지 않습니다. API prefix를 변경할 때는 site_api_path 분류도 함께 맞춥니다.

파일 하나 안의 주석을 따라 수정합니다. 실제 적용본에는 토큰/미사용 가상호스트나 예제를
섞지 않습니다. 소스의 [site template](https://github.com/appdign/NginxForge/blob/main/config/site-template.conf)은
별도 참고/생성용이며 @@...@@ 토큰을 치환하지 않은 채 운영 설정으로 설치하지 않습니다.

## API와 WebSocket의 기본값

기본은 동일 출처(프로토콜·호스트·포트가 같은 경우)입니다. 현재 접속한 허용 vhost의
호스트/포트를 자동 반영하므로 policy.conf에 도메인을 적지 않습니다. 80/443의 명시적
기본 포트와 생략 표기는 정규화하고 비표준 포트는 구분합니다. 알 수 없는 Host/SNI는 거부합니다.

- **우리 화면 -> 외부 API/WSS/CDN**: 각 사이트의 site_csp에서 해당 src에 추가합니다.
  connect-src의 현재 WSS 호스트/포트는 자동 생성됩니다. CSP를 두 헤더로 나누지 않습니다.
- **외부 웹사이트 -> 우리 API/WS**: 상단 site_external_origin에 대상 vhost별로 등록합니다.
  exact Origin 또는 protocol/host/port 전체를 고정한 하위 도메인 패턴을 사용합니다.
  API CORS와 WebSocket Origin 검사는 이 목록을 공유하지만 공개 모드는 따로 선택합니다.
- **API 공개**: 해당 사이트의 site_cors_mode를 public으로 설정하면 모든 HTTP(S) Origin에
  Access-Control-Allow-Origin: *를 응답합니다. 이 모드에서는 credentials 헤더를 내보내지 않습니다.
- **WS 공개**: site_ws_mode를 public으로 선택합니다. API 공개가 WS 공개를 자동으로 켜지 않으며
  WS 공개도 API 공개를 켜지 않습니다. Origin 없는 native WS는 별도로 1을 선택해야 합니다.
- **쿠키/세션 CORS**: restricted 목록에 일치한 실제 Origin만 응답합니다. *와
  Access-Control-Allow-Credentials: true를 같이 보내지 않습니다. null Origin은 기본 거부합니다.

와일드카드 등록 시 다른 vhost의 허용 목록에 번지지 않도록 대상 server_name을 함께
매칭합니다. 상위 도메인, 악성 suffix, 다른 scheme/port를 자동 허용하지 않습니다.
Origin을 무조건 응답에 복사하지 않습니다. CORS/CSP/Origin은 사용자 인증·객체별 인가·
CSRF를 대신하지 않으며 비브라우저의 직접 호출은 Spring Boot 인증으로 통제합니다.
Origin 없는 일반 HTTP API는 허용하며 backend 인증을 유지합니다.

## CSS와 JavaScript

site_csp는 인라인 CSS를 허용하며 인라인 script/onclick/eval을 차단합니다. 스타일 주입
제한을 완화하는 호환 선택입니다. 더 엄격한 스타일 정책은 앱의 nonce/hash 연동이 필요하며
정적 nonce는 사용하지 않습니다. 같은 사이트의 js/mjs 모듈은 정상 MIME으로 응답합니다.
MIME 오류가 text/html이면 파일 누락/잘못된 URL로 SPA fallback이 응답한 것인지 확인합니다.
외부 CDN은 해당 사이트의 CSP src에 필요한 출처만 추가합니다.

## 사이트별 요청/연결/업로드 설정

site.conf에서 client_max_body_size를 선택합니다. 파일 서버 기본은 **요청 전체 1 GiB**이며
파일·폼·multipart 형식을 모두 포함합니다. API 요청 5 MiB가 필요한 사이트는 5m로 선택합니다.
업로드 경로를 모르는 edoc 적용본은 사이트 전체 1 GiB이므로 JSON에도 같은 상한입니다.
다운로드 파일 크기 제한은 아닙니다.

파일당 50 MiB와 일반 폼 파라미터 5 MiB는 실제 Spring MVC/Servlet + Tomcat에 별도로
적용합니다. [backend YAML 참고](https://github.com/appdign/NginxForge/blob/main/docs/backend/application-upload.yml.example)는
운영 conf에 섞지 않습니다. NGINX가 자동 적용하지 않으며 여기의 native 검증은 실제
Spring 앱의 파일/폼 제한을 검증한 것이 아닙니다. Tomcat 폼 제한은 JSON/WS 메시지나
분할 업로드의 논리적 파일 합계를 제한하지 않습니다.

IP 빈도는 기본 10r/s·burst 20이고 일일 횟수 제한이 아닙니다. bucket은 vhost별로 분리합니다.
동시 연결 기본 20, WS idle 3600초 등은 사이트별로 조정합니다. NAT/장기 WS와 임시 파일
공간을 고려합니다. API 오류 JSON을 유지하려면 해당 사이트 proxy_intercept_errors를 off로
선택합니다. 로그/오류의 비밀정보 제거와 backend 인증은 계속 앱에서 담당합니다.

## 설치와 변경

기존 설정을 백업한 뒤 새 구조의 conf 네 파일과 html/__nginxforge_error.html을 함께 설치합니다.
r8의 conf.d/*.conf/policies include 구조와 병행 활성화하지 않습니다. 기존 실행 파일
NginxForge 1.30.6을 사용할 수 있으며 운영 서버에 자동 적용하지 않습니다.
같은 prefix/계정/-c 인수로 nginx -t 통과 후 기존 서비스 절차로 reload합니다.
Windows 일반 예는 ./nginx.exe -t 후 성공 시 ./nginx.exe -s reload입니다.

실제 인증서/키/프론트/backend는 운영 리소스이며 묶음에 포함하지 않습니다. 가상호스트를
추가한 뒤 로그인·SSO·API·업로드·WebSocket과 오류 응답을 실제 환경에서 확인합니다.
Linux는 native disable_symlinks를 적용하고 Windows는 NTFS ACL/재분석 지점 통제가 별도입니다.

검증은 실제 바이너리로 두 vhost의 root/backend/CSP/외부 목록/공개 모드/용량 제한 격리,
정확한 CORS preflight/Origin 경계, TLS, CSS/mjs, URI prefix/query, 전달 헤더, 쿠키,
오류/캐시, WebSocket handshake와 frame을 확인합니다. 사이트별 선택을 바꾸어도 공통
policy.conf의 바이트가 유지되는지 확인합니다. 전체 9개 필수 OS/CPU가 성공해야 발행합니다.

근거: [NGINX core](https://nginx.org/en/docs/http/ngx_http_core_module.html),
[proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS),
[CSP connect-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src).

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
