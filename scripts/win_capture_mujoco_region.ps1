# Capture live MuJoCo window region (real ROS session) -> Desktop mp4
$ErrorActionPreference = "Continue"
$FFmpeg = "C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
$Focus = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\scripts\FocusMuJoCo.exe"
$Log = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_win_record.log"
$FfLog = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_win_ffmpeg.log"
$Mkv = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mkv"
$Mp4 = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mp4"

Write-Host "Waiting for DQN..."
for ($i = 0; $i -lt 120; $i++) {
  if ((Test-Path $Log) -and ((Get-Content $Log -Raw -EA SilentlyContinue) -match "policy=rl_dqn|Fear action policy: dqn")) {
    Write-Host "DQN_READY"
    break
  }
  Start-Sleep 1
}

Start-Sleep 3
$focusOut = & $Focus | Out-String
Write-Host $focusOut
$rectLine = ($focusOut -split "`r?`n" | Where-Object { $_ -like "RECT=*" } | Select-Object -First 1)
if (-not $rectLine) { Write-Host "FAIL: MuJoCo window not found"; exit 1 }
$nums = $rectLine.Substring(5).Split(",")
$x = [int]$nums[0]; $y = [int]$nums[1]; $w = [int]$nums[2]; $h = [int]$nums[3]
if ($w % 2) { $w -= 1 }
if ($h % 2) { $h -= 1 }
if ($w -lt 640 -or $h -lt 480) { Write-Host "FAIL: window too small $w x $h"; exit 1 }
Write-Host "REGION x=$x y=$y w=$w h=$h"

Remove-Item $Mkv, $Mp4, $FfLog -EA SilentlyContinue
# Focus once only — do NOT keep clicking the MuJoCo UI (that pauses the viewer)
$arg = "-y -f gdigrab -framerate 12 -offset_x $x -offset_y $y -video_size ${w}x${h} -i desktop -t 700 -an -c:v libx264 -preset veryfast -crf 20 `"$Mkv`""
Write-Host "ARGS $arg"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $FFmpeg
$psi.Arguments = $arg
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$ff = New-Object System.Diagnostics.Process
$ff.StartInfo = $psi
[void]$ff.Start()
Start-Job -ScriptBlock { param($p,$f) $p.StandardError.ReadToEnd() | Set-Content -Path $f -Encoding utf8 } -ArgumentList $ff,$FfLog | Out-Null
Write-Host "REC=$($ff.Id)"

$done = $false
for ($i = 0; $i -lt 350; $i++) {
  if ((Get-Content $Log -Raw -EA SilentlyContinue) -match "ALL BRICKS DONE") {
    $done = $true
    Write-Host "BRICKS_DONE"
    Start-Sleep 5
    break
  }
  if ($ff.HasExited) {
    Write-Host "FF_EXIT"
    Get-Content $FfLog -Tail 40 -EA SilentlyContinue
    break
  }
  Start-Sleep 2
}

if (-not $ff.HasExited) {
  try { $ff.StandardInput.Write("q"); $ff.StandardInput.Flush() } catch {}
  if (-not $ff.WaitForExit(15000)) { $ff.Kill() }
}

Start-Sleep 1
$mkvLen = 0
if (Test-Path $Mkv) { $mkvLen = (Get-Item $Mkv).Length }
Write-Host "MKV=$mkvLen done=$done"
if ($mkvLen -lt 200000) {
  Write-Host "FAIL: mkv too small"
  Get-Content $FfLog -Tail 50 -EA SilentlyContinue
  exit 1
}

& $FFmpeg -y -i $Mkv -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart $Mp4
$mp4Len = 0
if (Test-Path $Mp4) { $mp4Len = (Get-Item $Mp4).Length }
Write-Host "MP4=$mp4Len"
Write-Host "REC_DONE"
if ($done -and $mp4Len -gt 200000) { exit 0 } else { exit 2 }
