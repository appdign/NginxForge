# 빌드 및 검증

`config/build-config.yml`은 JSON 문법을 사용하는 YAML 파일입니다. 별도 YAML 라이브러리가
필요하지 않습니다. 공통 configure 옵션과 플랫폼별 옵션, 컨테이너 digest, 필수 플랫폼을
한 곳에서 관리합니다. `dependencies.lock.json`은 외부 소스 버전·커밋·SHA-256을 고정합니다.

## GitHub Actions

`release.yml`이 공식 채널의 최신 버전 또는 수동 지정 버전을 확인하고 공식
`release-<version>` 태그를 불변 커밋으로 해석합니다. HTTPS로 받은 해당 커밋의
소스 아카이브 SHA-256을 단 한 번 결정해 공통 `plan.json`에 넣습니다.
모든 빌드는 같은 계획을 내려받아 소스 버전, digest, 의존성과 패치 해시를 확인합니다.
업스트림 태그의 서명을 PGP로 검증하는 방식은 구현하지 않았습니다. 신뢰 기반은
공식 GitHub 저장소의 태그 조회, HTTPS와 커밋 식별자입니다.

| 작업 | Runner | 빌드/실행 환경 |
| --- | --- | --- |
| Linux AMD64 | ubuntu-24.04 | digest 고정 Alpine musl |
| Linux ARM64 | ubuntu-24.04-arm | digest 고정 Alpine musl |
| Linux AMD64 실행 | ubuntu-24.04 | Ubuntu 22.04/24.04, Rocky 8/9 컨테이너 |
| Linux ARM64 실행 | ubuntu-24.04-arm | Ubuntu 22.04/24.04, Rocky 8/9 컨테이너 |
| Windows AMD64 | windows-2022 | MSVC x64, native Perl, Git Bash, nmake |

