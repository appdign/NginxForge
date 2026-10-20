# 완료 기준과 실제 검증 상태

2026-10-21 검증 결과: **NGINX 1.30.6 / NginxForge r9 정식 발행 및 Latest 지정 완료**.
기존 38개 분할 정책과 개별 include ON/OFF를 유지합니다. 도메인은 site.conf 맨 위
server_name 한 줄만 입력하고 HTTP/HTTPS 이동·동일 출처 API·현재 WSS CSP가 자동 반영됩니다.
외부 허용 목록·CSP 목적지·API/WS/backend·쿠키/업무 제한도 site.conf에서만 설정합니다.
nginx.conf/공통 정책에는 배포 도메인/backend를 입력하지 않습니다.

- [x] Linux AMD64/ARM64 native musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04, Rocky Linux 8/9에서 AMD64/ARM64 각각 실행
- [x] Windows Server 2022 AMD64 native 실행과 build 20348 확인
- [x] 기존 38개 분할 정책 보존과 활성 include별/모두 OFF 문법 검사
- [x] server_name 한 줄 변경 후 이동·API·WS·CSP 자동 변경 실행
- [x] 두 가상호스트의 root/backend/허용 목록/공개 모드/쿠키/캐시/오류/rate/본문 제한 분리
- [x] unknown Host/SNI 거부와 현재 비표준 포트/명시적 기본 포트 처리
- [x] 정확한 외부 Origin·하위 도메인 패턴 허용과 악성 suffix·다른 scheme/port·apex 거부
- [x] public API wildcard/credentials 충돌 방지, API와 WS 공개의 독립성
- [x] Origin 없는 WS 기본 거부와 사이트별 명시적 허용
- [x] 실제 WS 101 handshake와 마스킹된 frame 왕복·전체 전달 헤더
- [x] 정적 GET/HEAD와 REST 구분, URI prefix/query, SPA fallback/index 부재 처리
- [x] 파일/디렉터리/관리 경로/소스맵·보안 헤더·쿠키·캐시·오류·TLS·IP 빈도 제한
- [x] 6 MiB multipart 통과, 1 GiB 초과 Content-Length 거부, 사이트별 5 MiB 거부
- [x] 인라인 CSS·동일 사이트 JS/MJS 허용과 인라인 JS/onclick/eval 차단
- [x] 샘플/backend YAML/코드 프롬프트를 운영 conf와 분리
- [x] 세 바이너리·9개 환경 전체 성공 후 다섯 릴리즈 자산 발행/Latest 지정
- [x] 공개 다섯 파일 재다운로드·해시·manifest·원본/OS별 렌더링 재검증
- [x] 발행 후 업스트림 재조회와 중복 빌드/발행 생략

각 환경의 기존 엔진 40개와 패키지/사이트 64개, **104개 × 9 = 936개 실행 검사**가
통과했습니다. 릴리즈 안전성 단위 검사 30개와 actionlint도 통과했습니다.
Linux ELF의 인터프리터/외부 DSO 부재, Windows AMD64 PE의 정적 CRT/시스템 DLL 의존성을
확인했습니다. Linux 두 아키텍처의 소스·패치·의존성·정책은 동일합니다.
사이트별 변경 중 공통 분할 정책 38개를 변경하지 않았음을 검사했습니다.

운영 conf는 세 기반 파일(nginx.conf·mime.types·site.conf)과 분할 정책 38개, 총 41개입니다.
44개 release_inputs와 별도 사이트 템플릿 해시를 공통 계획에서 고정합니다.
공개 초기 site.conf는 127.0.0.1:8080에서 요청을 거부합니다. 실제 site.conf를 설치해야
HTTPS 사이트를 제공합니다. 이전 conf.d/map과 중복 로드하지 않습니다.
NGINX C 소스·의존성·핵심 패치는 이번 설정 변경으로 달라지지 않았습니다.

| 증거 | 결과 |
| --- | --- |
| [전체 빌드·실행·자동 발행](https://github.com/appdign/NginxForge/actions/runs/39459365947) | 최종 소스 전체 workflow success, 세 바이너리·9개 환경·936개 검사 |
| [발행 후 업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/39460879027) | 같은 r9의 중복 빌드/발행 생략 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r9) | 다섯 자산, draft=false, prerelease=false, Latest 확인 |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r9/build-manifest.json) | 소스·의존성·옵션·툴체인·배포 입력/사이트 템플릿 해시·실행 증거 |
| [보안 설정 안내](SECURITY-CONFIG.md) | 분할 정책 ON/OFF·도메인 한 줄·사이트별 API/WS/CSP·KISA 범위 |

빌드 소스: fcbbf39d8aac8934b4a6bb148b834d2ef2e6196d.
NGINX 공식 commit: fb0e979c6dd63c018958b41eeb844947c5c21264.
의존성: headers-more 0.40, OpenSSL 3.5.9, PCRE2 10.49, zlib 1.3.2.

Windows Chrome fixture에서 computed CSS/style 속성/style 태그/동적 style과 동일 출처 MJS
import, 인라인 script/onclick/eval 차단을 확인했습니다. 고객사 앱/운영 서버 검증은 아닙니다.
인라인 CSS 허용은 호환 선택이며 엄격한 스타일 정책에는 앱의 nonce/hash 연동이 필요합니다.

전체 1 GiB는 파일+폼+multipart 형식/JSON 본문 상한이며 다운로드 제한은 아닙니다.
초과 Content-Length의 즉시 거부를 검사했으며 1 GiB 전체 전송 부하 검사는 아닙니다.
파일당 50 MiB·폼 파라미터 5 MiB는 별도 Spring MVC/Tomcat 설정이고 실제 고객사 앱을
실행 검증한 것은 아닙니다. Origin/CORS/CSP는 인증·객체별 인가·CSRF를 대신하지 않습니다.

Linux는 native userspace 컨테이너이며 runner 커널을 공유합니다. 링크 파일 내용의 접근을
거부하며 SPA의 try_files는 차단된 파일 대신 정확한 공개 index를 반환할 수도 있습니다.
Windows는 symlink 지시문 미지원이므로 OS ACL/reparse point 검토 요구를 검사했습니다.
고객사 커널·서비스·SSO·backend 직접 포트·실제 인증서·부하·NTFS ACL은 별도 확인합니다.
실제 운영 설정은 자동 변경하지 않았습니다. KISA WEB-01~26 대응표는 인증/자동 합격 판정이 아닙니다.

## 이전 릴리즈 기록

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
