# 업데이트와 롤백

기존 NGINX의 `-V` 출력, 바이너리 경로, prefix, 설정 경로, 로그·pid·temp 경로,
실행 계정과 동적 모듈을 먼저 기록하세요. 패키지 관리자 설치본을 무조건 덮어쓰지 않습니다.
본 빌드에 없는 모듈 지시문이나 `load_module`이 있으면 교체 전에 호환성을 해결합니다.

1. 새 패키지와 manifest의 CPU·운영체제·업스트림 버전을 확인하고 SHA-256을 검증합니다.
2. 기존 실행 파일, 설정, 서비스 실행 인수와 인증서 위치를 백업합니다. 인증서 키의 접근 권한을 유지합니다.
3. 새 바이너리를 별도 staging 디렉터리에 풀고 기존의 **동일한 `-p`/`-c` 옵션**으로 `-t`를 실행합니다.
4. 정상 종료하고 기존 파일을 보관한 뒤 실행 파일만 교체합니다. 기존 설정·인증서·로그를 덮어쓰지 않습니다.
5. 교체 파일로 `-t`를 재검사하고 기존 서비스 방식으로 시작합니다. HTTP·HTTPS 및 실제 프록시 health check를 확인합니다.
6. 설정 검사·시작·health check가 실패하면 새 프로세스를 종료하고 백업 바이너리와 원래 실행 인수로 되돌립니다.

## Linux의 정지 후 안전한 교체 예시

아래 경로는 `/opt/nginxforge` 새 설치 기준입니다. 검증한 staging 파일을 사용하세요.

```bash
sudo /path/to/staging/nginx -p /opt/nginxforge/ -c conf/nginx.conf -t
sudo cp -p /opt/nginxforge/sbin/nginx /opt/nginxforge/sbin/nginx.previous
sudo /opt/nginxforge/sbin/nginx -p /opt/nginxforge/ -c conf/nginx.conf -s quit
# pid가 종료되고 리스너가 해제된 것을 확인한 다음:
sudo install -m 755 /path/to/staging/nginx /opt/nginxforge/sbin/nginx.new
sudo mv /opt/nginxforge/sbin/nginx.new /opt/nginxforge/sbin/nginx
sudo /opt/nginxforge/sbin/nginx -p /opt/nginxforge/ -c conf/nginx.conf -t
sudo /opt/nginxforge/sbin/nginx -p /opt/nginxforge/ -c conf/nginx.conf
# 실패하면 종료 후 nginx.previous를 원래 위치에 복구하고 검사·시작합니다.
```

운영 서비스 관리자가 프로세스를 제어한다면 해당 서비스 관리 절차를 사용합니다.
실행 중인 파일을 직접 덮어쓰지 않고 동일 파일시스템 내 rename을 사용합니다.

## Linux 무중단 바이너리 업그레이드

[NGINX 공식 절차](https://nginx.org/en/docs/control.html#upgrade)를 따릅니다.
기존 master 프로세스가 있어야 하며 `master_process off`인 테스트 구성에는 적용하지 않습니다.

1. 새 바이너리로 기존 설정의 `-t`를 통과시키고 기존 바이너리를 보관한 뒤 원래 실행 파일 경로를 원자적으로 교체합니다.
2. 현재 master PID에 `USR2`를 보냅니다. 이전 master PID는 pid 파일의 `.oldbin`에 기록되고 새 master/worker가 시작됩니다.
3. 새 PID, 로그, 리스너와 실제 요청을 확인한 다음 이전 master에 `WINCH`를 보내 기존 worker를 graceful 종료합니다.
4. 새 worker의 정상 처리를 확인한 뒤 이전 master에 `QUIT`을 보냅니다.
5. 실패하면 이전 master에 `HUP`을 보내 기존 worker를 다시 시작하고 새 master에 `QUIT`을 보냅니다.
   보관한 바이너리를 복구하고 pid·리스너 상태를 다시 확인합니다.

실제 PID를 확인하여 신호를 보내며, 이 저장소는 운영 서버에 신호를 자동 전송하지 않습니다.

## Windows

파일이 실행 중이면 교체할 수 없습니다. 새 nginx.exe로 기존 prefix/설정에 대한 `-t`를
수행하고 백업 후 `nginx.exe -s quit`으로 종료합니다. 작업 관리자 또는 서비스 관리자로
master와 worker 종료를 확인한 다음 교체·`-t`·시작·health check를 수행합니다.
실패 시 정상 종료 후 백업 nginx.exe를 복원합니다. 기존 서비스 계정, 작업 디렉터리,
인증서와 디렉터리 ACL을 유지합니다. Linux의 USR2 절차를 Windows에 적용하지 않습니다.