네이티브 Runner가 없으면 대기 또는 실패하며, ARM 검증을 생략하거나 에뮬레이션으로
대체하여 릴리즈하지 않습니다. 공개 저장소의 표준 ARM64 Runner를 사용합니다.
Windows는 공식 Win32 빌드 절차를 따르며 Git Bash를 configure 셸로 사용합니다.
MSVC는 `-FIngx_config.h`로 NGINX의 precompiled header를 소스보다 먼저 포함하고
`DDEBUG=0`을 공통 정의합니다. headers-more의 늦은 ngx_config.h include가 그 앞의
모듈 선언을 건너뛰게 하는 MSVC PCH 문제를 컴파일 옵션으로 해결하며 모듈 코드를
수정하거나 경고를 비활성화하지 않습니다.
[MSVC forced include 설명](https://learn.microsoft.com/en-us/cpp/build/reference/fi-name-forced-include-file)
및 [precompiled header 동작](https://learn.microsoft.com/en-us/cpp/build/reference/yu-use-precompiled-header-file)을 참고하세요.
OpenSSL은 두 Linux CPU에서 네이티브 최적화를 사용하고 Windows에서는 no-asm을 사용합니다.
Linux 기본 worker 계정은 `daemon:daemon`으로 명시하여 Alpine의 빌드 시 계정 자동 감지가
Ubuntu/Rocky 런타임의 그룹 이름 차이로 이어지지 않게 합니다. 운영에서는 전용 계정을
설정하고, 기존 nginx.conf의 user 지시문은 그대로 우선합니다.

Linux는 `file`, `readelf`, `ldd` 진단과 별도 ELF 파서로 완전 정적 링크와 ELF 머신을
검사합니다. PT_INTERP와 DT_NEEDED 등 외부 DSO 의존성을 금지합니다.
정적 PIE의 자체 재배치를 위한 PT_DYNAMIC은 공유 라이브러리 의존성을 뜻하지 않으므로
허용하되 각 항목을 파싱하여 의존성이 없는지 검사합니다.
[GCC 정적 PIE 설명](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html)을 참고하세요. Windows는 PE AMD64와
`dumpbin /dependents`로 비시스템 DLL 의존성을 차단하고 MSVC 정적 CRT를 사용합니다.
OpenSSL의 외부 모듈/DSO 로딩은 비활성화합니다.

## 보안 프로필과 실행 검사

`config/runtime`의 nginx.conf·사이트 스위치 목록·37개 정책 파일·SPA/WS map, 보안 운영 문서와 26개 항목
대응표를 공통 build plan에서 SHA-256으로 고정합니다. 텍스트는 LF로 통일합니다.
symlinks.conf의 단일 OS marker만 Linux native 차단과 Windows OS ACL 요구사항으로
렌더링하고 모든 보안 파일의 digest를 기록합니다. 렌더링 결과는 게이트에서도 재생성해 대조합니다.

기존 40개 검사에 47개 패키지 보안 프로필 검사를 추가합니다. 배포된 실제 파일의 기본
ON 상태로 리디렉션, unknown Host/SNI, 헤더 상속, 파일·메소드·요청 제한, 프록시·쿠키·관리자
CIDR을 검사합니다. 32개 정책을 하나씩 OFF한 설정과 모두 OFF한 설정을 실제 바이너리로
문법 검사하고, 대표 10개 정책은 OFF 동작과 다른 정책 유지 여부도 실제 요청으로 확인합니다.
단일 도메인 SPA/REST/WebSocket 샘플은 선택된 정책 각각 OFF와 모두 OFF의 문법 및
실제 101/frame 왕복, origin 거부, 두 목적지와 prefix/query 유지, REST 메소드·헤더·캐시·
정규식 우선순위·index 부재를 추가 검사합니다. 테스트 포트/loopback backend/CIDR·인증서
fixture 외의 보안 지시문은 교체하지 않습니다.
Linux는 실제 symlink 요청 거부를 검사합니다. Windows는 native 기능이 없음을 명시한
정책/운영 요구사항을 검사하며 NTFS 링크 차단을 실행 검증했다고 표시하지 않습니다.

## 실행 검사와 릴리즈 게이트

동일한 `tests/run-integration.py`가 9개 OS/CPU 조합에서 **패키지를 풀어 실제 배포 바이너리**로
실행됩니다. 버전, 빌드 옵션, 유효/무효 설정, 기본 샘플 설정, HTTP·HTTPS 서버, 정적 파일,
HEAD, 404·500, 프록시 성공·오류, Server 헤더 제거/변경, X-Powered-By 제거,
gzip, rewrite, TLS 1.2/1.3와 HTTP/2 ALPN/SETTINGS를 검사합니다.
테스트 인증서와 키는 loopback 전용 공개 fixture입니다.

테스트 실패 시 성공 보고서를 만들지 않습니다. `fail-fast: false`는 나머지 플랫폼의
진단을 계속 수집하며 필수 실패를 무시하지 않습니다. `continue-on-error`는 사용하지 않습니다.
`gate-release.py`가 9개 성공 보고서의 실제 OS·CPU, 전체 검사 목록, 소스 계획, 실행 바이너리
SHA-256과 패키지 SHA-256을 대조합니다. 누락, 중복, 다른 소스 혼입 모두 차단합니다.

Linux 컨테이너는 해당 배포판의 userspace를 검증하며 호스트 커널을 공유합니다.
Windows build 20348을 확인하지만 GitHub Runner 결과가 고객사의 실제 설치·서비스·보안 정책·
부하 검증을 대신하지 않습니다. SELinux 정책과 systemd 서비스 검증도 별도입니다.

## 재현 정보와 의존성 업데이트

릴리즈 `build-manifest.json`에 upstream commit, 의존성 커밋/해시, 패치,
configure 옵션, 툴체인 패키지 목록/버전, 빌드 호스트, 실행 증거를 기록합니다.
컨테이너 이미지는 multiarch index digest로 고정하고 Actions도 커밋으로 고정합니다.
Alpine apk·Ubuntu apt·Rocky dnf의 설치 패키지 저장소는 스냅샷으로 고정하지 않았으므로
비트 단위의 재현 가능성을 보장하지 않습니다. 툴체인까지 고정하려면 별도 snapshot image를
만들어 digest와 패키지 목록을 갱신하고 전체 검증을 수행하세요.

의존성 갱신은 공식 저장소의 태그/커밋과 다운로드 SHA-256을 검토하여 lock을 바꾸고
빌드 revision을 증가시킵니다. NGINX 버전은 코드에 하드코딩하지 않으며 공식 Stable 또는
Mainline 선택값에서 결정합니다. 보안 수정은 어느 아키텍처에서도 제외하지 않습니다.

참고: [공식 configure](https://nginx.org/en/docs/configure.html),
[공식 Win32 절차](https://nginx.org/en/docs/howto_build_on_win32.html),
[headers-more](https://github.com/openresty/headers-more-nginx-module),
[GitHub Runner 사양](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
