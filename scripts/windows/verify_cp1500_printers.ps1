param(
  [string]$AppBaseUrl = "http://127.0.0.1:8000",
  [string[]]$ExpectedPrinters = @("SELPHY-LEFT", "SELPHY-RIGHT"),
  [switch]$StartBackend
)

$ErrorActionPreference = "Stop"

Write-Host "=== Windows printers ==="
$osPrinters = Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus, WorkOffline
$osPrinters | Format-Table -AutoSize

Write-Host "`n=== Canon / SELPHY related PnP devices ==="
$pnpMatches = Get-PnpDevice | Where-Object {
  ($_.FriendlyName -and $_.FriendlyName -match 'Canon|SELPHY|CP1500') -or
  ($_.InstanceId -and $_.InstanceId -match 'CANON|SELPHY|CP1500|VID_04A9')
} | Select-Object Status, Class, FriendlyName, InstanceId

if ($pnpMatches) {
  $pnpMatches | Format-Table -AutoSize
} else {
  Write-Host "No Canon/SELPHY-related PnP devices found."
}

Write-Host "`n=== Installed print drivers ==="
Get-PrinterDriver | Select-Object Name, Manufacturer, MajorVersion | Format-Table -AutoSize

try {
  $null = Invoke-RestMethod "$AppBaseUrl/api/comfyui/status"
} catch {
  if (-not $StartBackend) {
    Write-Error "The app backend is not reachable at $AppBaseUrl. Start the FastAPI server first, or rerun this script with -StartBackend."
  }

  $repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
  $pythonExe = Join-Path $repo ".venv\Scripts\python.exe"
  if (-not (Test-Path $pythonExe)) {
    Write-Error "Cannot start backend automatically because $pythonExe was not found."
  }

  Write-Host "`n=== Starting backend ==="
  Start-Process -FilePath $pythonExe -ArgumentList "-m","uvicorn","backend.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $repo | Out-Null
  $started = $false
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
      $null = Invoke-RestMethod "$AppBaseUrl/api/comfyui/status"
      $started = $true
      break
    } catch {}
  }
  if (-not $started) {
    Write-Error "The app backend could not be started automatically."
  }
}

Write-Host "`n=== App visible printers ==="
$visible = Invoke-RestMethod "$AppBaseUrl/api/printers"
$visible.printers | ConvertTo-Json -Depth 6

Write-Host "`n=== App printer diagnostics ==="
$diagnostics = Invoke-RestMethod "$AppBaseUrl/api/printers/diagnostics"
$diagnostics | ConvertTo-Json -Depth 8

$missing = @()
foreach ($name in $ExpectedPrinters) {
  if (-not ($visible.printers | Where-Object { $_.name -eq $name })) {
    $missing += $name
  }
}

if ($missing.Count -gt 0) {
  Write-Error ("Missing expected printers in app view: " + ($missing -join ", "))
}

Write-Host "`nAll expected printers are visible in the app."
