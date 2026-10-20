# 완료 기준과 실제 검증 상태

r6의 단일 도메인 SPA/REST/WebSocket 샘플은 검증 중입니다. 아래는 기존 r5 공개 기록입니다.

2026-10-19 검증 결과: **NGINX 1.30.6 / NginxForge r5 정식 발행 및 Latest 지정 완료**.
32개 정책 파일과 site.conf.example의 개별 include 스위치를 포함한 실제 배포 압축파일로
검증했습니다. 기본값은 모든 정책 ON이며 include 앞에 #을 붙여 프론트/API별로 OFF할 수
있습니다. HTTP 공통 TLS는 nginx.conf에서 선택합니다. 실제 운영 값을 채운 뒤 사이트
파일 하나를 활성화하며 정책 디렉터리를 함께 설치합니다.

- [x] Linux AMD64 musl 완전 정적 빌드
- [x] Linux ARM64 musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04 AMD64 실행
- [x] Ubuntu 22.04/24.04 ARM64 실행
- [x] Rocky Linux 8/9 AMD64 실행
- [x] Rocky Linux 8/9 ARM64 실행
- [x] Windows Server 2022 Runner AMD64 실행 (build 20348)
- [x] 세 바이너리 공통 보안 기능 테스트
- [x] 배포된 nginx.conf와 단일 사이트 설정으로 정적 사이트·리버스 프록시 실행
- [x] 기본 ON의 CORS/CSP·쿠키·캐시·공용 관리/소스맵 차단 정책 실행
- [x] 32개 정책 각각 OFF 및 모두 OFF 상태의 실제 바이너리 문법 검사
- [x] 대표 10개 정책의 OFF 동작과 다른 정책 유지 여부 실행 검증
- [x] 정책 파일의 명시적 include 구조와 OS별 링크 정책 렌더링 검증
- [x] 담당 범위 문서와 프론트/Spring Boot 코드 전용 프롬프트 배포
- [x] 공식 최신 버전 감지
- [x] 발행 후 재조회에서 중복 빌드·배포 생략 확인
- [x] GitHub Releases 다섯 파일 자동 발행
- [x] 전체 성공 후 Latest 지정
- [x] 공개된 다섯 파일 재다운로드 후 무결성 및 포함 설정 검증

각 OS/CPU 조합에서 75개 실행 검사, 총 **675개**가 통과했습니다. 릴리즈 제어 로직의
29개 단위 테스트도 통과했습니다. Linux 바이너리 두 개는 ELF64의 PT_INTERP 및
외부 DSO 의존성 부재를 확인했고 Windows는 AMD64 PE 및 정적 CRT/시스템 DLL 의존성을 확인했습니다.

추가된 설정 검사는 HTTPS 이동, 알 수 없는 Host/SNI 차단, 정상/오류 응답의 보안 헤더,
목록·비밀 파일·스크립트·경로 이탈 요청 차단, 허용 메소드, 5 MiB 요청 크기 제한,
고정 프록시와 전달 헤더 재작성, 세션 쿠키 플래그, 업스트림 오류 정보 가림,
업로드 경로·관리자 IP 접근 제한, TLS 1.2/1.3와 요청 빈도 제한을 확인합니다.
기본 ON 설정은 정확한 origin CORS/preflight와 거부 동작, backend 헤더 중복 제거,
정상/오류 응답의 CSP·Permissions-Policy, 지정 세션 쿠키와 JS용 CSRF 쿠키의 구분,
private API no-store, 공용 관리 경로·소스맵 차단까지 검증했습니다.
각 정책을 개별적으로 끈 설정과 모두 끈 설정은 문법 검사를 통과했습니다. CSP, nosniff,
CORS, private cache, 세션 쿠키, 관리자 ACL, 오류 가림, 정보 헤더, 비밀 파일 및 요청 빈도는
하나씩 OFF한 실제 동작과 다른 정책이 계속 적용되는지도 검사했습니다.
Linux는 실제 심볼릭 링크 접근 차단도 검사합니다. Windows의 링크 관련 검사는
지원하지 않는 NGINX 지시문을 넣지 않고 OS 권한 검토 필요성을 명시했는지 확인하는 것으로,
고객사 NTFS 링크/ACL 통제가 자동 검증됐다는 의미가 아닙니다.

| 증거 | 결과 |
| --- | --- |
| [빌드·실행·게이트·자동 발행](https://github.com/appdign/NginxForge/actions/runs/39227444668) | 첫 실행 전체 workflow success, 세 바이너리와 9개 OS/CPU 조합의 675개 실행 검사 통과 |
| [업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/39228955529) | 이미 발행한 r5의 중복 빌드·배포 생략 검증 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r5) | 다섯 자산 공개, draft=false, prerelease=false, Latest 확인 |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r5/build-manifest.json) | 공통 소스·의존성·옵션·툴체인·설정/문서 해시·전체 실행 증거 포함 |
| [보안 설정 안내](SECURITY-CONFIG.md) | 사이트별 ON/OFF 스위치, 정책 파일·OFF 의미, KISA 2026 WEB-01~26 적용 범위 |
| [담당 범위와 코드 점검](SECURITY-OWNERSHIP.md) | NGINX·프레임워크·운영 설정과 프론트/Spring Boot 코드 작업 구분 |

