<#
.SYNOPSIS
  Phase 4 Increment 1: 本番サービング（ingest/viewer + Redis）をこのWindows機に
  ネイティブ・サービスとして構築する。冪等（再実行可）。**管理者PowerShellで実行**。

.DESCRIPTION
  設計は _docs/deployment/windows-service-setup.md を参照。処理:
   1. 前提確認（管理者/psql/python/既存Postgresサービス）
   2. Memurai(Redis互換) と Shawl(サービスラッパー) を winget 導入
   3. ネイティブPostgres(5432)に role=plc_user / db=plc_monitor を作成（パスワード生成）
   4. マイグレーション適用（flask db upgrade）
   5. admin/APIキーを生成して seed
   6. C:\ProgramData\plc-monitor\.env を生成（ACLで管理者のみ読取）
   7. plc-ingest / plc-viewer を Shawl でサービス登録（依存順・自動起動・自動再起動）
   8. サービス起動

  生成した認証情報（adminパスワード・APIキー）は最後に表示する。控えること。

.PARAMETER PgSuperPassword
  既存ネイティブPostgresの superuser(postgres) パスワード。role/db 作成に使う（必須）。

.EXAMPLE
  # 管理者PowerShellで:
  cd <repo>\plc-dashboard\scripts\windows-service
  .\setup-all.ps1 -PgSuperPassword '＜postgresのパスワード＞'
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PgSuperPassword,
  [string]$PgSuperUser = 'postgres',
  [int]$PgPort = 5432,
  [string]$BindHost = '0.0.0.0',
  [int]$IngestPort = 5000,
  [int]$ViewerPort = 5001,
  [string]$PythonExe = '',
  [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
function Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ OK ] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }

function New-Secret([int]$len = 28) {
  $chars = (48..57) + (65..90) + (97..122)   # 0-9 A-Z a-z（記号は.envや接続URLの取り回しを避け英数のみ）
  -join ($chars | Get-Random -Count $len | ForEach-Object { [char]$_ })
}

# ---- パス解決 ----
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path      # plc-dashboard
$backend = Join-Path $repo 'backend'
$frontendDist = Join-Path $repo '.output\public'
$progData = 'C:\ProgramData\plc-monitor'
$logDir = Join-Path $progData 'logs'
$envFile = Join-Path $progData '.env'

Info "repo(plc-dashboard) = $repo"

# ---- 1. 前提確認 ----
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Die '管理者権限で実行してください（右クリック→管理者としてPowerShell）。' }
Ok '管理者権限を確認'

if (-not (Get-Service 'postgresql-x64-18' -ErrorAction SilentlyContinue)) {
  Warn 'postgresql-x64-18 サービスが見つかりません。別バージョンなら -PgPort 等を調整してください。'
}

# psql 検出
$psql = (Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1).FullName
if (-not $psql) { Die 'psql.exe が見つかりません（C:\Program Files\PostgreSQL\*\bin）。' }
Ok "psql = $psql"

# python 検出
if (-not $PythonExe) {
  $pc = Get-Command python -ErrorAction SilentlyContinue
  if ($pc) { $PythonExe = $pc.Source }
  elseif (Test-Path 'C:\Users\tonto\AppData\Local\Programs\Python\Python312\python.exe') {
    $PythonExe = 'C:\Users\tonto\AppData\Local\Programs\Python\Python312\python.exe'
  }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) { Die 'python.exe が見つかりません。-PythonExe で明示してください。' }
Ok "python = $PythonExe"

# backend依存の存在確認
& $PythonExe -c "import flask, waitress, redis, psycopg2, flask_socketio, flask_migrate" 2>$null
if ($LASTEXITCODE -ne 0) { Die "backend依存が $PythonExe に無い。`n  cd $backend; & '$PythonExe' -m pip install -r requirements.txt を先に実行してください。" }
Ok 'backend依存を確認'

# ---- 2. Memurai / Shawl 導入 ----
if ($SkipInstall) {
  Info 'インストールをスキップ（-SkipInstall）'
} else {
  if (Get-Service 'Memurai' -ErrorAction SilentlyContinue) {
    Ok 'Memurai は既に導入済み'
  } else {
    Info 'Memurai Developer を winget 導入中...'
    winget install --id Memurai.MemuraiDeveloper -e --accept-package-agreements --accept-source-agreements
    if (-not (Get-Service 'Memurai' -ErrorAction SilentlyContinue)) { Warn 'Memuraiサービスが未検出。winget出力を確認してください。' } else { Ok 'Memurai 導入完了' }
  }
  Info 'Shawl を winget 導入中...'
  winget install --id mtkennerly.shawl -e --accept-package-agreements --accept-source-agreements
}

# shawl.exe 検出（PATH未反映のことがあるので実体を探す）
$shawl = (Get-Command shawl -ErrorAction SilentlyContinue).Source
if (-not $shawl) {
  $cand = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\mtkennerly.shawl*\shawl.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($cand) { $shawl = $cand.FullName }
}
if (-not $shawl) { Die 'shawl.exe が見つかりません。新しい管理者PowerShellを開き -SkipInstall で再実行してください（PATH反映のため）。' }
Ok "shawl = $shawl"

# Memurai(6379) 起動確認
Start-Service 'Memurai' -ErrorAction SilentlyContinue
Ok 'Memurai を起動（既に起動済みなら無視）'

