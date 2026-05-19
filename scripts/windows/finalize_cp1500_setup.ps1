param(
  [string[]]$ExpectedPrinters = @("SELPHY-LEFT", "SELPHY-RIGHT"),
  [switch]$ProvisionNames,
  [switch]$UpdateEnv,
  [switch]$StartBackend
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $PSCommandPath
$provisionScript = Join-Path $scriptRoot "provision_cp1500_printers.ps1"
$verifyScript = Join-Path $scriptRoot "verify_cp1500_printers.ps1"

if ($ProvisionNames) {
  Write-Host "=== Provisioning printer names ==="
  $provisionArgs = @{
    FilePath = $provisionScript
    ExecutionPolicy = "Bypass"
  }
  if ($UpdateEnv) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $provisionScript -TargetNames $ExpectedPrinters -UpdateEnv
  } else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $provisionScript -TargetNames $ExpectedPrinters
  }
}

Write-Host "`n=== Verifying printer visibility ==="
if ($StartBackend) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyScript -ExpectedPrinters $ExpectedPrinters -StartBackend
} else {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyScript -ExpectedPrinters $ExpectedPrinters
}

Write-Host "`n=== Sending test pages ==="
foreach ($printerName in $ExpectedPrinters) {
  Write-Host "Sending test page to $printerName"
  $response = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/printers/test-page" -ContentType "application/json" -Body (@{
    printer_name = $printerName
    copies = 1
  } | ConvertTo-Json)
  $response | ConvertTo-Json -Depth 8
}

Write-Host "`nAll requested test-page dispatch calls completed."
