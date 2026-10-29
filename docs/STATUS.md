# 완료 기준과 실제 검증 상태
2026-10-29 검증 결과: **NGINX 1.30.6 / NginxForge r12 정식 발행 및 Latest 지정 완료**.
첨부된 conf.zip의 실제 설정을 기본 배포 conf/nginx.conf, conf/mime.types, conf/site.conf에 반영했습니다.
세 플랫폼 배포 패키지의 site.conf 해시는 모두 동일하며 첨부 설정의 기본 도메인과 PDF.js blob CSP를 포함합니다.
정책 38개 분할 파일과 개별 include ON/OFF, KISA WEB-01~WEB-26 주석/대응표를 그대로 제공합니다.

- [x] Linux AMD64/ARM64 musl 완전 정적 바이너리 빌드
- [x] Ubuntu 22.04/24.04와 Rocky Linux 8/9에서 AMD64·ARM64 각각 실행
- [x] Windows Server 2022 AMD64 바이너리 빌드 및 실행
- [x] 환경당 111개, 9개 필수 환경 전체 **999개 실행 검사** 성공
- [x] 단위 검사 30개 및 release 게이트 성공
- [x] 세 바이너리, SHA256SUMS.txt, build-manifest.json 총 다섯 자산 자동 발행
- [x] 정식 릴리즈 공개 상태(draft=false, prerelease=false, Latest) 및 다운로드 해시 재검증
- [x] 세 플랫폼 아카이브의 conf/site.conf가 저장소의 기본 설정과 동일함을 확인

| 증거 | 결과 |
| --- | --- |
| [전체 빌드·9개 환경 실행·자동 발행](https://github.com/appdign/NginxForge/actions/runs/40826886158) | AMD64/ARM64/Windows 성공·999개 검사 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r12) | 세 바이너리와 manifest/checksum, Latest |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r12/build-manifest.json) | 입력 해시·의존성·툴체인·플랫폼별 9개 테스트 증거 |
| [보안 설정 안내](SECURITY-CONFIG.md) | 사이트별 정책·KISA 주석·운영 주의사항 |

소스 revision: b8ee9b9ee126bda72a729ed311ff84cb96472d9b. NGINX 공식 commit: fb0e979c6dd63c018958b41eeb844947c5c21264.
의존성: headers-more 0.40, OpenSSL 3.5.9, PCRE2 10.49, zlib 1.3.2.

사용자 지정 site.conf는 edoc-dev.sogang.ac.kr, *.sogang.ac.kr, Windows 인증서/웹루트 경로와 loopback 백엔드 주소를 기본값으로 가집니다. 인증서와 개인 키 파일 내용은 패키지에 포함하지 않습니다. Linux 서버에서 실행하기 전 Windows 경로를 해당 서버 경로로 변경해야 합니다. 배포는 GitHub Release 및 로컬 산출물이며 고객 운영 서버 설정을 원격 변경하지 않았습니다.

전체 1 GiB는 요청 본문 상한이며 파일당 50 MiB·폼 5 MiB는 별도 Spring MVC/Tomcat 설정입니다. Linux 컨테이너는 native userspace를 검사하고 runner 커널을 공유합니다. 고객 서비스·부하·인증서·커널·NTFS 검증은 별도이며, KISA 대응 주석/표는 인증이나 자동 합격 판정이 아닙니다.

## 이전 릴리즈 기록

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