# ---- 3. Postgres role/db ----
$env:PGPASSWORD = $PgSuperPassword
function Psql($sql, $db = 'postgres') {
  & $psql -U $PgSuperUser -h 127.0.0.1 -p $PgPort -d $db -tAc $sql
}
$roleExists = (Psql "SELECT 1 FROM pg_roles WHERE rolname='plc_user'").Trim()
if ($roleExists -eq '1') {
  Ok 'role plc_user は既に存在（パスワードは既存の.envを踏襲）'
  $pgPass = $null   # 既存なら後で.envから読む
} else {
  $pgPass = New-Secret 24
  Psql "CREATE ROLE plc_user LOGIN PASSWORD '$pgPass'" | Out-Null
  Ok 'role plc_user を作成'
}
$dbExists = (Psql "SELECT 1 FROM pg_database WHERE datname='plc_monitor'").Trim()
if ($dbExists -eq '1') {
  Ok 'db plc_monitor は既に存在'
} else {
  Psql "CREATE DATABASE plc_monitor OWNER plc_user ENCODING 'UTF8'" | Out-Null
  Ok 'db plc_monitor を作成（UTF8）'
}

# 既存role時: .envからパスワードを引き継ぐ（無ければ再設定）
if (-not $pgPass) {
  if (Test-Path $envFile) {
    $line = Select-String -Path $envFile -Pattern 'DATABASE_URL=' | Select-Object -First 1
    if ($line -and $line.Line -match 'plc_user:([^@]+)@') { $pgPass = $matches[1] }
  }
  if (-not $pgPass) {
    $pgPass = New-Secret 24
    Psql "ALTER ROLE plc_user PASSWORD '$pgPass'" | Out-Null
    Warn '既存roleのパスワードを再生成しました（.envを更新します）'
  }
}
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

$databaseUrl = "postgresql+psycopg2://plc_user:$pgPass@127.0.0.1:$PgPort/plc_monitor"

# ---- 4. マイグレーション ----
Info 'マイグレーション適用中（flask db upgrade）...'
Push-Location $backend
$env:DATABASE_URL = $databaseUrl
& $PythonExe -m flask --app manage.py db upgrade
if ($LASTEXITCODE -ne 0) { Pop-Location; Die 'マイグレーションに失敗' }
Ok 'マイグレーション適用完了'

# ---- 5. seed（admin/APIキー生成） ----
$adminPw = New-Secret 20
$apiKey = New-Secret 32
& $PythonExe -m flask --app manage.py auth seed --admin-password $adminPw --api-key $apiKey
if ($LASTEXITCODE -ne 0) { Pop-Location; Die 'auth seed に失敗' }
Ok 'admin/APIキーを seed'
Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
Pop-Location

# ---- 6. .env 生成（ACL） ----
New-Item -ItemType Directory -Force -Path $progData | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$secretKey = New-Secret 48
$envContent = @"
# plc-monitor 本番サービング設定（Phase 4 Increment 1・自動生成）
# 生成: setup-all.ps1。手編集可。サービスは serve_production.py がこれを読み込む。
SECRET_KEY=$secretKey
DATABASE_URL=$databaseUrl
SOCKETIO_MESSAGE_QUEUE=redis://127.0.0.1:6379/0
CORS_ORIGINS=http://127.0.0.1:$ViewerPort
FRONTEND_DIST=$frontendDist
HOST=$BindHost
"@
Set-Content -Path $envFile -Value $envContent -Encoding utf8
# ACL: 継承を切り、Administrators と SYSTEM のみに絞る
icacls $envFile /inheritance:r | Out-Null
icacls $envFile /grant:r "*S-1-5-32-544:(R)" "*S-1-5-18:(R)" | Out-Null
Ok ".env を生成（$envFile・管理者/SYSTEMのみ読取）"

# ---- 7. サービス登録（Shawl） ----
function Register-Service($name, $role, $port) {
  if (Get-Service $name -ErrorAction SilentlyContinue) {
    Info "$name は既存 → 停止して再登録"
    Stop-Service $name -Force -ErrorAction SilentlyContinue
    & $shawl remove --name $name | Out-Null
  }
  & $shawl add --name $name --cwd $backend --log-dir $logDir --restart -- `
      $PythonExe serve_production.py --role $role --port $port
  if ($LASTEXITCODE -ne 0) { Die "$name のShawl登録に失敗" }
  # 依存順（postgres→memurai→本サービス）と自動起動
  & sc.exe config $name depend= postgresql-x64-18/Memurai | Out-Null
  & sc.exe config $name start= auto | Out-Null
  Ok "$name を登録（role=$role port=$port 自動起動・自動再起動）"
}
Register-Service 'plc-ingest' 'ingest' $IngestPort
Register-Service 'plc-viewer' 'viewer' $ViewerPort

# ---- 8. 起動 ----
Start-Service 'plc-ingest'
Start-Service 'plc-viewer'
Start-Sleep -Seconds 3
Get-Service 'Memurai','plc-ingest','plc-viewer' | Format-Table Name, Status, StartType -AutoSize

Write-Host ""
Write-Host "==================== 生成された認証情報（控えること）====================" -ForegroundColor Magenta
Write-Host "  admin パスワード : $adminPw"
Write-Host "  エージェントAPIキー: $apiKey"
Write-Host "  .env             : $envFile"
Write-Host "  ログ             : $logDir"
Write-Host "========================================================================" -ForegroundColor Magenta
Write-Host ""
Ok '完了。次に verify（配信到達）を確認します。出力をそのまま貼り付けてください。'
