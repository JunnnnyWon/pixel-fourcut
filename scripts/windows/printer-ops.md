# Printer Ops

## Windows setup

1. Install both Canon SELPHY CP1500 printers in Windows.
2. Rename them to stable names such as:
   - `SELPHY-LEFT`
   - `SELPHY-RIGHT`
3. Optional but recommended: set the app printer filter.

```env
PRINTER_NAME_ALLOWLIST=SELPHY-LEFT,SELPHY-RIGHT
SHOW_VIRTUAL_PRINTERS=
```

4. Confirm they appear in PowerShell:

```powershell
Get-Printer | Select Name, DriverName, PortName, PrinterStatus
```

5. Confirm the app sees them:

```powershell
curl http://127.0.0.1:8000/api/printers
```

## CP1500 USB checklist

Before debugging the app, make sure Windows can see the printer as hardware:

1. Use the CP1500 AC power adapter.
2. Use a **USB data cable**, not a charge-only USB-C cable.
3. Connect the printer directly to the Windows PC when possible.
4. Confirm the printer appears in Windows device/printer listings before using the app.

Canon's official support page for SELPHY CP1500 lists:
- **Windows 11** support
- **USB 2.0 Type-C** connectivity for computer connection
- **USB charging not supported**

Reference:
- [Canon SELPHY CP1500 Support](https://www.usa.canon.com/support/p/selphy-cp1500)

If the app diagnostics show only cameras or no Canon/SELPHY printer devices at all, the problem is below the application layer:
- power
- cable
- USB enumeration
- Windows printer registration

If Windows already sees the CP1500 printers but the names are messy, normalize them and update the app allowlist in one step:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\provision_cp1500_printers.ps1 -UpdateEnv
```

To run the full final setup flow in one shot after both printers are connected:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\finalize_cp1500_setup.ps1 -ProvisionNames -UpdateEnv -StartBackend
```

6. If printers do not show up, inspect diagnostics:

```powershell
curl http://127.0.0.1:8000/api/printers/diagnostics
```

This shows:
- all Windows-registered printers
- which ones are hidden as virtual printers
- the active allowlist and virtual-printer filter state

7. Run the end-to-end printer visibility check:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\verify_cp1500_printers.ps1
```

## Operator workflow

1. In `/print`, select the highest-priority waiting session.
2. Build the final print image if needed.
3. Pick `SELPHY-LEFT` or `SELPHY-RIGHT`.
4. Set copy count.
5. Click `선택 프린터로 출력`.
6. Confirm the printer job history updates.
7. Click `인화 완료 처리 후 다음 팀으로`.

## Manual dispatch check

You can send a print job directly through the API without using the browser UI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\send_selected_print.ps1 `
  -SessionId 20260518_12_30 `
  -PrinterName SELPHY-LEFT `
  -Copies 1
```

If the backend is not already running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\send_selected_print.ps1 `
  -SessionId 20260518_12_30 `
  -PrinterName SELPHY-LEFT `
  -Copies 1 `
  -StartBackend
```

If you want to target a specific stored print output:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\send_selected_print.ps1 `
  -SessionId 20260518_12_30 `
  -PrinterName SELPHY-RIGHT `
  -PrintId print-001 `
  -Copies 2
```

To run the full dispatch + refresh + completion verification for one session:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\verify_print_completion.ps1 `
  -SessionId 20260518_12_30 `
  -PrinterName SELPHY-LEFT `
  -Copies 1 `
  -StartBackend
```

## Session tracking

- Generated print files remain under `workspace/sessions/<session_id>/prints/`.
- Printer dispatch history is stored in each session as `printer_jobs`.
- Each print output stores the most recent printer/copy info when dispatched.
