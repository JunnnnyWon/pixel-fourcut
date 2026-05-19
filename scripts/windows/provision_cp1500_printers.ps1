param(
  [string[]]$TargetNames = @("SELPHY-LEFT", "SELPHY-RIGHT"),
  [string]$EnvPath = "$env:USERPROFILE\pixel_AI\.env",
  [switch]$UpdateEnv
)

$ErrorActionPreference = "Stop"

Write-Host "=== Discovering Canon/SELPHY printers ==="
$printers = Get-Printer | Where-Object {
  ($_.Name -match 'Canon|SELPHY|CP1500') -or
  ($_.DriverName -match 'Canon|SELPHY|CP1500')
}

if (-not $printers) {
  Write-Error "No Canon/SELPHY printers are currently registered in Windows."
}

$printers | Select-Object Name, DriverName, PortName, PrinterStatus | Format-Table -AutoSize

if ($printers.Count -gt $TargetNames.Count) {
  Write-Error "More printers found than target names. Adjust -TargetNames and rerun."
}

for ($i = 0; $i -lt $printers.Count; $i++) {
  $current = $printers[$i]
  $desired = $TargetNames[$i]
  if ($current.Name -ne $desired) {
    Write-Host "Renaming '$($current.Name)' -> '$desired'"
    Rename-Printer -Name $current.Name -NewName $desired
  }
}

Write-Host "`n=== Final printer names ==="
$finalNames = $TargetNames | Select-Object -First $printers.Count
$finalPrinters = Get-Printer | Where-Object { $_.Name -in $finalNames }
$finalPrinters | Select-Object Name, DriverName, PortName, PrinterStatus | Format-Table -AutoSize

if ($UpdateEnv) {
  Write-Host "`n=== Updating .env printer allowlist ==="
  if (-not (Test-Path $EnvPath)) {
    Write-Error ".env not found at $EnvPath"
  }

  $content = Get-Content $EnvPath
  $allowlist = "PRINTER_NAME_ALLOWLIST=" + (($finalPrinters | Select-Object -ExpandProperty Name) -join ",")
  $found = $false
  for ($i = 0; $i -lt $content.Count; $i++) {
    if ($content[$i] -like "PRINTER_NAME_ALLOWLIST=*") {
      $content[$i] = $allowlist
      $found = $true
    }
  }
  if (-not $found) {
    $content += $allowlist
  }
  [System.IO.File]::WriteAllLines($EnvPath, $content, [System.Text.UTF8Encoding]::new($false))
  Write-Host $allowlist
}
