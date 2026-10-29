# NginxForge

공식 NGINX Open Source를 최소한으로 확장한 **비공식 커뮤니티 바이너리**입니다.
NGINX를 새로 구현하지 않으며, 공식 NGINX 배포판 또는 NGINX의 승인을 받은 제품을 의미하지 않습니다.

Linux AMD64와 ARM64는 동등한 필수 플랫폼입니다. 하나라도 빌드·실행 검증에 실패하면
그 버전 전체의 정식 릴리즈와 Latest 발행을 중단합니다.

| 필수 플랫폼 | 빌드 방식 | 릴리즈 필수 실행 검증 |
| --- | --- | --- |
| Linux AMD64 | 네이티브 Runner, musl 완전 정적 링크 | Ubuntu 22.04/24.04, Rocky Linux 8/9 |
| Linux ARM64 | 네이티브 ARM64 Runner, musl 완전 정적 링크 | Ubuntu 22.04/24.04, Rocky Linux 8/9 |
| Windows AMD64 | Windows Server 2022 Runner, MSVC /MT | 네이티브 nginx.exe 설정·HTTP·HTTPS 테스트 |

릴리즈는 3개 바이너리와 9개 OS/CPU 테스트 결과를 함께 검증합니다.
ARM64를 후속 과제로 미루거나 실패를 무시하지 않습니다. Linux 테스트는 해당 CPU의
컨테이너에서 실제 바이너리를 실행하며 호스트 커널을 공유합니다. 고객사 실제 서버의
커널, 서비스 등록, 부하 및 운영 설정 검증은 별도입니다.

다운로드: [GitHub Releases](https://github.com/appdign/NginxForge/releases)

## 기능

- headers-more 정적 통합: Server 헤더 제거/변경 및 응답 헤더 필터링
- 세 줄의 공통 패치로 기본 오류 페이지의 NGINX 식별 푸터 제거
- OpenSSL, PCRE2 JIT, zlib, HTTP/2, 리버스 프록시, gzip, rewrite
- 동일한 NGINX 태그/커밋, 보안 패치와 의존성 잠금을 세 바이너리에 적용
- 38개 정책 파일마다 취약점·조치·별도 점검 주석, 공개 패키지에도 주석 포함 사이트 원본 제공
- KISA 2026 웹 서비스 26개 항목 대응표와 공통 보안 설정·도메인별 HTTPS/프록시 예시 배포
- 파일 서버 요청 1 GiB 선택 정책과 Spring Boot/Tomcat 파일 50 MiB·폼 5 MiB 설정 예시
- 사이트별 SPA + REST + WebSocket 설정: 9090/9080 라우팅·Upgrade·실제 프레임 왕복 검사
- site.conf 한 줄로 iframe 와일드카드 허용, API/CORS/WebSocket과 분리 및 KISA WEB-xx 주석 제공
- site.conf의 정책별 include ON/OFF: CORS/CSP, 쿠키, private API no-store, 관리자/공용 관리 경로 차단
- 프론트/Spring Boot 코드 점검 프롬프트와 NGINX·프레임워크·운영 설정 담당 범위 제공
- Linux ELF 인터프리터·동적 섹션 차단, Windows AMD64 PE와 시스템 DLL 의존성 검사
- 매일 09:00 KST경 공식 Stable 확인, 수동 Mainline/특정 버전/재빌드 지원
- 모든 필수 검사 통과 → draft 업로드 → 업로드 파일 재검증 → 정식 발행

```nginx
server_tokens off;
more_clear_headers Server X-Powered-By;
# 또는
more_set_headers 'Server: CustomServer';
more_clear_headers X-Powered-By;
```

헤더 은닉은 취약점 해결을 대체하지 않습니다. `nginx -v/-V`는 운영 진단을 위해
실제 버전과 빌드 정보를 유지합니다. 기존 설정을 자동 변경하지 않으므로 기존 배포에는
위 보안 설정을 직접 적용하고 `nginx -t`로 확인해야 합니다.

## 배포 파일

```text
nginxforge-<NGINX version>-linux-amd64.tar.gz
nginxforge-<NGINX version>-linux-arm64.tar.gz
nginxforge-<NGINX version>-windows-amd64.zip
SHA256SUMS.txt
build-manifest.json
```

첫 빌드 리비전은 위 이름을 사용합니다. 리비전 2부터 버전 뒤에 `-r2` 등을 붙입니다.
Git 태그는 `v<NGINX version>-r<revision>`입니다. 정식 배포 파일을 덮어쓰지 않습니다.

고객사 서버에는 컴파일러·WSL·Docker·MSYS2가 필요하지 않습니다. 실행 파일 외에
설정, 인증서, 로그·임시 디렉터리는 필요합니다. 기본 site.conf는 edoc-dev Windows 사이트 값으로 구성되며
인증서 파일은 포함하지 않습니다. 다른 도메인이나 Linux에서 사용하면 기동 전에 site.conf의 경로/값을 바꾸세요.
단일 바이너리 교체로 업데이트할 수 있지만 다른 배포판의 옵션·동적 모듈·경로까지
자동 호환된다고 가정하지 마세요.

## 시작과 문서

GitHub Actions를 활성화하면 `main`의 빌드 관련 변경으로 검증 및 신규 버전 발행이 실행됩니다.
수동 실행은 Actions → **NginxForge gated release**에서 `version`, `channel`, `rebuild`,
`publish`를 지정합니다. 검증만 필요하면 `publish=false`를 선택합니다.
이미 발행한 버전은 스케줄에서 건너뛰고, `rebuild=true`이면 재검증만 합니다.
패치·의존성·배포 설정·포함 문서를 변경해 새 배포를 낼 때
`config/build-config.yml`의 `revision`을 올립니다.

- [빌드와 검증](docs/BUILD.md)
- [설치](docs/INSTALL.md)
- [업데이트와 롤백](docs/UPDATE.md)
- [업스트림 추적](docs/UPSTREAM.md)
- [통합 요구사항](docs/REQUIREMENTS.md)
- [실제 검증 상태와 완료 기준](docs/STATUS.md)
- [KISA 2026 보안 설정·도메인 샘플과 운영 조치](docs/SECURITY-CONFIG.md)
- [NGINX·앱 코드·프레임워크·운영 설정 구분](docs/SECURITY-OWNERSHIP.md)
- [프론트엔드 코드 전용 프롬프트](docs/prompts/FRONTEND-CODE-REVIEW.md)
- [Spring Boot 코드 전용 프롬프트](docs/prompts/SPRING-BOOT-CODE-REVIEW.md)
- [라이선스](THIRD_PARTY_LICENSES.md)

로컬 제어 로직 검증:

```console
python -m unittest discover -s tests -p "test_*.py" -v
```

바이너리 빌드는 GitHub Actions에서 수행합니다. 정식 릴리즈가 실제로 발행되고
모든 필수 플랫폼 증거가 확인되기 전에는 프로젝트를 완료로 간주하지 않습니다.

보안 정책 38개는 기존처럼 conf/policies 아래 목적별 파일로 유지합니다.
conf/site.conf의 각 include 줄로 ON/OFF하며, 도메인은 사이트 구역 맨 위 server_name
한 줄만 지정합니다. 외부 허용 목록·CSP 목적지·API·WS·backend도 site.conf에서 관리합니다.
nginx.conf/정책에 운영 도메인을 적지 않습니다. 참고 샘플/backend YAML/코드 프롬프트는
운영 conf와 분리하며, TLS만 HTTP 문맥 때문에 nginx.conf에서 선택합니다.
