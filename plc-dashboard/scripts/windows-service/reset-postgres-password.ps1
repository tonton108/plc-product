<#
.SYNOPSIS
  ネイティブPostgreSQLの superuser(postgres) パスワードを安全にリセットする。
  **管理者PowerShellで実行**。
.DESCRIPTION
  pg_hba.conf を一時的に trust（ローカルはパスワード不要）へ切替 → サービス再起動 →
  ALTER USER で新パスワード設定 → pg_hba.conf を必ず元に復元 → サービス再起動、を自動で行う。
  元の pg_hba.conf は .bak.<連番> として退避し、finally で確実に戻す。
.EXAMPLE
  .\reset-postgres-password.ps1 -NewPassword 'MyNewPass123'
  # 続いて: .\setup-all.ps1 -PgSuperPassword 'MyNewPass123' -SkipInstall
.NOTES
  NewPassword は英数字推奨（シングルクォート等を含めない。ALTER USER のSQL文字列を壊すため）。
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [string]$NewPassword,
  [string]$ServiceName = 'postgresql-x64-18',
  [int]$PgPort = 5432
)
$ErrorActionPreference = 'Stop'

function Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ OK ] $m" -ForegroundColor Green }
function Die($m)  { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }

# 0. 管理者確認
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
  ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) { Die '管理者権限が必要です。管理者PowerShellで実行してください。' }

# 1. パスワードにSQL文字列を壊す文字が無いか
if ($NewPassword -match "['``\\]") {
  Die 'NewPassword に クォート・バッククォート・バックスラッシュ を含めないでください（英数字推奨）。'
}

# 2. サービス存在確認 + データディレクトリ検出（binPath の -D から）
$svc = Get-Service $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) { Die "サービス $ServiceName が見つかりません。名前を確認してください（Get-Service *postgres*）。" }

$binPath = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName
if ($binPath -match '-D\s+"([^"]+)"') { $dataDir = $Matches[1] }
elseif ($binPath -match '-D\s+(\S+)') { $dataDir = $Matches[1] }
else { Die "データディレクトリを binPath から検出できません: $binPath" }
Info "データディレクトリ: $dataDir"

$hba = Join-Path $dataDir 'pg_hba.conf'
if (-not (Test-Path $hba)) { Die "pg_hba.conf が見つかりません: $hba" }

# 3. psql.exe を検出
$psql = (Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1).FullName
if (-not $psql) { Die 'psql.exe が見つかりません（C:\Program Files\PostgreSQL\*\bin）。' }

# 4. バックアップ（.bak.<連番>）— Date.now が使えない環境向けに連番で一意化
$i = 0
do { $bak = "$hba.bak.$i"; $i++ } while (Test-Path $bak)
Copy-Item $hba $bak -Force
Ok "pg_hba.conf を退避: $bak"

$restored = $false
try {
  # 5. 先頭に trust 行を差し込む（pg_hba は先頭一致優先。ローカルのみ trust）
  $orig = Get-Content $hba -Raw
  $trustBlock = @"
# --- TEMP (reset-postgres-password.ps1): ローカル接続を一時的に trust 化 ---
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
local   all             all                                     trust
# --- /TEMP ---

"@
  Set-Content -Path $hba -Value ($trustBlock + $orig) -Encoding ASCII
  Info 'pg_hba.conf を一時 trust 化しました'

  # 6. 反映（reload では認証方式変更が確実でないため再起動）
  Restart-Service $ServiceName -Force
  Start-Sleep -Seconds 2
  Ok "$ServiceName を再起動（trust 有効）"

  # 7. パスワード無しで接続してリセット
  Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
  $alter = "ALTER USER postgres PASSWORD '$NewPassword';"
  $out = & $psql -U postgres -h 127.0.0.1 -p $PgPort -d postgres -w -c $alter 2>&1
  if ($LASTEXITCODE -ne 0) { Die "ALTER USER に失敗:`n$out" }
  Ok 'postgres のパスワードを再設定しました'
}
finally {
  # 8. 必ず pg_hba.conf を元に戻す
  if (Test-Path $bak) {
    Copy-Item $bak $hba -Force
    $restored = $true
    Restart-Service $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Ok 'pg_hba.conf を元に戻し、サービスを再起動しました（trust 解除）'
  }
}
if (-not $restored) { Die "重大: pg_hba.conf の復元に失敗。手動で $bak を $hba に戻してください。" }

# 9. 新パスワードで検証
$env:PGPASSWORD = $NewPassword
$verify = & $psql -U postgres -h 127.0.0.1 -p $PgPort -d postgres -w -tAc 'SELECT 1' 2>&1
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
if ("$verify".Trim() -eq '1') {
  Ok '新パスワードで接続成功'
  Write-Host ''
  Write-Host '次のコマンドでセットアップを続行してください:' -ForegroundColor Yellow
  Write-Host "  .\setup-all.ps1 -PgSuperPassword '$NewPassword' -SkipInstall" -ForegroundColor Yellow
} else {
  Die "新パスワードでの接続検証に失敗:`n$verify"
}
