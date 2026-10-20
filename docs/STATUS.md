# 완료 기준과 실제 검증 상태

2026-10-20 검증 결과: **NGINX 1.30.6 / NginxForge r6 정식 발행 및 Latest 지정 완료**.
기존 두 도메인 샘플과 단일 도메인 SPA/REST/WebSocket 샘플을 실제 배포 압축파일로
검증했습니다. 37개 정책 파일을 제공하고 선택한 사이트의 include 앞에 #을 붙여
ON/OFF할 수 있습니다. HTTP 공통 TLS는 nginx.conf, 단일 도메인 map은 server 밖에서
관리합니다. 실제 운영 값을 채운 뒤 사이트 하나를 활성화하고 정책 디렉터리를 함께 설치합니다.

- [x] Linux AMD64 musl 완전 정적 빌드
- [x] Linux ARM64 musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04 AMD64 실행
- [x] Ubuntu 22.04/24.04 ARM64 실행
- [x] Rocky Linux 8/9 AMD64 실행
- [x] Rocky Linux 8/9 ARM64 실행
- [x] Windows Server 2022 Runner AMD64 실행 (build 20348)
- [x] 세 바이너리 공통 보안 기능 테스트
- [x] 기본 사이트의 CORS/CSP·쿠키·캐시·관리/소스맵 차단 정책 실행
- [x] 기본 32개 정책 각각 OFF 및 모두 OFF 상태 문법 검사
- [x] 대표 10개 정책 OFF 동작과 다른 정책 유지 여부 실행 검증
- [x] 단일 도메인 샘플의 각 선택 정책 OFF 및 모두 OFF 문법 검사
- [x] SPA fallback·정적 메소드 제한·REST POST/PUT/PATCH/DELETE·두 목적지 실행
- [x] URI prefix/query·전체 전달 헤더·API/정적 캐시·보안 정규식 우선순위 실행
- [x] 실제 WebSocket 101 handshake와 마스킹된 텍스트 프레임 왕복
- [x] WebSocket origin 거부와 OFF 동작, index.html 부재 시 404 실행
- [x] 정책 파일의 명시적 include와 OS별 링크 정책 렌더링 검증
- [x] 담당 범위 문서와 프론트/Spring Boot 코드 전용 프롬프트 배포
- [x] 공식 최신 버전 감지와 발행 후 중복 빌드·배포 생략
- [x] GitHub Releases 다섯 파일 자동 발행 및 전체 성공 후 Latest 지정
- [x] 공개된 다섯 파일 재다운로드 후 무결성 및 전체 포함 설정 검증

각 OS/CPU 조합에서 87개 실행 검사, 총 **783개**가 통과했습니다. 릴리즈 제어 로직의
29개 단위 테스트도 통과했습니다. Linux 바이너리는 ELF64의 PT_INTERP 및 외부 DSO
의존성 부재, Windows는 AMD64 PE 및 정적 CRT/시스템 DLL 의존성을 확인했습니다.

기존 40개 엔진 검사와 35개 기본 패키지 보안 검사를 유지하고, 단일 도메인 샘플의
12개 검사를 추가했습니다. 기본 샘플의 HTTPS 이동, Host/SNI 거부, 정상/오류 보안 헤더,
목록·비밀 파일·스크립트·경로 이탈·메소드·본문 크기·빈도 제한, 프록시·세션 쿠키·
관리자 CIDR·TLS·CORS·CSP·private API 캐시·관리 경로·소스맵을 검사합니다.
정책별 OFF와 다른 정책 유지 여부도 실제 요청으로 검사합니다.

단일 도메인 샘플은 정적 GET/HEAD 제한을 정적 location에 두고 REST 메소드를 차단하지
않는지 확인합니다. 서로 다른 두 backend와 URI prefix/query를 유지하고 WebSocket
location에서 전체 전달 헤더를 재작성하는지 검사합니다. 실제 TLS 연결의 HTTP/1.1
101 handshake 뒤 마스킹된 client text frame을 backend까지 보내 응답 frame을 받았습니다.
잘못된/누락된 WebSocket Origin은 거부하며 WebSocket OFF는 upgrade하지 않습니다.
API/인코딩된 prefix/내부 오류 응답의 no-store와 정적 성공 응답의 구분,
backend 보안 헤더 중복 제거 및 보안 정규식의 SPA/backend 우선순위도 확인했습니다.

