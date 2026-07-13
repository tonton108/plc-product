<#
.SYNOPSIS
  Phase 4 Increment 1 の基本ヘルスチェック（管理者不要）。
.DESCRIPTION
  サービス状態・ポート待受・エンドポイント応答を確認する。配信到達（ingest→Redis→viewer）の
  E2Eは verify-serving.py（別途）で行う。
#>
[CmdletBinding()]
param([int]$IngestPort = 5000, [int]$ViewerPort = 5001)

function Check($label, [scriptblock]$test) {
  try { $r = & $test; if ($r) { Write-Host "[ OK ] $label" -ForegroundColor Green } else { Write-Host "[FAIL] $label" -ForegroundColor Red } }
  catch { Write-Host "[FAIL] $label : $_" -ForegroundColor Red }
}
function HttpCode($url) {
  try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8).StatusCode } catch { -1 }
}

Write-Host "==== サービス状態 ====" -ForegroundColor Cyan
Get-Service 'Memurai','plc-ingest','plc-viewer' -ErrorAction SilentlyContinue | Format-Table Name, Status, StartType -AutoSize

Write-Host "==== エンドポイント ====" -ForegroundColor Cyan
# 127.0.0.1 を使う（localhost だと Windows は IPv6 を先に試み遅延する既知の罠）
Check "Memurai(6379) 待受"        { (Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue) -ne $null }
Check "ingest  /api/health (200)" { (HttpCode "http://127.0.0.1:$IngestPort/api/health") -eq 200 }
Check "viewer  /api/health (200)" { (HttpCode "http://127.0.0.1:$ViewerPort/api/health") -eq 200 }
Check "viewer  / (UI配信 200)"    { (HttpCode "http://127.0.0.1:$ViewerPort/") -eq 200 }

Write-Host ""
Write-Host "上記が全てOKなら、サービスのネイティブ常駐は成立。" -ForegroundColor Yellow
Write-Host "配信到達(ingest POST→Redis→viewerへリアルタイム反映)のE2Eは、設備登録を含む次段で確認します。" -ForegroundColor Yellow
