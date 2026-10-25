# Real MuJoCo viewer capture (bricks move). Visual review required before claiming ready.
$ErrorActionPreference = "Continue"
$FFmpeg = "C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
$Ffprobe = "C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
$Focus = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\scripts\FocusAndFrameMuJoCo.exe"
$Log = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_real_viewer.log"
$FfLog = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_viewer_ffmpeg.log"
$Mkv = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mkv"
$Mp4 = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mp4"
$Prev = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\_preview"
$Py = "C:\Users\Fahrad\AppData\Local\Programs\Python\Python314\python.exe"
$Checker = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\scripts\check_overview_frame.py"
$MaxSec = 720

New-Item -ItemType Directory -Force -Path $Prev | Out-Null

Write-Host "Waiting for DQN..."
$ready = $false
for ($i = 0; $i -lt 150; $i++) {
  if ((Test-Path $Log) -and ((Get-Content $Log -Raw -EA SilentlyContinue) -match "policy=rl_dqn|Fear action policy: dqn")) {
    $ready = $true
    Write-Host "DQN_READY"
    break
  }
  Start-Sleep 1
}
if (-not $ready) { Write-Host "FAIL: DQN not ready"; exit 1 }

Start-Sleep 3
$focusOut = & $Focus | Out-String
Write-Host $focusOut
$rectLine = ($focusOut -split "`r?`n" | Where-Object { $_ -like "RECT=*" } | Select-Object -First 1)
if (-not $rectLine) { Write-Host "FAIL: MuJoCo window not found"; exit 1 }
$nums = $rectLine.Substring(5).Split(",")
$x = [Math]::Max(0, [int]$nums[0])
$y = [Math]::Max(0, [int]$nums[1])
$w = [int]$nums[2]
$h = [int]$nums[3]
if ($w % 2) { $w -= 1 }
if ($h % 2) { $h -= 1 }
Write-Host ("REGION x={0} y={1} w={2} h={3}" -f $x, $y, $w, $h)

# Hard gate: refuse to record if framing is still robot-zoom.
$frameStill = Join-Path $Prev "frame_before_record.png"
& $FFmpeg -y -f gdigrab -framerate 1 -offset_x $x -offset_y $y -video_size (${w}.ToString() + "x" + $h.ToString()) -i desktop -frames:v 1 $frameStill 2>$null
$chk = & $Py $Checker $frameStill 2>&1 | Out-String
Write-Host $chk
if ($LASTEXITCODE -ne 0) {
  Write-Host "FAIL: camera framing not overview - refusing capture (no false positive)"
  exit 5
}
Write-Host "FRAMING_OK"

Remove-Item $Mkv, $Mp4, $FfLog -EA SilentlyContinue
$sizeArg = "{0}x{1}" -f $w, $h
$arg = "-y -f gdigrab -framerate 12 -offset_x $x -offset_y $y -video_size $sizeArg -i desktop -t $MaxSec -an -c:v libx264 -preset veryfast -crf 20 `"$Mkv`""
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
Start-Job -ScriptBlock { param($p, $f) $p.StandardError.ReadToEnd() | Set-Content -Path $f -Encoding utf8 } -ArgumentList $ff, $FfLog | Out-Null
Write-Host ("REC={0}" -f $ff.Id)

$done = $false
for ($i = 0; $i -lt 360; $i++) {
  $txt = Get-Content $Log -Raw -EA SilentlyContinue
  if ($txt -and ($txt -match "ALL BRICKS DONE")) {
    $done = $true
    Write-Host "LOG_ALL_BRICKS_DONE"
    Start-Sleep 8
    break
  }
  if ($ff.HasExited) { Write-Host "FF_EXIT"; break }
  Start-Sleep 2
}

if (-not $ff.HasExited) {
  try { $ff.StandardInput.Write("q"); $ff.StandardInput.Flush() } catch {}
  if (-not $ff.WaitForExit(20000)) { $ff.Kill() }
}
Start-Sleep 1

$mkvLen = 0
if (Test-Path $Mkv) { $mkvLen = (Get-Item $Mkv).Length }
Write-Host ("MKV={0} log_done={1}" -f $mkvLen, $done)
if ($mkvLen -lt 800000) { Write-Host "FAIL: mkv too small"; exit 1 }

& $FFmpeg -y -i $Mkv -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart $Mp4
if (-not (Test-Path $Mp4)) { Write-Host "FAIL: mp4 missing"; exit 1 }
$mp4Len = (Get-Item $Mp4).Length
$dur = & $Ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $Mp4
Write-Host ("MP4={0} duration={1}" -f $mp4Len, $dur)

$durN = 0.0
[void][double]::TryParse([string]$dur, [ref]$durN)
if ($durN -lt 120.0) {
  Write-Host ("FAIL: video too short ({0}s)" -f $durN)
  exit 3
}
if (-not $done) {
  Write-Host "FAIL: log never reached ALL BRICKS DONE"
  exit 4
}

$mid = [Math]::Max(30.0, $durN * 0.45)
$late = [Math]::Max(60.0, $durN * 0.85)
& $FFmpeg -y -ss 15 -i $Mp4 -frames:v 1 "$Prev\check_early.png" 2>$null
& $FFmpeg -y -ss $mid -i $Mp4 -frames:v 1 "$Prev\check_mid.png" 2>$null
& $FFmpeg -y -ss $late -i $Mp4 -frames:v 1 "$Prev\check_late.png" 2>$null
Write-Host "CHECK_FRAMES_WRITTEN"
$vis = & $Py $Checker "$Prev\check_early.png" "$Prev\check_mid.png" "$Prev\check_late.png" 2>&1 | Out-String
Write-Host $vis
if ($LASTEXITCODE -ne 0) {
  Remove-Item $Mp4, $Mkv -EA SilentlyContinue
  Write-Host "FAIL: visual overview gate failed - deleted mp4 (no false positive)"
  exit 6
}
Write-Host "CAPTURE_OK_PENDING_HUMAN_FRAME_REVIEW"
Write-Host ("MP4_PATH={0}" -f $Mp4)
exit 0