Linux는 실제 symlink 접근 차단을 검사합니다. Windows 링크 검사는 OS 권한 검토가
필요하다고 명시했는지 확인하는 것으로 고객사 NTFS 링크/ACL을 검증했다는 뜻이 아닙니다.

| 증거 | 결과 |
| --- | --- |
| [빌드·실행·게이트·자동 발행](https://github.com/appdign/NginxForge/actions/runs/39370470807) | 첫 실행 전체 workflow success, 세 바이너리와 9개 OS/CPU 조합의 783개 실행 검사 통과 |
| [업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/39371559316) | 이미 발행한 r6의 중복 빌드·배포 생략 검증 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r6) | 다섯 자산 공개, draft=false, prerelease=false, Latest 확인 |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r6/build-manifest.json) | 공통 소스·의존성·옵션·툴체인·설정/문서 해시·전체 실행 증거 포함 |
| [보안 설정 안내](SECURITY-CONFIG.md) | 사이트별 ON/OFF, 단일 도메인 SPA/REST/WS 적용 및 KISA WEB-01~26 범위 |
| [담당 범위와 코드 점검](SECURITY-OWNERSHIP.md) | NGINX·프레임워크·운영 설정과 프론트/Spring Boot 코드 작업 구분 |

빌드 소스와 릴리즈 태그 commit은 `a90ad174534b4efe0786a7e80e723b124fad6aca`입니다.
첫 실행에서 전체 빌드·실행·게이트·발행을 통과했습니다. 필수 플랫폼이나 업로드 검증을
생략하지 않았습니다. 공개된 다섯 파일의 GitHub 자산 SHA-256/크기, SHA256SUMS.txt의
네 파일 해시와 압축파일 안의 모든 설정·문서 해시를 다시 확인했습니다.

세 패키지의 conf에는 기본 네 파일, examples/spa-api-websocket.conf.example,
maps/spa-api-websocket.conf와 정책 37개가 정확히 포함되어 있습니다. 정책은 conf.d 밖에
두어 wildcard로 자동 로드하지 않습니다. symlinks.conf는 원본에서 OS별로 결정적으로
렌더링한 바이트와 대조했고 Linux 두 아키텍처의 전체 설정은 같습니다.
보안 안내·담당 범위·코드 전용 프롬프트 두 개와 26개 항목 대응표도 포함되어 있으며,
실제 인증서·개인키·비밀번호 파일 및 테스트 fixture는 배포 압축파일에 포함되지 않습니다.

r5와 NGINX 소스·의존성·핵심 패치·빌드 옵션은 같습니다. 기존 NginxForge 1.30.6에서도
새 설정을 실행할 수 있습니다. 인증서/root/Origin/CSP/backend와 실제 업무 설정을 맞추고
같은 서비스 prefix/계정으로 nginx -t 통과 후 reload해야 합니다.
요청 본문 기본 5 MiB, 장기 WebSocket의 연결 수/idle timeout, CSP와 API 오류 형식은
실제 업무에 맞게 검토합니다. 고객사 Windows 경로 적용본은 별도 구성으로, fixture
인증서/root를 사용한 문법 확인과 실제 운영 인증서/backend 검증을 구분합니다.

KISA 공식 2026 웹 서비스 기준은 26개 항목이며 이 결과는 **점검 항목의 자동 합격이나
인증을 뜻하지 않습니다**. OS 계정·파일/로그 권한·Windows 링크 통제·인증서 운영과
앱 인증·인가·CSRF·업로드 저장소·다운로드 총량은 실제 환경에서 별도 점검해야 합니다.
고객사 실제 브라우저·SSO·Spring Boot 소스·서비스 통합·커널·부하 검증은 여기의
GitHub Runner/네이티브 userspace 및 fixture backend 검증과 구분합니다.

OFF는 해당 지시문을 제거하므로 NGINX 기본값/상위 설정/backend 정책과 이전에 받은
HSTS가 남을 수 있습니다. OFF한 통제를 적용 완료로 판정하지 않습니다.
ARM64를 포함한 모든 필수 빌드·실행·릴리즈 검증을 통과했으며 이후 버전도 같은
전체 검증을 통과해야만 발행합니다.

## 이전 릴리즈 기록

r5는 [전체 675개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39227444668)을
첫 실행에서 통과했습니다. [r5 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r5)는
32개 정책 파일과 site.conf의 ON/OFF 스위치를 처음 포함한 공개 기록으로 보존합니다.

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
