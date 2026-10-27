# 완료 기준과 실제 검증 상태

r11 검증 중: 정책 38개 전체에 취약점/조치/별도 점검 주석을 보강하고, 공개 배포에도 주석 포함 사이트 원본을 제공합니다.
맞춤형은 최소 업데이트가 아닌 전체 구성본으로 다시 제공합니다. 전체 검증/발행 전에는 r11을 완료로 표시하지 않습니다.

2026-10-27 검증 결과: **NGINX 1.30.6 / NginxForge r10 정식 발행 및 Latest 지정 완료**.
site.conf의 site_embed_domain 한 줄로 iframe 부모 도메인/와일드카드를 지정합니다.
CSP frame-ancestors와 X-Frame-Options가 자동으로 연동되며 운영 도메인은 정책/nginx.conf에
반복 입력하지 않습니다. API 프록시 목적지·CORS·WebSocket·connect-src는 기존대로 유지합니다.
분할 정책 38개와 개별 include ON/OFF를 보존하고 설정 옆에 KISA WEB-xx/추가 강화 주석을 넣었습니다.

- [x] Linux AMD64/ARM64 native musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04, Rocky Linux 8/9에서 AMD64/ARM64 각각 실행
- [x] Windows Server 2022 AMD64 native 실행과 build 20348 확인
- [x] 기존 엔진 40개와 패키지/사이트 70개, 환경당 110개 × 9 = **990개 실행 검사**
- [x] 빈값/잘못된 iframe 옵션은 동일 출처만 허용하고 SAMEORIGIN 유지
- [x] 유효한 iframe 도메인은 HTTP/HTTPS 부모의 모든 포트 허용 및 upstream XFO 충돌 제거
- [x] iframe 옵션 변경 시 다른 가상호스트/API/CORS/WebSocket/connect-src 범위 유지
- [x] KISA WEB-01~WEB-26 주석 연결과 운영/앱 점검·추가 강화 구분
- [x] 단위 검사 30개, actionlint 및 설정/문서 해시 검증
- [x] 세 바이너리·9개 환경 전체 성공 후 다섯 자산 발행 및 Latest 지정
- [x] 공개 파일 재다운로드·해시·manifest·OS별 정책 렌더링 재검증
- [x] 발행 후 공식 업스트림 재조회 및 같은 릴리즈 중복 빌드/발행 생략

로컬 Windows Chrome에서 별도 **15개 실제 iframe 시나리오**를 통과했습니다.
HTTP/HTTPS 비표준 포트·중첩 하위 도메인·동일 출처는 허용하고 apex·악성 suffix·다른 회사·
다른 가상호스트·허용되지 않은 상위 ancestor는 차단했습니다. 한 줄 도메인 교체/정확한 호스트/
빈값 복원도 실행했습니다. iframe 허용 후에도 회사 부모의 브라우저 API CORS는 차단됐습니다.
브라우저 증거는 사이트 템플릿과 frame-options.conf의 SHA-256으로 릴리즈 입력과 대조했습니다.

| 증거 | 결과 |
| --- | --- |
| [전체 빌드·실행·자동 발행](https://github.com/appdign/NginxForge/actions/runs/40454885270) | 세 바이너리·9개 환경·990개 검사 |
| [발행 후 업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/40455746117) | 같은 r10의 중복 빌드/발행 생략 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r10) | 다섯 자산, draft=false, prerelease=false, Latest |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r10/build-manifest.json) | 소스/의존성/옵션/툴체인·44개 배포 입력·사이트 템플릿·실행 증거 |
| [보안 설정 안내](SECURITY-CONFIG.md) | 한 줄 iframe 옵션·KISA 주석·기존 API/CORS/WS와 독립성 |

빌드 소스: 2c85de8213f4fe91ffe66c7a87022f8c24256a0d.
NGINX 공식 commit: fb0e979c6dd63c018958b41eeb844947c5c21264.
의존성: headers-more 0.40, OpenSSL 3.5.9, PCRE2 10.49, zlib 1.3.2.
NGINX C 소스·핵심 패치·의존성은 이번 설정 변경으로 달라지지 않았습니다.
운영 conf는 세 기반 파일과 분할 정책 38개, 총 41개이며 예제/코드 프롬프트/backend YAML을 섞지 않습니다.

iframe 허용은 세션 인증·인가·쿠키 정책을 바꾸지 않습니다. HTTP SAP 등의 임베드 로그인은
SameSite=Lax와 브라우저 서드파티 쿠키 제한을 실제 환경에서 별도로 확인해야 합니다.
브라우저 fixture는 실제 SAP·고객사 앱/세션/인증서 검증이 아닙니다. 운영 서버에는 자동 적용하지 않았습니다.

전체 1 GiB는 요청 본문 상한이며 파일당 50 MiB·폼 5 MiB는 별도 Spring MVC/Tomcat 설정입니다.
Linux 컨테이너는 native userspace를 검사하고 runner 커널을 공유합니다. Windows symlink는
OS ACL/reparse point 검토가 필요하며 고객사 서비스·부하·인증서·커널·NTFS 검증은 별도입니다.
KISA 대응 주석/표는 인증이나 자동 합격 판정이 아닙니다.

## 이전 릴리즈 기록

r9는 [936개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39459365947)을
통과했습니다. [r9 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r9)는
38개 분할 정책을 유지하면서 도메인 한 줄과 사이트별 API/WS/backend 제어를 제공했습니다.
빌드 소스는 fcbbf39d8aac8934b4a6bb148b834d2ef2e6196d입니다.

r8은 [837개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39412754812)을
통과했습니다. [r8 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r8)는
인라인 CSS 호환과 MJS MIME 수정을 처음 포함했습니다. 빌드 소스는
631f2f7098b8baaa4d8a7b00a90ce171e1b597ea입니다.

r7은 [전체 810개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39373262622)을
통과했습니다. [r7 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r7)는
1 GiB 파일 서버 선택 정책과 Spring MVC/Tomcat 용량 설정 예시를 처음 포함한 공개 기록입니다.
빌드 소스는 `62d814559246e5d83d0ab9b5aadc59138d761753`입니다.

r6는 [전체 783개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/39370470807)을
첫 실행에서 통과했습니다. [r6 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r6)는
37개 정책과 단일 도메인 SPA/REST/WebSocket 샘플을 처음 포함한 공개 기록으로 보존합니다.
빌드 소스는 `a90ad174534b4efe0786a7e80e723b124fad6aca`입니다.

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
