# NginxForge 프로젝트 구축 프롬프트

## 0. 프로젝트 목표

프로젝트명: **NginxForge**

공식 NGINX Open Source 업스트림을 기반으로 보안 관련 기능을 확장한 Linux 및 Windows용 NGINX 바이너리를 자동 빌드하고 GitHub Releases에 배포하는 오픈소스 프로젝트를 구축한다.

본 프로젝트는 NGINX를 새로 구현하거나 독자적인 웹 서버를 개발하는 프로젝트가 아니다.

**공식 NGINX 소스는 최대한 유지하고, 최소한의 확장 모듈 또는 패치만 적용하여 업스트림 신규 릴리즈를 지속적으로 추적하는 것이 핵심이다.**

작업은 단순 설계나 예제 작성에 그치지 말고, 실제 GitHub 저장소에 커밋할 수 있는 파일과 실행 가능한 빌드·테스트 워크플로까지 구현한다.

## 1. 필수 요구사항

### 1.1 필수 지원 플랫폼

- Windows Server 2022 x64 (AMD64)
- Ubuntu 22.04 / 24.04 x64 (AMD64)
- Ubuntu 22.04 / 24.04 ARM64 (AArch64)
- Rocky Linux 8 / 9 x64 (AMD64)
- Rocky Linux 8 / 9 ARM64 (AArch64)

Linux AMD64와 ARM64는 동등한 수준의 필수 지원 플랫폼으로 취급한다.
ARM64 지원을 후속 개발 과제로 미루지 않는다.

### 1.1.1 ARM64 빌드 요구사항

1. GitHub Actions에서 Linux AMD64 및 ARM64 바이너리를 자동 빌드한다.
2. ARM64 네이티브 GitHub Actions Runner를 우선 검토하고, 필요하면 크로스 컴파일을 사용한다.
3. musl libc 기반 정적 링크를 두 아키텍처 모두 지원한다.
4. OpenSSL, PCRE2, zlib 및 추가 보안 기능이 ARM64에서도 정상 작동해야 한다.
5. Ubuntu 및 Rocky Linux의 ARM64 환경에서 실제 실행 테스트를 수행한다.
6. ARM64 테스트 실패 시 해당 버전의 전체 릴리즈를 중단한다.
7. AMD64와 ARM64는 동일한 NGINX 버전 및 보안 패치를 사용한다.

Windows 서버는 고객사 운영 서버로 WSL, Docker, Hyper-V, MSYS2, 컴파일러 등의 추가 설치가 제한되어 있다.

따라서 모든 빌드 작업은 GitHub Actions에서 수행해야 한다.

고객사 서버에는 완성된 바이너리만 배포한다.

### 1.2 기본 배포 원칙

Windows:
- `nginx.exe` 단일 실행 파일을 목표로 한다.
- 추가 모듈은 가능하면 정적으로 통합한다.
- 실행 시 별도 개발 도구나 런타임 설치를 요구하지 않는다.
- `nginx.conf` 등 기존 설정을 유지한다.

Linux:
- Gitea와 유사한 단일 바이너리 배포를 목표로 한다.
- Ubuntu와 Rocky Linux에서 공통으로 실행되는 바이너리를 우선 검토한다.
- musl libc 기반 완전 정적 빌드를 Linux AMD64와 ARM64 모두에서 필수 구현한다.
- OpenSSL, PCRE2, zlib 및 보안 확장 기능을 AMD64·ARM64 모두에 정적으로 통합한다.
- 고객사 서버에서 `configure`, `make`, `make install`을 요구하지 않는다.
- 최초 환경 구성 이후에는 실행 파일 교체만으로 업데이트할 수 있어야 한다.

완전 정적 빌드가 특정 기능과 충돌한다면 문제를 조사하고 현실적인 대안을 구현한다.

완전 정적 링크를 구현하지 못했다면 단일 바이너리 호환성을 달성했다고 보고하지 않는다.

### 1.3 NGINX 업스트림

공식 저장소:

https://github.com/nginx/nginx

- 공식 릴리즈 태그를 기준으로 버전을 선택한다.
- 기본 추적 채널은 Stable로 한다.
- Mainline으로 전환할 수 있는 옵션을 제공한다.
- 버전 문자열을 하드코딩하지 않는다.
- 신규 버전을 자동 감지한다.
- 기존에 릴리즈한 업스트림 버전은 중복 배포하지 않는다.
- 공식 소스를 가능한 한 수정하지 않는다.
- 변경 사항은 별도 패치 또는 외부 모듈로 관리한다.
- 업스트림 릴리즈와 자체 빌드 리비전을 구분한다.
- 새 업스트림 버전에서 빌드나 테스트에 실패하면 기존 정상 릴리즈를 유지한다.

## 2. 보안 관련 확장 기능

다음 기능을 제공하는 것이 목적이다.

