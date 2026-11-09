# 완료 기준과 실제 검증 상태
2026-11-09 검증 결과: **NGINX 1.30.6 / NginxForge r14 정식 발행 및 Latest 지정 완료**.
KISA 스캔에서 지적된 WEB-16은 HTTP 가상 호스트를 고르기 전 생성되는 parser 오류 응답에서 `Server: nginx/1.30.6`이 노출된 문제였습니다. 공통 `http {}` 수준과 기본 80/443 listener에서 `server_tokens off` 및 `more_clear_headers Server`를 적용하고, 잘못된 평문 HTTP 요청을 TLS 포트에 보냈을 때 `Server` 헤더가 없는지 9개 실행 환경에서 검사했습니다.
사용자 제공 사이트 설정과 PDF.js blob 지원(frame-src self/blob 포함)을 r14 배포 설정에 유지했습니다. `frame-src`는 우리 사이트가 로드하는 blob 프레임을 허용하며, 외부 사이트의 임베드는 site.conf의 별도 `frame-ancestors` 설정으로 관리됩니다. 프레임 로딩 허용은 교차 출처 프레임의 JavaScript/print 접근 권한을 부여하지 않습니다.
KISA 보고서에서 별도로 FAIL된 WEB-09(NGINX 서비스가 Windows SYSTEM 계정으로 실행)와 WEB-26(로그 경로 ACL의 Users 쓰기 권한)은 운영체제/서비스 설정 문제라 NGINX 설정으로 차단할 수 없습니다. 이 작업 환경에는 DIGIRECEIPT-DEV 서버 접근이 없어 원격 서비스 계정과 ACL은 변경하지 않았습니다. WEB-24는 업로드 경로 정보 부재로 MANUAL_REVIEW이며 FAIL은 아닙니다. 전체 재점검 PASS를 주장하려면 해당 서버의 서비스 계정/NTFS ACL 조정 후 KISA 재검사가 필요합니다.
정책 38개 분할 파일과 개별 include ON/OFF, KISA WEB-01~WEB-26 주석/대응표를 유지합니다.

- [x] Linux AMD64/ARM64 musl 완전 정적 바이너리 빌드
- [x] Ubuntu 22.04/24.04와 Rocky Linux 8/9에서 AMD64·ARM64 각각 실행
- [x] Windows Server 2022 AMD64 바이너리 빌드 및 실행
- [x] 환경당 112개, 9개 필수 환경 전체 **1,008개 실행 검사** 성공
- [x] KISA WEB-16 parser-error 응답에서 Server 버전 헤더 제거를 9개 환경에서 검사
- [x] frame-src self/blob가 배포 설정과 실제 CSP 응답에 포함되는지 검사
- [x] 세 바이너리, SHA256SUMS.txt, build-manifest.json 총 다섯 자산 자동 발행
- [x] 공개 Latest 릴리즈 및 다운로드 SHA-256SUMS 검증
- [x] 세 플랫폼 패키지 site.conf 동일 SHA-256 확인: 3caa3451d9056a46496ea7c00e7fb33a8a8498b0a9f50ca8b64946147468120a

| 증거 | 결과 |
| --- | --- |
| [전체 빌드·9개 환경 실행·자동 발행](https://github.com/appdign/NginxForge/actions/runs/42571411512) | AMD64/ARM64/Windows 성공·1,008개 검사 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r14) | 세 바이너리와 manifest/checksum, Latest |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r14/build-manifest.json) | 입력 해시·의존성·툴체인·플랫폼별 9개 테스트 증거 |
| [보안 설정 안내](SECURITY-CONFIG.md) | blob 프레임 CSP 및 사이트별 정책/운영 주의사항 |

릴리즈 빌드 소스: 6d255a728823b9f0e1e1a4984d07e442650e282a. NGINX 공식 commit: fb0e979c6dd63c018958b41eeb844947c5c21264.
의존성: headers-more 0.40, OpenSSL 3.5.9, PCRE2 10.49, zlib 1.3.2.

사용자 지정 site.conf는 edoc-dev.sogang.ac.kr, *.sogang.ac.kr, Windows 인증서/웹루트 경로와 loopback backend 주소를 기본값으로 가집니다. 인증서와 개인 키 파일 내용은 패키지에 포함하지 않습니다. Linux에서 실행할 경우 Windows 경로를 바꿔야 합니다. GitHub Release에 배포했으며 운영 서버 설정은 원격 변경하지 않았습니다.

전체 1 GiB는 요청 본문 상한이며 파일당 50 MiB·폼 5 MiB는 별도 Spring MVC/Tomcat 설정입니다. Linux 컨테이너는 native userspace를 검사하고 runner 커널을 공유합니다. 고객 서비스·부하·인증서·커널·NTFS 검증은 별도이며, KISA 대응 주석/표는 인증이나 자동 합격 판정이 아닙니다.

## 이전 릴리즈 기록

r13은 r14 이전 Latest 릴리즈로, PDF.js blob 프레임의 CSP 허용과 배포 검증을 추가했습니다. [r13 검증 기록](https://github.com/appdign/NginxForge/actions/runs/40829165767) 및 [릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r13)를 보존합니다.


r11은 [9개 환경·999개 검사 통과](https://github.com/appdign/NginxForge/actions/runs/40462605813) 후 발행한 이전 Latest 릴리즈이며, r12에서 사용자 제공 기본 사이트 설정을 반영하고 모든 필수 게이트를 다시 검증했습니다.

r10은 [990개 실행 검사와 자동 발행](https://github.com/appdign/NginxForge/actions/runs/40454885270)을
통과했습니다. [r10 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r10)는
iframe 도메인 한 줄과 site.conf의 KISA 항목 주석을 제공했습니다. 빌드 소스는
2c85de8213f4fe91ffe66c7a87022f8c24256a0d입니다. 맞춤형 r10 ZIP은 최소 업데이트였고
r11부터는 주석 보강된 정책 38개 전체를 포함한 맞춤형 전체 구성본을 제공합니다.

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
