#!/usr/bin/env bash
# Record REAL live MuJoCo viewer (bricks actually move) with overview framing.
# PASS only if log has ALL BRICKS DONE AND video is large enough.
# Do NOT claim success from logs alone — operator must check frames.
set +e
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
export FEAR_TEST_THAW=0
export FEAR_DQN_MODEL="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz"

ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
LOG="$ROOT/output/live_session_real_viewer.log"
OUT_DIR="$ROOT/output"
DESK="/mnt/c/Users/Fahrad/Desktop"
MKV="$DESK/FearHRI_live_session_for_Csenge.mkv"
MP4="$DESK/FearHRI_live_session_for_Csenge.mp4"
FFMPEG_WIN='/mnt/c/Users/Fahrad/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe'
FOCUS_EXE='/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/FocusAndFrameMuJoCo.exe'
FFLOG="$OUT_DIR/live_viewer_ffmpeg.log"
RECORD_MAX_S="${RECORD_MAX_S:-720}"

mkdir -p "$OUT_DIR"
rm -f "$LOG" "$MKV" "$MP4" "$FFLOG"

bash "$ROOT/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 2

echo "Launching live MuJoCo (real viewer — bricks move in this window)..."
bash "$ROOT/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!

READY=0
for i in $(seq 1 150); do
  if grep -Eiq 'policy=rl_dqn|Fear action policy: dqn' "$LOG" 2>/dev/null; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "$READY" -ne 1 ]]; then
  echo "FAIL: DQN not ready"
  exit 1
fi
echo "DQN ready — framing overview camera (Align + zoom out), then capture"
sleep 4

# Frame camera via Windows helper (must run under Windows, not WSL ELF)
# Write a small PowerShell driver to Desktop temp
PS1="$OUT_DIR/_capture_framed_viewer.ps1"
cat > "$PS1" <<'PSEOF'
$ErrorActionPreference = "Continue"
$FFmpeg = "C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
$Focus = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\scripts\FocusAndFrameMuJoCo.exe"
$Log = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_real_viewer.log"
$FfLog = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_viewer_ffmpeg.log"
$Mkv = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mkv"
$Mp4 = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mp4"
$MaxSec = 720

$focusOut = & $Focus | Out-String
Write-Host $focusOut
$rectLine = ($focusOut -split "`r?`n" | Where-Object { $_ -like "RECT=*" } | Select-Object -First 1)
if (-not $rectLine) { Write-Host "FAIL: MuJoCo window not found"; exit 1 }
$nums = $rectLine.Substring(5).Split(",")
$x = [Math]::Max(0, [int]$nums[0]); $y = [Math]::Max(0, [int]$nums[1])
$w = [int]$nums[2]; $h = [int]$nums[3]
if ($w % 2) { $w -= 1 }
if ($h % 2) { $h -= 1 }
Write-Host "REGION x=$x y=$y w=$w h=$h"

Remove-Item $Mkv, $Mp4, $FfLog -EA SilentlyContinue
$arg = "-y -f gdigrab -framerate 12 -offset_x $x -offset_y $y -video_size ${w}x${h} -i desktop -t $MaxSec -an -c:v libx264 -preset veryfast -crf 20 `"$Mkv`""
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
for ($i = 0; $i -lt 360; $i++) {
  if ((Get-Content $Log -Raw -EA SilentlyContinue) -match "ALL BRICKS DONE") {
    $done = $true
    Write-Host "LOG_ALL_BRICKS_DONE"
    Start-Sleep 6
    break
  }
  if ($ff.HasExited) { Write-Host "FF_EXIT"; break }
  Start-Sleep 2
}
if (-not $ff.HasExited) {
  try { $ff.StandardInput.Write("q"); $ff.StandardInput.Flush() } catch {}
  if (-not $ff.WaitForExit(15000)) { $ff.Kill() }
}
Start-Sleep 1
$mkvLen = 0
if (Test-Path $Mkv) { $mkvLen = (Get-Item $Mkv).Length }
Write-Host "MKV=$mkvLen log_done=$done"
if ($mkvLen -lt 500000) { Write-Host "FAIL: mkv too small"; exit 1 }
& $FFmpeg -y -i $Mkv -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart $Mp4
$mp4Len = 0
if (Test-Path $Mp4) { $mp4Len = (Get-Item $Mp4).Length }
Write-Host "MP4=$mp4Len"
Write-Host "CAPTURE_FINISHED"
if ($done -and $mp4Len -gt 500000) { exit 0 } else { exit 2 }
PSEOF
# Convert to CRLF-ish and run under Windows PowerShell
sed -i 's/$/\r/' "$PS1" 2>/dev/null || true

# Invoke via powershell.exe from WSL interop often fails on this machine —
# so we signal Windows by writing a flag and ask the agent shell to run PS.
echo "RUN_PS1=$PS1"
echo "SIM_LOG=$LOG"
echo "WAITING_FOR_WINDOWS_CAPTURE"
