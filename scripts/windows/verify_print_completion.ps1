param(
  [Parameter(Mandatory = $true)]
  [string]$SessionId,

  [Parameter(Mandatory = $true)]
  [string]$PrinterName,

  [string]$PrintId = "",
  [int]$Copies = 1,
  [string]$AppBaseUrl = "http://127.0.0.1:8000",
  [switch]$StartBackend
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $PSCommandPath
$sendScript = Join-Path $scriptRoot "send_selected_print.ps1"

if ($StartBackend) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $sendScript -SessionId $SessionId -PrinterName $PrinterName -Copies $Copies -PrintId $PrintId -StartBackend | Out-Null
} else {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $sendScript -SessionId $SessionId -PrinterName $PrinterName -Copies $Copies -PrintId $PrintId | Out-Null
}

Write-Host "`n=== Refreshing printer job state ==="
$refresh = Invoke-RestMethod -Method Post -Uri "$AppBaseUrl/api/sessions/$SessionId/printer-jobs/refresh"
$refresh | ConvertTo-Json -Depth 8

Write-Host "`n=== Session detail after dispatch ==="
$session = Invoke-RestMethod -Method Get -Uri "$AppBaseUrl/api/sessions/$SessionId"
$session | ConvertTo-Json -Depth 8

Write-Host "`n=== Attempting completion ==="
$printIdToUse = $PrintId
if (-not $printIdToUse) {
  $printIdToUse = $session.latest_print_output.print_id
}
$completion = Invoke-RestMethod -Method Post -Uri "$AppBaseUrl/api/session/complete" -ContentType "application/json" -Body (@{
  session_id = $SessionId
  print_id = $printIdToUse
} | ConvertTo-Json)
$completion | ConvertTo-Json -Depth 8