### 필수 기능

1. HTTP 응답의 Server 헤더 제거
2. Server 헤더를 임의의 문자열로 변경
3. NGINX 버전 정보 노출 방지
4. 기본 오류 응답에서 NGINX 식별 정보 노출 최소화
5. 불필요한 응답 헤더 제거 및 변경
6. HTTP 및 HTTPS 환경에서 동일하게 동작

가능하면 다음과 같은 형태로 설정할 수 있도록 한다.

```nginx
server_tokens off;

more_set_headers 'Server: CustomServer';

more_clear_headers 'X-Powered-By';
```

단, 위 구문은 목표 사용 예시이며 반드시 같은 구현체를 사용해야 하는 것은 아니다.

기존 `headers-more-nginx-module` 활용 가능성을 먼저 조사한다.

Windows 빌드 호환성, 업스트림 유지보수, 라이선스 및 정적 링크 가능성을 검증한다.

외부 모듈 사용이 불리하다면 최소한의 NGINX 소스 패치 방식도 비교한다.

**가장 중요한 판단 기준은 업스트림 NGINX 업데이트 시 유지보수 부담이 적은 구조이다.**

기능을 구현하기 위해 불필요하게 NGINX 내부 코드를 광범위하게 수정하지 않는다.

Server 헤더 제거·변경이 기본 응답, 오류 응답, 프록시 응답에서 실제로 적용되는지 테스트한다.

Server 헤더 은닉을 보안 취약점 자체의 해결로 간주하지 않는다.

## 3. 저장소 구조

다음 구조를 기본으로 하되 필요에 따라 개선한다.

```text
NginxForge/
├── .github/
│   └── workflows/
│       ├── upstream-check.yml
│       ├── build-linux.yml
│       ├── build-windows.yml
│       └── release.yml
├── config/
│   └── build-config.yml
├── modules/
├── patches/
├── scripts/
│   ├── check-upstream.py
│   ├── build-linux.sh
│   ├── build-windows.ps1
│   ├── verify-binary.sh
│   └── package-release.py
├── tests/
│   ├── test-headers.py
│   ├── test-reverse-proxy.py
│   └── test-nginx-config.py
├── docs/
│   ├── BUILD.md
│   ├── INSTALL.md
│   ├── UPDATE.md
│   └── UPSTREAM.md
├── README.md
├── LICENSE
└── THIRD_PARTY_LICENSES.md
```

NGINX 전체 소스 코드를 저장소에 복사해서 유지하는 방식은 가급적 피한다.

공식 릴리즈 소스를 빌드 시 가져오도록 한다.

외부 의존성은 버전 또는 커밋을 고정하고 검증 가능한 방법으로 다운로드한다.

## 4. GitHub Actions 자동 업데이트

### 4.1 스케줄러

매일 한국시간 오전 9시경 신규 업스트림 릴리즈를 확인한다.

GitHub Actions의 `schedule` 기능을 사용한다.

다음 실행 방식도 제공한다.

- `workflow_dispatch`: 수동 실행
- 업스트림 버전 직접 지정
- Stable/Mainline 선택
- 특정 버전 재빌드
- 자체 패치 변경 시 빌드 실행

스케줄 실행이 지연되거나 누락될 수 있다는 점을 고려하고, 다음 실행에서 누락된 버전을 감지할 수 있도록 구성한다.

### 4.2 업스트림 변경 감지

1. 공식 NGINX 릴리즈 목록 조회
2. Stable 또는 Mainline 최신 버전 결정
3. 기존 GitHub Releases와 비교
4. 신규 버전이 없다면 종료
5. 신규 버전이면 빌드 실행

릴리즈 조회 실패나 네트워크 오류를 신규 버전이 없는 것으로 잘못 판단하지 않는다.

### 4.3 자동 빌드

새로운 업스트림 버전이 감지되면 다음을 수행한다.

1. 공식 소스 다운로드
2. 소스 버전 및 무결성 확인
3. 고정된 모듈 또는 패치 적용
4. Linux AMD64 musl 정적 빌드
5. Linux ARM64 musl 정적 빌드
6. Windows AMD64 빌드
7. 세 바이너리 검증
8. 전체 필수 운영체제·CPU 기능 테스트
9. 전체 성공 시 GitHub Release 생성

Linux AMD64, Linux ARM64 및 Windows AMD64 빌드는 병렬 실행할 수 있도록 설계한다.

단, 모든 필수 플랫폼이 통과하기 전에는 정식 릴리즈를 발행하지 않는다.

## 5. Linux 빌드

Linux 빌드는 가장 중요한 기능 중 하나다.

목표는 Ubuntu와 Rocky Linux에서 동일한 NGINX 실행 파일을 사용할 수 있도록 만드는 것이다.

요구사항:

