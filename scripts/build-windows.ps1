$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-Checked([scriptblock] $Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}
# Use the native MSVC environment. No compiler/runtime is required on customer hosts.
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$installation = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $installation) { throw 'MSVC x64 tools not found' }
$devcmd = Join-Path $installation 'Common7\Tools\VsDevCmd.bat'
$environment = & $env:ComSpec /d /s /c "`"$devcmd`" -no_logo -arch=x64 -host_arch=x64 >nul && set"
if ($LASTEXITCODE -ne 0) { throw 'Could not initialize MSVC' }
foreach ($line in $environment) {
    if ($line -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
$gitBash = 'C:\Program Files\Git\bin\bash.exe'
if (-not (Test-Path -LiteralPath $gitBash)) { throw 'Git for Windows bash not found' }
if (-not (Get-Command perl -ErrorAction SilentlyContinue)) { throw 'Native Perl required for OpenSSL' }
Invoke-Checked { python scripts/fetch-sources.py }
Invoke-Checked { python scripts/apply-patches.py }
$env:MSYS_NO_PATHCONV = '1'
Invoke-Checked { & $gitBash scripts/configure-windows.sh }
Push-Location build/src/nginx
try { Invoke-Checked { nmake /nologo } } finally { Pop-Location }
Invoke-Checked { python scripts/package-release.py --plan build/plan.json --target windows-amd64 --binary build/src/nginx/objs/nginx.exe --options build/configure-options.txt }
