$base = 'http://127.0.0.1:8000'
$repo = Join-Path $env:USERPROFILE 'pixel_AI'
$watch = 'C:\Users\junnnnyServer\Desktop\shots'
$sampleA = Join-Path $repo 'frontend\src\assets\frames\frame-05-pixel-arcade.png'
$sampleB = Join-Path $repo 'frontend\src\assets\frames\frame-01-signature-white.png'
Invoke-RestMethod -Method Post -Uri "$base/api/session/reset" | Out-Null
$comfy = Invoke-RestMethod -Method Get -Uri "$base/api/comfyui/status"
if (-not $comfy.online) { throw 'ComfyUI offline' }
$presets = Invoke-RestMethod -Method Get -Uri "$base/api/presets"
if (-not $presets.active) { throw 'No active preset' }
$start = Invoke-RestMethod -Method Post -Uri "$base/api/session/start"
$sessionId = $start.session_id
Copy-Item -LiteralPath $sampleA -Destination (Join-Path $watch ('e2e_a_' + [guid]::NewGuid().ToString() + '.png')) -Force
Copy-Item -LiteralPath $sampleB -Destination (Join-Path $watch ('e2e_b_' + [guid]::NewGuid().ToString() + '.png')) -Force
$shots = $null
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 750
  $session = Invoke-RestMethod -Method Get -Uri "$base/api/sessions/$sessionId"
  if (($session.shots | Measure-Object).Count -ge 2) { $shots = $session.shots; break }
}
if (-not $shots -or $shots.Count -lt 2) { throw 'Expected 2 ingested shots' }
$shot1 = $shots[0]
$shot2 = $shots[1]
Invoke-RestMethod -Method Post -Uri "$base/api/session/finish-capture" | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/api/session/select-shot" -ContentType 'application/json' -Body (@{ shot_id = $shot1.shot_id } | ConvertTo-Json) | Out-Null
$run1 = Invoke-RestMethod -Method Post -Uri "$base/api/session/run-selected"
$detail = $null
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Seconds 1
  $detail = Invoke-RestMethod -Method Get -Uri "$base/api/sessions/$sessionId"
  if ($detail.phase -eq 'result_ready') { break }
  if ($detail.phase -eq 'error') { throw ('First generation failed: ' + $detail.error) }
}
if ($detail.phase -ne 'result_ready') { throw 'First generation timeout' }
$firstResult = $detail.generated_results[-1]
Invoke-RestMethod -Method Post -Uri "$base/api/sessions/$sessionId/select-shot" -ContentType 'application/json' -Body (@{ shot_id = $shot2.shot_id } | ConvertTo-Json) | Out-Null
$rerun = Invoke-RestMethod -Method Post -Uri "$base/api/session/rerun" -ContentType 'application/json' -Body (@{ session_id = $sessionId } | ConvertTo-Json)
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Seconds 1
  $detail = Invoke-RestMethod -Method Get -Uri "$base/api/sessions/$sessionId"
  if ($detail.phase -eq 'result_ready' -and ($detail.generated_results | Measure-Object).Count -ge 2) { break }
  if ($detail.phase -eq 'error') { throw ('Rerun failed: ' + $detail.error) }
}
if ($detail.phase -ne 'result_ready') { throw 'Rerun timeout' }
$latestResult = $detail.generated_results[-1]
$compose = Invoke-RestMethod -Method Post -Uri "$base/api/session/compose-print" -ContentType 'application/json' -Body (@{
  session_id = $sessionId
  frame_id = 'frame-02-signature-black'
  result_id = $latestResult.result_id
  layout = @{ original = @{ scale = 1.0; offset_x = 0; offset_y = 0 }; ai = @{ scale = 1.0; offset_x = 0; offset_y = 0 } }
} | ConvertTo-Json -Depth 5)
Invoke-RestMethod -Method Post -Uri "$base/api/session/complete" -ContentType 'application/json' -Body (@{ session_id = $sessionId } | ConvertTo-Json) | Out-Null
$final = Invoke-RestMethod -Method Get -Uri "$base/api/sessions/$sessionId"
[pscustomobject]@{
  session_id = $sessionId
  first_prompt_id = $run1.prompt_id
  rerun_prompt_id = $rerun.prompt_id
  first_result_source_shot = $firstResult.source_shot_id
  latest_result_source_shot = $latestResult.source_shot_id
  latest_result_source_filename = $latestResult.source_shot_filename
  generated_result_count = ($final.generated_results | Measure-Object).Count
  selected_shot_id = $final.selected_shot_id
  selected_generated_result_id = $final.selected_generated_result_id
  print_output_count = ($final.print_outputs | Measure-Object).Count
  latest_print_result_id = $final.latest_print_output.result_id
  phase = $final.phase
} | ConvertTo-Json -Compress
