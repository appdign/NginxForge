# 별도 참고 구성

이 디렉터리의 이전 r8 예시와 테스트는 운영 conf에 자동 복사/로드하지 않습니다.
현재 운영 구성은 config/runtime의 분할 정책과 별도 config/site-template.conf를 사용합니다.
사이트 도메인/출처/API/backend는 site.conf에서만 설정하고 정책은 개별 include로 선택합니다.
이전 예시는 현재 구조와 함께 include하지 않습니다.
