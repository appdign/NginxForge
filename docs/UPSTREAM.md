# 업스트림과 릴리즈 정책

공식 [NGINX 다운로드](https://nginx.org/en/download.html)의 Stable/Mainline 구역에서
최신 버전을 결정하고 [공식 저장소](https://github.com/nginx/nginx)의 릴리즈 태그를
검증합니다. 태그를 불변 commit으로 해석하고 소스 내부의 `NGINX_VERSION`도 대조합니다.
서드파티는 고정 태그/커밋과 SHA-256으로 다운로드하며 전체 소스를 저장소에 복사하지 않습니다.

매일 UTC 00:00(한국시간 09:00경)에 검사합니다. GitHub 스케줄은 지연·누락될 수 있습니다.
검사는 직전 실행 시간에 의존하지 않고 현재 최신 버전과 Releases를 비교하므로 다음 실행에서
미발행 최신 버전을 감지합니다. 놓친 중간 버전을 모두 자동 발행하지는 않습니다.
과거 버전이 필요하면 수동 version으로 지정할 수 있습니다. 조회/네트워크/권한/레이트 제한
오류는 실패로 처리하고 '신규 버전 없음'으로 숨기지 않습니다.

`revision`은 NginxForge 자체 빌드 리비전이며 NGINX 버전과 구분합니다. 같은 upstream의
패치·의존성을 바꾸어 발행하려면 revision을 증가시킵니다. 이미 공개한 태그와 파일은
덮어쓰지 않습니다. `rebuild=true`는 같은 버전의 재검증을 허용하고 기존 정식 릴리즈를
변경하지 않습니다. 빌드 관련 main 변경은 자동으로 재검증합니다.

전체 Linux/Windows 작업 성공 후에만 릴리즈 게이트를 실행합니다. 8개 Linux 조합 또는
Windows 검증 중 하나라도 실패·누락되면 모든 플랫폼의 정식 배포를 중단합니다.
통과 후 다섯 자산을 draft에 올려 다시 다운로드해 SHA-256을 대조한 뒤 공개합니다.
실패 시 기존 Latest를 유지하며 업로드 실패는 draft 상태에 남습니다.
동일 소스 commit의 draft만 재개할 수 있습니다. 다른 소스이면 revision을 올립니다.

빌드·검증이 성공하고 업로드/발행만 실패한 경우 Actions의 **Resume verified publication**에
원래 run ID를 지정할 수 있습니다. 이 작업은 같은 저장소의 완료된 release workflow에서
실제로 전체 게이트가 성공했는지 확인합니다. `verified-release` artifact의 원래 소스 commit,
9개 증거, 바이너리 및 패키지 해시를 다시 검증하고 재생성 결과가 원본과 바이트 단위로
같을 때만 발행합니다. 현재 build config/patch/의존성이 원래 계획과 달라졌으면 거부합니다.
새로 빌드하거나 기존 결과를 다른 소스 commit의 결과로 바꾸지 않습니다.
draft는 태그별 조회 API에서 404가 될 수 있으므로 전체 Releases 목록에서 찾아 ID로 조회합니다.

Stable의 전체 통과 릴리즈만 Latest 후보입니다. 과거 버전의 수동 빌드가 더 최신인
기존 Latest를 내리지 않도록 숫자 버전/리비전을 비교합니다. Mainline은 prerelease로
발행하고 Latest로 지정하지 않습니다. 동시 발행은 저장소 단위 concurrency로 직렬화합니다.
빌드 작업의 토큰은 읽기 전용이며 릴리즈 작업에만 `contents: write`를 부여합니다.

외부 의존성·도구·Runner 이미지 갱신도 반드시 두 CPU를 동시에 검증합니다.
컴파일 경고를 무시하거나 필수 테스트를 skip/continue-on-error로 통과시키지 않습니다.
