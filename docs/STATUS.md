# 완료 기준과 실제 검증 상태

현재는 초기 구현 단계입니다. 아래 항목은 실제 GitHub Actions 및 Releases 결과 확인 전까지 미완료입니다.

- [ ] Linux AMD64 musl 완전 정적 빌드
- [ ] Linux ARM64 musl 완전 정적 빌드
- [ ] Ubuntu 22.04/24.04 AMD64 실행
- [ ] Ubuntu 22.04/24.04 ARM64 실행
- [ ] Rocky Linux 8/9 AMD64 실행
- [ ] Rocky Linux 8/9 ARM64 실행
- [ ] Windows Server 2022 Runner AMD64 실행
- [ ] 세 바이너리 공통 보안 기능 테스트
- [ ] 공식 최신 버전 감지와 중복 발행 방지
- [ ] GitHub Releases 다섯 파일 자동 발행
- [ ] 전체 성공 후 Latest 지정

고객사 실제 Windows Server 2022 설치 환경과 별도 Linux 호스트 커널, 운영 서비스,
부하 검증은 GitHub Runner/컨테이너 실행과 구분합니다.

ARM64를 포함한 모든 필수 빌드·실행·릴리즈 검증 완료 전까지 프로젝트 완료를 선언하지 않습니다.
