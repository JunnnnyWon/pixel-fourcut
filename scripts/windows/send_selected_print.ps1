param(
  [Parameter(Mandatory = $true)]
  [string]$SessionId,

  [Parameter(Mandatory = $true)]
  [string]$PrinterName,

  [string]$PrintId = "",
  [int]$Copies = 1,
  [string]$AppBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$payload = @{
  session_id = $SessionId
  printer_name = $PrinterName
  copies = [Math]::Max(1, $Copies)
}

if ($PrintId) {
  $payload.print_id = $PrintId
}

Write-Host "Sending print job..."
$response = Invoke-RestMethod -Method Post -Uri "$AppBaseUrl/api/session/send-to-printer" -ContentType "application/json" -Body ($payload | ConvertTo-Json)
$response | ConvertTo-Json -Depth 8
