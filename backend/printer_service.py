from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from backend.config import PRINTER_NAME_ALLOWLIST, SHOW_VIRTUAL_PRINTERS


VIRTUAL_PRINTER_TOKENS = (
    "print to pdf",
    "xps",
    "onenote",
    "fax",
    "pdf",
)


def _run_powershell(script: str) -> str:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _is_virtual_printer(name: str, driver_name: str | None, port_name: str | None) -> bool:
    haystacks = [name or "", driver_name or "", port_name or ""]
    combined = " ".join(haystacks).lower()
    return any(token in combined for token in VIRTUAL_PRINTER_TOKENS)


def _normalize_printers(data: list[dict] | dict) -> list[dict]:
    if isinstance(data, dict):
        data = [data]

    return [
        {
            "name": item["Name"],
            "driver_name": item.get("DriverName"),
            "port_name": item.get("PortName"),
            "printer_status": item.get("PrinterStatus"),
            "work_offline": item.get("WorkOffline"),
            "is_virtual": _is_virtual_printer(item["Name"], item.get("DriverName"), item.get("PortName")),
            "is_available": not bool(item.get("WorkOffline")),
        }
        for item in data
    ]


def list_all_printers() -> list[dict]:
    if platform.system() != "Windows":
        return []

    output = _run_powershell(
        "Get-Printer | Select-Object Name,DriverName,PortName,PrinterStatus,WorkOffline | ConvertTo-Json -Compress"
    )
    if not output:
        return []
    return _normalize_printers(json.loads(output))


def list_printers() -> list[dict]:
    printers = []
    for item in list_all_printers():
        name = item["name"]
        is_virtual = item["is_virtual"]
        if PRINTER_NAME_ALLOWLIST and name not in PRINTER_NAME_ALLOWLIST:
            continue
        if is_virtual and not SHOW_VIRTUAL_PRINTERS:
            continue
        printers.append(item)

    return printers


def get_printer_diagnostics() -> dict:
    all_printers = list_all_printers()
    visible_printers = list_printers()
    hidden_printers = [
        printer
        for printer in all_printers
        if printer["name"] not in {item["name"] for item in visible_printers}
    ]
    return {
        "platform": platform.system(),
        "allowlist": PRINTER_NAME_ALLOWLIST,
        "show_virtual_printers": SHOW_VIRTUAL_PRINTERS,
        "all_printers": all_printers,
        "visible_printers": visible_printers,
        "hidden_printers": hidden_printers,
        "installed_print_drivers": list_print_drivers(),
        "related_pnp_devices": list_related_pnp_devices(),
    }


def list_print_drivers() -> list[dict]:
    if platform.system() != "Windows":
        return []

    output = _run_powershell(
        "Get-PrinterDriver | Select-Object Name,Manufacturer,MajorVersion | ConvertTo-Json -Compress"
    )
    if not output:
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    return [
        {
            "name": item.get("Name"),
            "manufacturer": item.get("Manufacturer"),
            "major_version": item.get("MajorVersion"),
        }
        for item in data
    ]


def list_related_pnp_devices() -> list[dict]:
    if platform.system() != "Windows":
        return []

    output = _run_powershell(
        """
$matches = Get-PnpDevice | Where-Object {
  ($_.FriendlyName -and $_.FriendlyName -match 'Canon|SELPHY|CP1500') -or
  ($_.InstanceId -and $_.InstanceId -match 'CANON|SELPHY|CP1500|VID_04A9')
} | Select-Object Status,Class,FriendlyName,InstanceId | ConvertTo-Json -Compress
$matches
"""
    )
    if not output:
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    return [
        {
            "status": item.get("Status"),
            "device_class": item.get("Class"),
            "friendly_name": item.get("FriendlyName"),
            "instance_id": item.get("InstanceId"),
        }
        for item in data
    ]


def get_print_job(printer_name: str, windows_job_id: int) -> dict | None:
    if platform.system() != "Windows":
        return None

    ps_printer = printer_name.replace("'", "''")
    output = _run_powershell(
        f"""
$job = Get-PrintJob -PrinterName '{ps_printer}' -ID {int(windows_job_id)} -ErrorAction SilentlyContinue
if ($job) {{
  $job | Select-Object ID, PrinterName, DocumentName, JobStatus, SubmittedTime | ConvertTo-Json -Compress
}}
"""
    )
    if not output:
        return None
    data = json.loads(output)
    return {
        "windows_job_id": data.get("ID"),
        "printer_name": data.get("PrinterName"),
        "document_name": data.get("DocumentName"),
        "job_status": data.get("JobStatus"),
        "submitted_time": data.get("SubmittedTime"),
    }


