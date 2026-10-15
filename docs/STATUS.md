# 완료 기준과 실제 검증 상태

2026-10-15 검증 결과: **NGINX 1.30.6 / NginxForge r1 정식 발행 및 Latest 지정 완료**.

- [x] Linux AMD64 musl 완전 정적 빌드
- [x] Linux ARM64 musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04 AMD64 실행
- [x] Ubuntu 22.04/24.04 ARM64 실행
- [x] Rocky Linux 8/9 AMD64 실행
- [x] Rocky Linux 8/9 ARM64 실행
- [x] Windows Server 2022 Runner AMD64 실행 (build 20348)
- [x] 세 바이너리 공통 보안 기능 테스트
- [x] 공식 최신 버전 감지
- [x] 발행 후 재조회에서 중복 빌드·배포 생략 확인
- [x] GitHub Releases 다섯 파일 자동 발행
- [x] 전체 성공 후 Latest 지정
- [x] 공개된 다섯 파일 재다운로드 후 무결성 검증

각 OS/CPU 조합에서 40개 실행 검사, 총 360개가 통과했습니다. 릴리즈 제어 로직의
26개 단위 테스트도 통과했습니다. Linux 바이너리 두 개는 ELF64의 PT_INTERP 및
외부 DSO 의존성 부재를 확인했고 Windows는 AMD64 PE 및 정적 CRT/시스템 DLL 의존성을 확인했습니다.

| 증거 | 결과 |
| --- | --- |
| [빌드와 실행 결과](https://github.com/appdign/NginxForge/actions/runs/38661867375) | 세 바이너리, 9개 OS/CPU 조합, 전체 릴리즈 게이트 통과 |
| [자동 발행 및 재검증](https://github.com/appdign/NginxForge/actions/runs/38682918382) | 원본 산출물·소스 commit·전체 증거 재대조 후 공개 성공 |
| [업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/38682984544) | success, 이미 발행한 버전의 Linux/Windows 빌드와 릴리즈 작업을 정상 생략 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r1) | 다섯 자산 공개, prerelease=false, Latest 확인 |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r1/build-manifest.json) | 전체 소스·의존성·옵션·툴체인·실행 증거 포함 |

빌드 소스 commit은 `5459db1fed9f85b37949825a84bc4b569cfcbe14`이며 릴리즈 태그도 이 commit을
가리킵니다. 발행 제어 코드는 main에서 draft 조회 처리를 수정한 뒤 검증된 원본 파일을
그대로 재검증·발행했습니다. 최초 빌드 run의 전체 상태는 발행 API 단계 실패 때문에 failure로
남아 있지만 빌드/실행/게이트 성공 증거는 변경하지 않았습니다. 발행 재개 run은 success입니다.

고객사 실제 Windows Server 2022 설치 환경과 별도 Linux 호스트 커널, 운영 서비스,
부하 검증은 GitHub Runner/컨테이너 실행과 구분합니다.

ARM64를 포함한 모든 필수 빌드·실행·릴리즈 검증을 통과했습니다. 이후 버전도 동일한
전체 검증을 통과해야만 발행합니다. 필수 플랫폼 검증을 생략하거나 실패를 무시하지 않습니다.
