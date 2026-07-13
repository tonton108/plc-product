<#
.SYNOPSIS
  Phase 4 Increment 1 のロールバック。**管理者PowerShellで実行**。
.DESCRIPTION
  plc-ingest / plc-viewer サービスを停止・削除する。既定ではMemurai/Shawl/DBは残す
  （-Full で Memurai/Shawl の winget アンインストールと plc_monitor DB 削除も行う）。
.EXAMPLE
  .\uninstall.ps1                 # サービスのみ削除
  .\uninstall.ps1 -Full -PgSuperPassword 'xxx'   # Memurai/Shawl/DBも撤去
#>
[CmdletBinding()]
param(
  [switch]$Full,
  [string]$PgSuperPassword = '',
  [int]$PgPort = 5432
)
$ErrorActionPreference = 'Continue'
function Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ OK ] $m" -ForegroundColor Green }

$shawl = (Get-Command shawl -ErrorAction SilentlyContinue).Source
if (-not $shawl) {
  $c = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\mtkennerly.shawl*\shawl.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($c) { $shawl = $c.FullName }
}

foreach ($n in 'plc-ingest', 'plc-viewer') {
  if (Get-Service $n -ErrorAction SilentlyContinue) {
    Stop-Service $n -Force -ErrorAction SilentlyContinue
    if ($shawl) { & $shawl remove --name $n | Out-Null } else { & sc.exe delete $n | Out-Null }
    Ok "$n を停止・削除"
  } else { Info "$n は未登録" }
}

if ($Full) {
  Info 'Memurai / Shawl を winget アンインストール'
  winget uninstall --id Memurai.MemuraiDeveloper -e 2>$null
  winget uninstall --id mtkennerly.shawl -e 2>$null
  if ($PgSuperPassword) {
    $env:PGPASSWORD = $PgSuperPassword
    $psql = (Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1).FullName
    if ($psql) {
      & $psql -U postgres -h 127.0.0.1 -p $PgPort -d postgres -tAc "DROP DATABASE IF EXISTS plc_monitor" | Out-Null
      & $psql -U postgres -h 127.0.0.1 -p $PgPort -d postgres -tAc "DROP ROLE IF EXISTS plc_user" | Out-Null
      Ok 'plc_monitor DB / plc_user role を削除'
    }
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
  }
  Info 'C:\ProgramData\plc-monitor は手動確認のうえ削除してください（.env・ログを含む）'
}
Ok 'ロールバック完了'