빌드 소스와 릴리즈 태그 commit은 `432ccd55cf691efecf45ef0f535b19d200ce12f9`입니다.
첫 실행에서 전체 빌드·실행·게이트·발행을 통과했으며 필수 플랫폼 검증이나
업로드 파일 검증을 생략하지 않았습니다.
공개된 파일 다섯 개를 다시 내려받아 GitHub 자산 SHA-256과 크기를 대조했으며,
SHA256SUMS.txt의 네 파일 해시와 각 압축파일의 설정 해시를 모두 확인했습니다.
세 패키지에 nginx.conf, mime.types, conf.d/README.md, conf.d/site.conf.example과
policies 아래 32개 파일이 정확히 포함됐는지 확인했습니다. policies는 conf.d 밖에 있어
wildcard로 자동 로드되지 않으며 site.conf의 명시적인 include만 해당 정책을 선택합니다.
symlinks.conf는 각 대상별로 원본에서 결정적으로 렌더링한 바이트와 대조했습니다.
Linux AMD64/ARM64의 전체 설정은 동일하며 Windows 링크 정책은 OS 권한 검토 사항을
명시합니다. 기본 스위치는 모두 ON이고 실제 인증서를 준비한 뒤 site.conf로 이름을 바꿉니다.
보안 안내·담당 범위·코드 전용
프롬프트 두 개와 26개 항목 대응표도 포함되어 있고,
실제 인증서·개인키·비밀번호 파일 및 테스트 fixture는 포함되지 않습니다.

KISA 공식 2026 웹 서비스 기준은 26개 항목이며 이 결과는 **26개 점검 항목의 자동 합격이나
인증을 뜻하지 않습니다**. 기존 headers-more 정적 모듈과 NGINX 기본 기능으로 제공하는
서버 조치를 문서화했습니다. 계정·비밀번호 정책, OS 파일/로그 권한, Windows 링크 통제,
인증서 운영, 앱 인증·인가·업로드 저장소·다운로드 총량 등은 실제 환경에서 별도로 점검해야 합니다.

고객사 실제 Windows Server 2022 설치 환경과 별도 Linux 호스트 커널, 운영 서비스,
부하 검증은 GitHub Runner/컨테이너 실행과 구분합니다.
정책은 HTTP 응답/실행 동작을 검증한 것으로, 고객사 프론트의 실제 브라우저 동작,
SSO/CSP 호환성 또는 별도 Spring Boot 소스의 보안 점검 완료를 의미하지 않습니다.
OFF는 해당 지시문을 제거하므로 NGINX 기본값/상위 설정이나 backend 정책이 남을 수 있고,
이전에 받은 HSTS는 브라우저에 남습니다. OFF한 통제를 적용 완료로 판정하지 않습니다.

ARM64를 포함한 모든 필수 빌드·실행·릴리즈 검증을 통과했습니다. 이후 버전도 동일한
전체 검증을 통과해야만 발행합니다. 필수 플랫폼 검증을 생략하거나 실패를 무시하지 않습니다.

## 이전 릴리즈 기록

r4는 [전체 657개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39199206198)을
첫 실행에서 통과했습니다. [r4 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r4)는
nginx.conf와 단일 사이트 파일에 정책을 직접 작성한 공개 기록으로 보존합니다.
r5는 정책별 include 스위치를 제공하며 r4와 NGINX 소스·의존성·핵심 패치·빌드 옵션은 같습니다.

r3는 [전체 648개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39195702671)을
통과했습니다. 최초 실행의 draft 생성 직후 재조회 실패는 같은 commit의 발행 job만
재시도하여 원본 산출물을 다시 검증한 뒤 완료했습니다.
[r3 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r3)는 옵션별 정책 샘플과
코드 전용 점검 프롬프트를 포함한 공개 기록으로 보존합니다. r4는 이를 통합 설정으로
재구성했으며 NGINX C 소스·의존성·핵심 패치를 바꾸지 않았습니다.

r2는 [전체 576개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/38685349446)을
통과했습니다. [r2 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r2)는
KISA 대응표와 공통 보안/도메인 샘플을 처음 포함한 공개 기록으로 보존합니다.

r1은 [최초 빌드와 360개 실행 검사](https://github.com/appdign/NginxForge/actions/runs/38661867375)를
통과했습니다. 최초 발행 API 단계의 draft 조회 실패는 main에서 수정한 뒤
[원본 산출물 재검증·발행](https://github.com/appdign/NginxForge/actions/runs/38682918382)으로
완료했습니다. [r1 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r1)와
그 바이너리·태그는 변경하지 않았습니다.