- Linux AMD64와 ARM64 동등한 필수 지원
- AMD64·ARM64 모두 musl libc 기반 완전 정적 링크 구현
- OpenSSL 지원
- PCRE2 지원
- zlib 지원
- HTTP/2 지원
- 리버스 프록시 지원
- gzip 및 rewrite 지원
- 보안 관련 확장 기능 포함
- 실행 파일 단독 배포
- 고정된 설정 파일 경로

`ldd`, `file`, `readelf` 등을 활용해 동적 의존성 여부를 검증한다.

Ubuntu 22.04/24.04 및 Rocky Linux 8/9의 AMD64·ARM64 각 환경에서 실제 NGINX 실행 테스트를 수행한다.

컨테이너에서 테스트할 수 있지만, 고객사 서버에서는 컨테이너가 필요 없어야 한다.

단일 바이너리를 제공하더라도 설정 파일, 인증서, 로그 디렉터리 등의 외부 런타임 리소스는 필요할 수 있다.

이 사실을 문서에 명확히 기재한다.

## 6. Windows 빌드

Windows는 네이티브 Win32 NGINX 빌드로 구현한다.

참고 문서:

https://nginx.org/en/docs/howto_build_on_win32.html

요구사항:

- GitHub Actions Windows Runner 사용
- Visual C++ 컴파일러 사용
- 필요한 빌드 도구 자동 준비
- 공식 NGINX 빌드 절차 준수
- OpenSSL 지원
- PCRE2 지원
- zlib 지원
- 보안 확장 기능 통합
- Windows Server 2022 호환성 검증
- 가능하면 단일 `nginx.exe` 생성

Windows에서 외부 모듈 컴파일 문제가 발생하면 원인을 파악하고 플랫폼 호환성 패치를 최소화한다.

Linux 전용 API를 그대로 사용하지 않는다.

Windows에서 실제 `nginx.exe`를 실행하여 설정 및 HTTP 요청 테스트를 진행한다.

GitHub의 Windows Runner 테스트를 Windows Server 2022 실환경 검증과 동일하다고 주장하지 않는다.

실제 Windows Server 2022 검증이 수행되지 않았다면 별도 확인이 필요함을 문서화한다.

## 7. 테스트 및 품질 검증

컴파일 성공만으로 릴리즈하지 않는다.

다음 테스트를 구현한다.

### 기능 테스트

- `nginx -v`
- `nginx -V`
- `nginx -t`
- HTTP 서버 기동
- HTTPS 서버 기동
- Server 헤더 변경
- Server 헤더 제거
- 버전 정보 은닉
- 오류 응답 처리
- 리버스 프록시
- 정적 파일 응답
- gzip
- rewrite

### 호환성 테스트

- Ubuntu 22.04 AMD64 / ARM64
- Ubuntu 24.04 AMD64 / ARM64
- Rocky Linux 8 AMD64 / ARM64
- Rocky Linux 9 AMD64 / ARM64
- Windows Server 2022 AMD64 빌드 및 실행 환경

실행 파일과 설정 파일의 경로가 버전 변경 후에도 일관성을 유지하는지 확인한다.

가능하다면 HTTP 요청 및 응답을 자동 비교한다.

### 릴리즈 차단 조건

- 컴파일 실패
- 패치 적용 실패
- 필수 모듈 누락
- 바이너리 실행 실패
- `nginx -t` 실패
- Server 헤더 변경 기능 실패
- 필수 운영체제 테스트 실패

문제가 발생하면 GitHub Actions 실패로 명확히 표시하고 정식 릴리즈를 발행하지 않는다.

## 8. GitHub Releases

릴리즈 파일명 예시:

```text
nginxforge-1.x.x-linux-amd64.tar.gz
nginxforge-1.x.x-linux-arm64.tar.gz
nginxforge-1.x.x-windows-amd64.zip
SHA256SUMS.txt
build-manifest.json
```

파일명과 버전은 실제 업스트림 버전을 기준으로 자동 생성한다.

빌드 리비전이 필요한 경우 별도의 식별자를 추가한다.

릴리즈 설명에는 다음 정보를 포함한다.

- NGINX 업스트림 버전
- NginxForge 빌드 리비전
- 포함된 모듈
- 적용한 패치
- 주요 빌드 옵션
- 지원 운영체제
- 알려진 제한 사항
- 업스트림 변경 사항 링크

`build-manifest.json`에는 재현 가능한 빌드를 위해 업스트림 커밋, 의존성 버전, 모듈 커밋 및 빌드 옵션을 기록한다.

SHA-256 체크섬을 제공한다.

모든 필수 검증을 통과한 릴리즈만 Latest로 지정한다.

## 9. 고객사 업데이트

고객사에는 별도의 빌드 도구를 설치하지 않는다.

### Windows

