# KISA 2026 보안 설정과 도메인 샘플

기준은 KISA의 2025-12-24 공개 「2026 주요정보통신기반시설 기술적 취약점 분석·평가 방법
상세가이드」 웹 서비스 편입니다. 공식 표 p.272~273은 **WEB-01~WEB-26 총 26개**입니다.
[공식 게시물](https://www.kisa.kr/2060204/form?postSeq=22&page=1)과
[공식 PDF](https://www.kisa.kr/post/fileDownload?menuSeq=2060204&postSeq=22&attachSeq=1&lang_type=KO)를 참고하세요.
원본 PDF SHA-256: `44fe393981b244147be6af7423d99dc15633c089fad0bcb296cbe2371dde812d`.
이 배포는 KISA 인증 또는 고객사 점검 통과를 의미하지 않습니다. 적용 환경의 실제 설정,
계정·파일 권한·인증서·업스트림 애플리케이션을 함께 점검해야 합니다.

## 통합 파일 두 개로 적용

보안 옵션을 파일별로 고르는 구조를 없앴습니다. 옵션별 snippets/examples/platform.conf는
배포하지 않습니다. 다음 **두 설정 파일** 안에 보안 정책이 실제 지시문으로 모두 들어 있습니다.

| 파일 | 내용 |
| --- | --- |
| `conf/nginx.conf` | 공통 HTTP/TLS, 보안 헤더·CSP, CORS map, 요청 제한, 쿠키, 프록시·OS 정책 |
| `conf/conf.d/site.conf.example` → `site.conf` | 기본 Host/SNI 거부, 프론트와 Spring Boot 도메인, HTTPS 이동/HSTS, CORS 응답/preflight, private API no-store, 관리자 CIDR와 노출 경로 차단 |

`mime.types`는 표준 MIME 데이터이며 `html/__nginxforge_error.html`은 공통 오류 본문입니다.
이 리소스들은 패키지에 포함됩니다. 옵션 조각을 조립하거나 보안 include 주석을 하나씩 해제하지 않습니다.
인증서가 없는 새 설치도 실행할 수 있도록 **전체 사이트 한 파일**만 `.example` 상태로 제공하고,
첫 시작은 기존과 같이 `127.0.0.1:8080`입니다. 사이트를 활성화하면 모든 사이트 보안 정책이 함께 적용됩니다.

### 실제 환경에 맞춰 바꿀 값

파일의 `DEPLOYMENT VALUE(S)` 주석은 운영 값의 위치를 표시합니다. 보안 정책을 꺼 두는 주석이 아닙니다.

- 프론트 `example.test`, API `app.example.test`를 실제 도메인으로 바꿉니다.
  샘플은 두 도메인을 한 `site.conf`에 함께 정의합니다. 동일 도메인의 `/api/` 구조라면
  기존 경로 라우팅에 맞게 server/location 구성을 맞추고 회귀 확인합니다.
- 인증서/개인키 경로는 **conf 디렉터리 기준**입니다.
  예: `conf/certs/example.test/fullchain.pem`, `conf/certs/example.test/privkey.pem`.
- 프론트 root는 prefix 기준 `sites/example.test/public`, Spring Boot backend는
  `127.0.0.1:9000`입니다. 실제 경로와 로컬 포트로 바꿉니다.
- CORS 허용 origin은 `nginx.conf`의 **한 map 목록**에서 scheme/host/port를 정확히 바꿉니다.
  샘플의 프론트/API/portal origin 중 실제 사용하지 않는 주소는 지웁니다. wildcard는 없습니다.
- CSP는 실제 API origin 및 JS/CSS/이미지/SSO 출처를 필요한 지시문에만 반영합니다.
  기본값은 self와 명시한 API의 connect-src만 허용합니다. nonce/hash가 필요한 렌더링은
  앱/빌드와 연동하고 고정 nonce를 사용하지 않습니다.
- 관리자/VPN CIDR은 `site.conf`의 allow 목록에 넣습니다. 기본은 loopback만 허용하며
  `/admin`과 `/api/admin` 경로를 함께 제한합니다. 실제 관리자 URL도 확인합니다.
- 세션 쿠키 이름 JSESSIONID/SESSION과 SameSite=lax를 실제 인증/SSO에 맞춥니다.
  cross-site 쿠키가 필요한 경우 None+Secure와 앱 CSRF 정책을 함께 검토합니다.
- API 기본 허용 메소드는 GET/HEAD/POST/OPTIONS입니다. 실제 REST API에 PUT/PATCH/DELETE가
  필요하면 CORS map, Allow-Methods와 API 메소드 조건을 함께 맞춥니다.
- 요청 본문 5 MiB, IP당 10r/s·burst 20, 연결 20, 각 timeout은 실제 업무 트래픽에 맞춥니다.

### 활성화와 기존 서버 반영

1. 서버 OS에 맞는 릴리즈 패키지의 `nginx.conf`를 사용합니다. Linux는 AMD64/ARM64 모두
   같은 통합 설정이며 링크 제한이 inline입니다. Windows 파일에는 지원하지 않는 링크 지시문이 없습니다.
2. 위 운영 값과 인증서·정적 파일·backend를 준비합니다. 설정·키·업로드 저장소를 웹 루트와 분리합니다.
3. `conf/conf.d/site.conf.example`을 **한 번만** `site.conf`로 이름을 바꿉니다.
   실제 인증서·개인키·기본 계정·비밀번호는 배포하지 않습니다.
4. 기존 서버의 사용자 정의 라우팅·계정·실행 인수는 보존하여 통합본에 대조합니다.
   예전 snippets/include나 같은 listen/server_name/default_server를 중복으로 남기지 않습니다.
5. 기존 서비스와 같은 prefix/계정으로 `nginx -p <prefix>/ -c conf/nginx.conf -t`를 통과시킨 후
   해당 서비스의 reload 절차로 적용하고 로그인·업무 API·파일 전송을 확인합니다.

통합본은 `add_header_inherit merge`를 사용하므로 **NGINX 1.29.3 이상**이 필요합니다.
NginxForge r2/r3의 NGINX 1.30.6에서도 사용할 수 있습니다. 이번 변경 때문에 본체 교체가
필수인 것은 아닙니다. 기존 설정·인증서·서비스를 자동으로 변경하거나 운영 서버에 접속하지 않습니다.
IPv6가 필요하면 도메인/default listener와 방화벽·deny 정책에 같은 범위로 추가합니다.

## 이미 반영된 정책과 담당 범위

- 정보 헤더 제거, 목록/SSI/gzip 비활성화, 본문·시간·빈도·연결 제한과 TLS 1.2/1.3 정책은 공통 설정입니다.
- 보안 헤더·CSP·Permissions-Policy는 공통으로 발행합니다. domain의 HSTS/CORS/no-store와
  함께 상속되도록 merge하며 upstream의 상충 헤더를 제거합니다. 같은 이름을 사용자 location에서
  다시 add_header로 넣으면 merge로 중복될 수 있으므로 값의 소유자를 한 곳에 둡니다.
- HSTS는 HTTPS 도메인에 1년이며 includeSubDomains/preload는 강제하지 않습니다.
  카메라·마이크·위치는 기본적으로 제한되므로 필요한 업무 기능은 허용 출처를 조정합니다.
- API는 정확한 허용 origin에만 credentialed CORS를 발행하고 알 수 없는 nonempty Origin은
  403으로 차단합니다. Origin 없는 native 요청에는 CORS 권한을 주지 않습니다.
  preflight는 고정 허용 메소드/헤더 목록으로 204를 내며 임의 요청 헤더를 반사하지 않습니다.
  CORS는 로그인·인가·CSRF 검증을 대체하지 않습니다. Spring의 중복 CORS 설정도 대조합니다.
- private API는 성공/오류 응답에 no-store를 적용합니다. 공개 프론트 정적 파일의 캐시와는
  분리합니다. 앱 메모리·service worker가 직접 저장한 데이터를 삭제하는 기능은 아닙니다.
- 지정 세션 쿠키에만 Secure/HttpOnly/SameSite를 적용합니다. JS가 읽는 XSRF-TOKEN은
  HttpOnly로 바꾸지 않습니다. 쿠키 발급·세션 만료·폐기·JWT 검증은 앱/IdP 책임입니다.
- 숨김·설정·키·백업·스크립트·업로드 직접 경로, 기본 Actuator/Swagger/H2 및 소스맵 요청은
  도메인 설정에서 차단합니다. 사용자 정의 관리 경로와 backend 직접/관리 포트의 접근은 별도로 확인합니다.
- 전달 헤더를 외부 입력 그대로 신뢰하지 않고 덮어씁니다. 신뢰 LB 뒤에서는 정확한 CIDR만
  real-IP 설정에 등록합니다. 원격 backend가 필요하면 TLS·CA·hostname 검증을 별도로 설정합니다.
  하위 location에 proxy_set_header를 추가하면 상위 전달 헤더가 상속되지 않을 수 있으므로
  기존의 전체 전달 헤더 정책을 유지하고 spoofing 검사를 다시 수행합니다.
- 오류 정보 가림은 API 오류 스키마에 영향을 줄 수 있습니다. 앱의 200 응답이나 로그에 이미
  섞인 비밀정보를 안전하게 제거하지 않습니다. download limit_rate는 속도이며 파일 크기/총량 제한이 아닙니다.

실행 검사는 **배포된 두 파일을 그대로** 사용합니다. 조각을 추가하거나 정책 주석을 해제하지 않고,
테스트용 포트·backend·CIDR 및 인증서 fixture만 대입하여 전체 설정을 검증합니다.
고객사 브라우저·SSO 호환성이나 별도 애플리케이션 코드까지 점검 완료한 의미는 아닙니다.

[보안 담당 범위](SECURITY-OWNERSHIP.md), [프론트 코드 전용 프롬프트](prompts/FRONTEND-CODE-REVIEW.md),
[Spring Boot 코드 전용 프롬프트](prompts/SPRING-BOOT-CODE-REVIEW.md)를 함께 제공합니다.
세션 TTL·표준 JWT·PasswordEncoder·Actuator 노출·OS ACL 등 설정 항목은 코드 점검에서 분리하고,
객체별 인가·XSS 출력·파일 내용/경로·업무 할당량·일회성 토큰 소비 등 실제 코드 작업만 남깁니다.

## 운영체제별 권한과 링크

Linux 패키지는 `conf/nginx.conf` 안에 `disable_symlinks on;`을 직접 넣습니다. 링크를 사용하는
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
