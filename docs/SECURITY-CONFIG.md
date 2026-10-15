# KISA 2026 보안 설정과 도메인 샘플

기준은 KISA의 2025-12-24 공개 「2026 주요정보통신기반시설 기술적 취약점 분석·평가 방법
상세가이드」 웹 서비스 편입니다. 공식 표 p.272~273은 **WEB-01~WEB-26 총 26개**입니다.
[공식 게시물](https://www.kisa.kr/2060204/form?postSeq=22&page=1)과
[공식 PDF](https://www.kisa.kr/post/fileDownload?menuSeq=2060204&postSeq=22&attachSeq=1&lang_type=KO)를 참고하세요.
원본 PDF SHA-256: `44fe393981b244147be6af7423d99dc15633c089fad0bcb296cbe2371dde812d`.
이 배포는 KISA 인증 또는 고객사 점검 통과를 의미하지 않습니다. 적용 환경의 실제 설정,
계정·파일 권한·인증서·업스트림 애플리케이션을 함께 점검해야 합니다.

## 적용 방법

새 설치의 `conf/nginx.conf`는 127.0.0.1:8080 확인용이며 인터넷 공개용 HTTPS 설정은
활성화하지 않습니다. 인증서/개인키/기본 관리자 계정/비밀번호는 배포하지 않습니다.
기존 설치는 새 파일을 staging에 풀어 비교하고 필요한 옵션만 병합합니다.

1. `conf/examples/00-default-deny.conf.example`을 검토해 `conf/conf.d/00-default-deny.conf`로 복사합니다.
2. 정적 사이트는 `example.test.static.conf.example`, 애플리케이션 프록시는
   `app.example.test.proxy.conf.example`을 선택하여 `conf/conf.d/<도메인>.conf`로 복사합니다.
3. 예시 도메인을 실제 도메인으로 모두 바꾸고 인증서 체인과 개인키를 준비합니다.
   `ssl_certificate` 경로는 **설정 파일 디렉터리 conf 기준**입니다.
   예시: `conf/certs/example.test/fullchain.pem`, `conf/certs/example.test/privkey.pem`.
4. 정적 파일은 prefix 기준 `sites/example.test/public`에 둡니다. 설정·로그·임시 파일·
   업로드 저장소·개인키를 이 웹 루트 안에 두지 않습니다. 업로드는 애플리케이션이 별도
   디렉터리에 저장하고 권한·확장자·내용·총 용량을 검증해야 합니다.
5. 프록시는 고정된 loopback backend `127.0.0.1:9000`을 실제 서비스에 맞게 검토합니다.
   원격 backend는 TLS와 `proxy_ssl_verify on`, 신뢰 CA 및 hostname 검증을 설정합니다.
6. 실제 실행 인수와 계정으로 `nginx -p <prefix>/ -c conf/nginx.conf -t`를 통과시킨 뒤
   재시작/재로드하고 HTTP→HTTPS, 정상/오류 응답, 인증과 업로드를 확인합니다.

예시 도메인 파일은 `.example`로 끝나 자동 로드되지 않습니다. 검토 후 `.conf`로
명시적으로 활성화합니다. 기본 deny 가상 호스트는 한 번만 설치합니다. IPv6가 필요한 환경은
`[::]:80`, `[::]:443 ssl` 바인딩과 방화벽/deny 정책을 동일하게 추가·검증해야 합니다.

## 포함된 통제와 조정이 필요한 값

- `http-policy.conf`: Server/X-Powered-By 등 제거, 디렉터리 목록/SSI 끄기,
  5 MiB 요청 본문 제한, 헤더/본문/응답 타임아웃과 연결 수·요청 빈도 정책.
- `server-guards.conf`: 숨김·설정·키·백업 파일 및 CGI/스크립트 확장자 차단,
  직접 업로드 경로 차단, 내부 공통 오류 페이지. 파일 제거·실행 권한 통제도 별도로 필요합니다.
- 정적 도메인은 GET/HEAD만, 프록시 예시는 GET/HEAD/POST/OPTIONS만 허용합니다.
  PUT/PATCH/DELETE가 필요한 API는 필요한 경로에 한해 검토 후 허용합니다.
- `tls.conf`: TLS 1.2/1.3, TLS 1.2 AEAD cipher, 세션 티켓 비활성화.
  운영 인증서 신뢰·SAN·만료·갱신과 원격 backend TLS는 운영자가 검증해야 합니다.
- HTTPS 도메인 예시의 HSTS는 1년이며 `includeSubDomains`/`preload`를 강제하지 않습니다.
  유효한 HTTPS를 계속 유지할 도메인에만 활성화합니다.
- 보안 응답 헤더는 `always`로 오류 응답에도 적용합니다. 자식 location에서 `add_header`를
  쓰면 상위 헤더가 상속되지 않을 수 있으므로 `response-headers.conf`를 같은 level에 다시 포함합니다.
  `more_set_headers`/`more_clear_headers`도 자식에 새로 정의하면 상위 모듈 설정의 상속을
  검토해야 합니다. `server_tokens off`만으로 Server 헤더가 완전히 제거되지는 않습니다.
- CSP와 세션 쿠키 플래그는 `optional-policies.conf.example`의 선택 설정입니다.
  앱의 스크립트·SSO·iframe·CSRF 동작을 확인한 후 적용합니다. 모든 쿠키에 일괄 HttpOnly를
  적용하지 않습니다. CORS 전체 허용은 포함하지 않습니다.
- 프록시 예시는 외부의 X-Forwarded-For/Forwarded 값을 신뢰하지 않고 덮어씁니다.
  실제 로드밸런서 뒤에서는 정확한 trusted CIDR만 real-IP 설정에 등록합니다.
- 프록시의 오류 가림은 앱/API 오류 스키마에 영향을 줄 수 있습니다. 기존 상태 코드와 인증
  헤더를 유지할지 검토합니다. 애플리케이션이 200 응답 본문에 내보낸 비밀까지 제거하지는 않습니다.
- 다운로드 **전송 속도**인 `limit_rate`를 다운로드 **파일 크기/총량 제한**으로 간주하지 않습니다.
  파일 크기·일일 총량·권한·동시성은 앱/저장소 정책으로 확인합니다.
- 기본 gzip은 비활성화입니다. 비밀이 포함되지 않는 공개 정적 리소스에 한해 성능 정책에 맞게
  재활성화할 수 있습니다. rate/connection 제한은 실제 트래픽과 NAT 사용자 수에 맞게 조정합니다.

## 운영체제별 권한과 링크

Linux 패키지는 `conf/platform.conf`에 `disable_symlinks on;`을 넣습니다. 링크를 사용하는
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