- 기존 `nginx.exe` 백업
- 새 바이너리의 체크섬 검증
- 기존 설정 호환성 확인
- NGINX 정상 종료
- 실행 파일 교체
- 설정 검사
- 정상 기동
- 실패 시 롤백

### Linux

- 기존 실행 파일 백업
- 새 바이너리의 체크섬 검증
- 기존 설정 호환성 확인
- 안전한 바이너리 교체
- 설정 검사
- 정상 기동
- 실패 시 롤백

Linux에서는 공식 NGINX 바이너리 업그레이드 기능을 활용한 무중단 업데이트 방법도 문서화한다.

이미 패키지 관리자로 설치된 NGINX를 무조건 덮어쓰지 않는다.

기존 `nginx -V` 결과를 확인하여 경로, 빌드 옵션, 동적 모듈 및 런타임 의존성을 검증한다.

실행 파일 업데이트로 기존 설정·인증서가 삭제되거나 초기화되지 않아야 한다.

업데이트 스크립트는 설치된 환경을 임의로 변경하기 전에 검증 및 백업을 수행해야 한다.

## 10. 오픈소스 및 라이선스

본 프로젝트는 공개 GitHub 저장소로 운영한다.

- 공식 NGINX와의 관계를 명확하게 설명한다.
- 공식 NGINX 배포판으로 오인시키지 않는다.
- NGINX 라이선스 고지를 유지한다.
- 추가 모듈의 라이선스를 검토한다.
- 제3자 라이브러리 고지를 포함한다.
- 비공식 커뮤니티 빌드임을 README에 명시한다.

## 11. 개발 진행 원칙

다음 순서로 작업한다.

1. 공식 NGINX 빌드 절차와 모듈 구조 조사
2. Windows 및 Linux 호환성 검토
3. 가장 유지보수하기 쉬운 확장 방식 결정
4. 프로젝트 구조 생성
5. Linux AMD64 musl 정적 빌드 구현
6. Linux ARM64 musl 정적 빌드 구현
7. Windows AMD64 빌드 구현
8. 공통 보안 기능 테스트 작성
9. Ubuntu/Rocky AMD64·ARM64 호환성 검증
10. 업스트림 자동 감지 구현
11. 세 바이너리 GitHub Releases 자동 배포 구현
12. 전체 플랫폼 문서화 및 최종 검증

문제가 발생했을 때 임의의 우회 코드로 테스트만 통과시키지 않는다.

특히 테스트 실패를 무시하거나 `continue-on-error`로 필수 검증을 통과한 것처럼 처리하지 않는다.

불가능하거나 검증되지 않은 부분은 명확히 표시한다.

외부 모듈 호환성을 억지로 맞추기 위해 유지보수가 어려운 대규모 소스 변경을 하지 않는다.

코드 변경 후에는 가능한 범위에서 실제 빌드와 테스트를 수행한다.

GitHub 접근 권한이 없다면 로컬에서 검증 가능한 워크플로를 구현하고, 원격 배포가 검증되지 않았음을 명시한다.

실제 릴리즈가 만들어지지 않았다면 릴리즈 완료라고 보고하지 않는다.

## 12. 최종 완료 조건

프로젝트 완료 기준은 다음과 같다.

- [ ] Linux AMD64 정적 바이너리 빌드 성공
- [ ] Linux ARM64 정적 바이너리 빌드 성공
- [ ] Windows AMD64 바이너리 빌드 및 실행 테스트 성공
- [ ] Server 헤더 변경 및 제거 테스트 성공
- [ ] 버전 노출 방지 테스트 성공
- [ ] Ubuntu 22.04/24.04 AMD64·ARM64 실행 테스트 성공
- [ ] Rocky Linux 8/9 AMD64·ARM64 실행 테스트 성공
- [ ] Windows NGINX 기본 동작 테스트
- [ ] 공식 NGINX 신규 릴리즈 자동 감지
- [ ] 신규 버전만 자동 빌드
- [ ] 세 플랫폼 바이너리 GitHub Releases 자동 배포
- [ ] 세 플랫폼 모두 성공해야 Latest 릴리즈 발행
- [ ] 실패 시 기존 Latest 릴리즈 유지
- [ ] 고객사 바이너리 업데이트 및 롤백 절차 문서화
- [ ] README 및 라이선스 문서 작성

**최종 목표는 사용자가 평소에 아무런 관리 작업을 하지 않아도 공식 NGINX 신규 버전을 자동으로 추적하고, 검증된 Linux/Windows 커스텀 바이너리를 GitHub Releases에서 즉시 다운로드할 수 있는 상태를 만드는 것이다.**

작업을 시작하고, 실제 구현과 검증을 진행하라. 단순한 개발 계획만 제출하고 종료하지 마라.

**ARM64를 포함한 모든 필수 플랫폼의 빌드와 검증이 완료되기 전까지 프로젝트를 완료 처리하지 않는다.**
