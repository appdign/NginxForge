# 보안 조치의 담당 범위

원칙은 **NGINX로 처리 가능한 공통 HTTP 정책은 NGINX에 모으고, 애플리케이션
프롬프트에는 코드로 처리해야 하는 결함만 남기는 것**입니다. 프레임워크나 OS 설정으로
해결하는 항목도 코드 목록에서 분리하지만, NGINX 기능으로 잘못 분류하지 않습니다.

| 담당 | 항목 | 구현/설정 위치 |
| --- | --- | --- |
| NGINX 공통 기반 | 로그·MIME·공유 TLS·헤더 상속 | conf/nginx.conf. 도메인/backend 없음 |
| NGINX 공통 보안 | 고정 보안 헤더·정보 노출 방지·위험 파일/관리 경로 차단 | conf/policy.conf. 도메인/backend 없음 |
| 사이트 정책 | 도메인·인증서·root·CSP·CORS/WS 출처·proxy_pass·쿠키·오류·제한·timeout | conf/site.conf 한 파일. vhost별 독립 선택 |
| 프론트 코드 | 안전한 출력/HTML 처리, URL/메시지 검증, 인증정보·계정 전환 상태 처리, CSRF 프로토콜 연동 | [프론트 코드 프롬프트](https://github.com/appdign/NginxForge/blob/main/docs/prompts/FRONTEND-CODE-REVIEW.md) |
| Spring Boot 코드 | 데이터별 인가, DTO/쿼리/파일/외부 URL 처리, 업무 할당량·일회성 토큰·오류/감사 로직 | [백엔드 코드 프롬프트](https://github.com/appdign/NginxForge/blob/main/docs/prompts/SPRING-BOOT-CODE-REVIEW.md) |
| Spring/인증 서버 설정 | 인증 필터 체인, 표준 JWT 검증, 세션 TTL/폐기 정책, 비밀번호 해시 정책, Actuator 노출, multipart 파일 50 MiB/요청 1 GiB·Tomcat 폼 5 MiB | 앱 프레임워크/IdP 구성. [업로드 설정 예시](https://github.com/appdign/NginxForge/blob/main/docs/backend/application-upload.yml.example). Java 설정도 포함 |
| 운영 설정 | OS/DB 계정·ACL, Windows 링크, 방화벽·backend 직접 접근, 비밀값 주입·인증서·로그 회전·패치 | 배포/운영 담당 |

코드와 설정은 파일 확장자로 구분하지 않습니다. 예를 들어 `SecurityFilterChain`을
정의하는 Java 코드는 주로 프레임워크 정책 설정이고, 서비스에서 파일 소유자를 검사하는
코드는 업무 인가입니다. 설정으로 해결되는 문제는 프롬프트 결과의 별도 설정 표로 보냅니다.

## NGINX가 대신하지 않는 부분

- CORS/IP 제한은 사용자 인증·객체 소유권 검사·CSRF 토큰 검증을 대체하지 않습니다.
- CSP는 코드의 XSS를 제거하지 않습니다. 앱 inline/eval 개선, SSR nonce/hash 연동이
  실제로 필요하면 그 연동 코드만 프론트/SSR 작업으로 남깁니다.
- `proxy_cookie_flags`는 backend가 **이미 Set-Cookie로 발급한** 지정 쿠키의 응답 플래그를
  바꿉니다. JS localStorage의 토큰을 HttpOnly 쿠키로 옮기거나 세션을 발급/폐기하지 않습니다.
- 요청 본문 크기/IP 빈도 제한은 파일 내용·해제 후 크기·계정별 저장 용량·다운로드 총량을
  검사하지 않습니다. IP 제한만으로 계정별 로그인 남용 제어가 완료되지 않습니다.
- 오류 페이지 가림은 API 오류 형식에 영향을 줄 수 있고, 200 응답이나 앱 로그에 이미 섞인
  비밀정보를 안전하게 제거하지 않습니다.
- 외부에서 Actuator 경로를 막아도 직접 backend 포트/별도 관리 포트의 노출과 권한은
  Spring/네트워크 설정으로 확인해야 합니다. NGINX가 Spring 의존성을 업데이트하지 않습니다.

NGINX를 반드시 거치는 트래픽 경계를 먼저 확정합니다. 별도 hostname, 포트, IPv6,
관리 리스너나 내부 직접 접근으로 우회되는 경우에는 해당 설정의 보호가 적용되지 않습니다.

## 배포와 판정

운영 설정은 nginx.conf·policy.conf·site.conf·mime.types 네 파일로 제공합니다.
모든 사이트별 선택값은 site.conf 안에서 조정하고 policy.conf는 수정하지 않습니다.
예제·backend YAML·코드 프롬프트는 별도 참고 자료로 분리합니다. 공개 초기 설정은
요청을 거부하므로 실제 site.conf를 설치합니다. 완화/해제한 통제를 적용 완료로 판정하지 않습니다.
설치 절차와 헤더 상속 주의사항은 [보안 설정 안내](SECURITY-CONFIG.md)에 있습니다.
프론트/백엔드 코드 수정, 프레임워크 설정, 운영 설정과 실제 NGINX 활성화 상태를
각각 기록합니다. 이 분류는 KISA 26개 항목을 계층별 26개씩 나누거나 자동 합격시키는 기준이 아닙니다.
