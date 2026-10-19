# 설치

GitHub Releases에서 서버 CPU에 맞는 파일과 `SHA256SUMS.txt`를 받습니다.
Linux `uname -m`이 `x86_64`이면 amd64, `aarch64`이면 arm64입니다.
AMD64/ARM64 패키지는 서로 교환할 수 없습니다.

## Linux

다음은 새 설치 예시입니다. 패키지 관리자의 NGINX를 덮어쓰지 않습니다.
다운로드 파일의 실제 버전으로 명령을 바꾸세요.

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
tar -xzf nginxforge-<version>-linux-<arch>.tar.gz
sudo install -d /opt/nginxforge/{sbin,conf,logs,html,temp}
sudo install -m 755 nginx /opt/nginxforge/sbin/nginx
# conf는 새 설치에만 복사합니다. 기존 설정을 덮어쓰지 마세요.
sudo cp -R conf/. /opt/nginxforge/conf/
sudo cp -R html/. /opt/nginxforge/html/
sudo /opt/nginxforge/sbin/nginx -t
sudo /opt/nginxforge/sbin/nginx
```

기본 prefix는 `/opt/nginxforge`, 설정은 `conf/nginx.conf`입니다. `-p`와 `-c`로
고정 경로를 명시할 수 있습니다. 새 설치의 8080 포트는 127.0.0.1에서만 수신합니다.
운영 HTTPS는 [보안 설정 문서](SECURITY-CONFIG.md)를 따라 실제 도메인·인증서를 넣어
통합 사이트 conf/conf.d/site.conf.example 하나를 site.conf로 활성화합니다. 옵션별 파일을
선택하거나 보안 include 주석을 해제할 필요가 없습니다. 샘플 포함만으로 보안 점검이
완료되는 것은 아닙니다. 기존 nginx.conf는 자동 변경하지 않습니다.
프로세스 사용자에게 로그·temp 디렉터리 권한을 부여하고,
운영에서는 전용 비특권 사용자와 조직의 systemd/SELinux 정책을 적용하세요.
root로 기동할 때의 기본 worker 계정은 두 Linux 배포판에 공통으로 존재하는 `daemon:daemon`입니다.
운영 전용 계정을 만들었다면 기존 설정의 `user <사용자> <그룹>;`으로 명시하세요.
기존의 명시적 user 설정은 이 빌드 기본값보다 우선합니다. 비특권 계정으로 직접 기동하면
현재 계정을 사용합니다.
HTTPS 인증서와 키는 별도로 관리합니다. 컨테이너·컴파일러·추가 libc 설치는 필요하지 않습니다.

## Windows Server 2022 AMD64

```powershell
$expected = ((Get-Content .\SHA256SUMS.txt | Where-Object { $_ -match 'windows-amd64\.zip$' }) -split '\s+')[0]
$actual = (Get-FileHash .\nginxforge-<version>-windows-amd64.zip -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw 'SHA256 mismatch' }
Expand-Archive .\nginxforge-<version>-windows-amd64.zip C:\nginxforge
Set-Location C:\nginxforge
.\nginx.exe -p C:/nginxforge/ -c conf/nginx.conf -t
Start-Process .\nginx.exe -ArgumentList '-p','C:/nginxforge/','-c','conf/nginx.conf' -WindowStyle Hidden
```

고객사에는 WSL·Docker·Hyper-V·MSYS2·컴파일러가 필요하지 않습니다.
nginx.exe 외에 설정, 인증서, 로그·temp 디렉터리는 필요합니다. 경로는 `/` 구분자를 권장합니다.
NGINX/Windows의 upstream 연결 처리·워커·서비스 제한을 유지하며 Windows 서비스 래퍼는
포함하지 않습니다. 기존 서비스의 실행 계정·작업 디렉터리·권한을 따로 확인하세요.
