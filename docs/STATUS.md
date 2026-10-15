# 완료 기준과 실제 검증 상태

2026-10-15 검증 결과: **NGINX 1.30.6 / NginxForge r2 정식 발행 및 Latest 지정 완료**.
KISA 2026 보안 설정과 도메인 샘플을 포함한 실제 배포 압축파일로 검증했습니다.

- [x] Linux AMD64 musl 완전 정적 빌드
- [x] Linux ARM64 musl 완전 정적 빌드
- [x] Ubuntu 22.04/24.04 AMD64 실행
- [x] Ubuntu 22.04/24.04 ARM64 실행
- [x] Rocky Linux 8/9 AMD64 실행
- [x] Rocky Linux 8/9 ARM64 실행
- [x] Windows Server 2022 Runner AMD64 실행 (build 20348)
- [x] 세 바이너리 공통 보안 기능 테스트
- [x] 배포된 nginx.conf와 정적 사이트·리버스 프록시 도메인 샘플 실행
- [x] 공식 최신 버전 감지
- [x] 발행 후 재조회에서 중복 빌드·배포 생략 확인
- [x] GitHub Releases 다섯 파일 자동 발행
- [x] 전체 성공 후 Latest 지정
- [x] 공개된 다섯 파일 재다운로드 후 무결성 및 포함 설정 검증

각 OS/CPU 조합에서 64개 실행 검사, 총 **576개**가 통과했습니다. 릴리즈 제어 로직의
28개 단위 테스트도 통과했습니다. Linux 바이너리 두 개는 ELF64의 PT_INTERP 및
외부 DSO 의존성 부재를 확인했고 Windows는 AMD64 PE 및 정적 CRT/시스템 DLL 의존성을 확인했습니다.

추가된 설정 검사는 HTTPS 이동, 알 수 없는 Host/SNI 차단, 정상/오류 응답의 보안 헤더,
목록·비밀 파일·스크립트·경로 이탈 요청 차단, 허용 메소드, 5 MiB 요청 크기 제한,
고정 프록시와 전달 헤더 재작성, 선택 세션 쿠키 플래그, 업스트림 오류 정보 가림,
업로드 경로·관리자 IP 접근 제한, TLS 1.2/1.3와 요청 빈도 제한을 확인합니다.
Linux는 실제 심볼릭 링크 접근 차단도 검사합니다. Windows의 링크 관련 검사는
지원하지 않는 NGINX 지시문을 넣지 않고 OS 권한 검토 필요성을 명시했는지 확인하는 것으로,
고객사 NTFS 링크/ACL 통제가 자동 검증됐다는 의미가 아닙니다.

| 증거 | 결과 |
| --- | --- |
| [빌드·실행·게이트·자동 발행](https://github.com/appdign/NginxForge/actions/runs/38685349446) | 전체 workflow success, 세 바이너리와 9개 OS/CPU 조합의 576개 실행 검사 통과 |
| [업스트림 재조회](https://github.com/appdign/NginxForge/actions/runs/38720658492) | 이미 발행한 r2의 중복 빌드·배포 생략 검증 |
| [정식 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r2) | 다섯 자산 공개, draft=false, prerelease=false, Latest 확인 |
| [검증 manifest](https://github.com/appdign/NginxForge/releases/download/v1.30.6-r2/build-manifest.json) | 공통 소스·의존성·옵션·툴체인·설정 해시·전체 실행 증거 포함 |
| [보안 설정 안내](SECURITY-CONFIG.md) | nginx.conf, 도메인 샘플 활성화 절차와 KISA 2026 WEB-01~26 적용 범위 |

빌드 소스와 릴리즈 태그 commit은 `bf0995ab0f7ea16775712c4c4f5928581c9806f1`입니다.
공개된 파일 다섯 개를 다시 내려받아 GitHub 자산 SHA-256과 크기를 대조했으며,
SHA256SUMS.txt의 네 파일 해시와 각 압축파일의 설정 해시를 모두 확인했습니다.
세 패키지에 nginx.conf, 비활성 도메인 샘플, 보안 안내와 26개 항목 대응표가 포함되어 있고,
실제 인증서·개인키·비밀번호 파일 및 테스트 fixture는 포함되지 않습니다.

KISA 공식 2026 웹 서비스 기준은 26개 항목이며 이 결과는 **26개 점검 항목의 자동 합격이나
인증을 뜻하지 않습니다**. 기존 headers-more 정적 모듈과 NGINX 기본 기능으로 제공하는
서버 조치를 문서화했습니다. 계정·비밀번호 정책, OS 파일/로그 권한, Windows 링크 통제,
인증서 운영, 앱 인증·인가·업로드 저장소·다운로드 총량 등은 실제 환경에서 별도로 점검해야 합니다.

고객사 실제 Windows Server 2022 설치 환경과 별도 Linux 호스트 커널, 운영 서비스,
부하 검증은 GitHub Runner/컨테이너 실행과 구분합니다.

ARM64를 포함한 모든 필수 빌드·실행·릴리즈 검증을 통과했습니다. 이후 버전도 동일한
전체 검증을 통과해야만 발행합니다. 필수 플랫폼 검증을 생략하거나 실패를 무시하지 않습니다.

## 이전 릴리즈 기록

r1은 [최초 빌드와 360개 실행 검사](https://github.com/appdign/NginxForge/actions/runs/38661867375)를
통과했습니다. 최초 발행 API 단계의 draft 조회 실패는 main에서 수정한 뒤
[원본 산출물 재검증·발행](https://github.com/appdign/NginxForge/actions/runs/38682918382)으로
완료했습니다. [r1 릴리즈](https://github.com/appdign/NginxForge/releases/tag/v1.30.6-r1)와
그 바이너리·태그는 변경하지 않았습니다.