def send_image_to_printer(image_path: Path, printer_name: str, copies: int = 1) -> dict:
    if platform.system() != "Windows":
        raise RuntimeError("Windows 프린터 출력은 Windows 환경에서만 지원됩니다.")

    image_path = Path(image_path).resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일이 없습니다: {image_path}")

    available_printers = {printer["name"]: printer for printer in list_printers()}
    if printer_name not in available_printers:
        raise RuntimeError(f"허용된 프린터 목록에 없는 프린터입니다: {printer_name}")
    if not available_printers[printer_name].get("is_available", False):
        raise RuntimeError(f"현재 오프라인 상태인 프린터입니다: {printer_name}")

    ps_image = str(image_path).replace("'", "''")
    ps_printer = printer_name.replace("'", "''")
    copies = max(1, int(copies))

    script = f"""
Add-Type -AssemblyName System.Drawing
$imagePath = '{ps_image}'
$printerName = '{ps_printer}'
$copies = {copies}
$image = [System.Drawing.Image]::FromFile($imagePath)
$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName = $printerName
if (-not $doc.PrinterSettings.IsValid) {{
  throw "Printer not found: $printerName"
}}
$doc.PrinterSettings.Copies = [int16]$copies
$doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
$doc.add_PrintPage({{
  param($sender, $e)
  $bounds = $e.MarginBounds
  if ($bounds.Width -le 0 -or $bounds.Height -le 0) {{
    $bounds = $e.PageBounds
  }}
  $ratio = [Math]::Min($bounds.Width / $image.Width, $bounds.Height / $image.Height)
  $drawWidth = [int]($image.Width * $ratio)
  $drawHeight = [int]($image.Height * $ratio)
  $drawX = $bounds.X + [int](($bounds.Width - $drawWidth) / 2)
  $drawY = $bounds.Y + [int](($bounds.Height - $drawHeight) / 2)
  $e.Graphics.DrawImage($image, $drawX, $drawY, $drawWidth, $drawHeight)
  $e.HasMorePages = $false
}})
$beforeIds = @()
try {{
  $beforeIds = @(Get-PrintJob -PrinterName $printerName -ErrorAction Stop | Select-Object -ExpandProperty ID)
}} catch {{}}
$doc.Print()
$image.Dispose()
$job = $null
for ($i = 0; $i -lt 10; $i++) {{
  try {{
    $jobs = @(Get-PrintJob -PrinterName $printerName -ErrorAction Stop | Sort-Object ID -Descending)
    $job = $jobs | Where-Object {{ $_.ID -notin $beforeIds }} | Select-Object -First 1
    if (-not $job) {{
      $job = $jobs | Select-Object -First 1
    }}
    if ($job) {{ break }}
  }} catch {{}}
  Start-Sleep -Milliseconds 300
}}
$result = [ordered]@{{
  status = 'sent'
  printer_name = $printerName
  copies = $copies
}}
if ($job) {{
  $result['windows_job_id'] = $job.ID
  $result['job_status'] = $job.JobStatus
  $result['document_name'] = $job.DocumentName
  $result['submitted_time'] = $job.SubmittedTime
}}
$result | ConvertTo-Json -Compress | Write-Output
"""

    output = _run_powershell(script)
    return json.loads(output or "{}")


def create_test_page(output_path: Path, printer_name: str) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (1200, 1800), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        body_font = ImageFont.truetype("arial.ttf", 38)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "PIXEL AI PRINTER TEST",
        f"Printer: {printer_name}",
        f"Created: {timestamp}",
        "",
        "If this page prints correctly,",
        "the Windows printer pipeline is working.",
    ]

    y = 180
    for index, line in enumerate(lines):
        font = title_font if index == 0 else body_font
        draw.text((100, y), line, fill=(20, 20, 20), font=font)
        y += 120 if index == 0 else 70

    draw.rectangle((80, 80, 1120, 1720), outline=(30, 30, 30), width=8)
    draw.line((100, 520, 1100, 520), fill=(60, 60, 60), width=4)
    image.save(output_path)
    return output_path
