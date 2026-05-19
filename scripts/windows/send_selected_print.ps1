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

if ($StartBackend) {
  try {
    $null = Invoke-RestMethod "$AppBaseUrl/api/comfyui/status"
  } catch {
    $scriptRoot = Split-Path -Parent $PSCommandPath
    $repo = Split-Path -Parent (Split-Path -Parent $scriptRoot)
    $pythonExe = Join-Path $repo ".venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
      Write-Error "Cannot start backend automatically because $pythonExe was not found."
    }

    Write-Host "Starting backend..."
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
}

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
