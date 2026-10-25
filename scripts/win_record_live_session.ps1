# Clean live MuJoCo session capture (Windows desktop) -> Desktop mp4 only.
$ErrorActionPreference = "Continue"
$FFmpeg = "C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
$Out = "C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mp4"
$Log = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_win_record.log"
$FfLog = "C:\Users\Fahrad\Desktop\AI Lab\fear_mecanumbot\output\live_session_win_ffmpeg.log"
$MaxSec = 700

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
Remove-Item $Out -ErrorAction SilentlyContinue
Remove-Item $Log -ErrorAction SilentlyContinue
Remove-Item $FfLog -ErrorAction SilentlyContinue

Write-Host "Launching live MuJoCo Fear HRI..."
$launchCmd = "export DISPLAY=:0 MUJOCO_GL=glfw FEAR_USE_SIM=1 FEAR_CATCH_ATTENTION=0 FEAR_TEST_THAW=0 FEAR_DQN_MODEL='/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz'; bash '/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_clean_brick_sim.sh' > '/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/live_session_win_record.log' 2>&1"
$launch = Start-Process -FilePath "wsl.exe" -ArgumentList "-e","bash","-lc",$launchCmd -PassThru -WindowStyle Minimized

Write-Host "Waiting for Double DQN..."
$ready = $false
for ($i = 0; $i -lt 180; $i++) {
  if (Test-Path $Log) {
    $txt = Get-Content $Log -Raw -ErrorAction SilentlyContinue
    if ($txt -match "policy=rl_dqn") { $ready = $true; break }
    if ($txt -match "Fear action policy: dqn") { $ready = $true; break }
  }
  Start-Sleep -Seconds 1
}
if (-not $ready) {
  Write-Host "FAIL: DQN not ready"
  if (Test-Path $Log) { Get-Content $Log -Tail 40 }
  exit 1
}
Write-Host "DQN ready"
Start-Sleep -Seconds 5

Write-Host "Starting desktop capture..."
$arg = "-y -f gdigrab -framerate 12 -i desktop -t $MaxSec -pix_fmt yuv420p -an -c:v libx264 -preset veryfast -crf 22 -movflags +faststart `"$Out`""
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
Start-Job -ScriptBlock {
  param($proc, $path)
  $proc.StandardError.ReadToEnd() | Set-Content -Path $path
} -ArgumentList $ff, $FfLog | Out-Null

Write-Host ("FFPID={0} recording..." -f $ff.Id)
$done = $false
$deadline = (Get-Date).AddSeconds($MaxSec)
while ((Get-Date) -lt $deadline) {
  if (Test-Path $Log) {
    $txt = Get-Content $Log -Raw -ErrorAction SilentlyContinue
    if ($txt -match "ALL BRICKS DONE") {
      $done = $true
      Write-Host "ALL BRICKS DONE - finalizing video"
      Start-Sleep -Seconds 4
      break
    }
  }
  if ($ff.HasExited) {
    Write-Host "WARN: ffmpeg exited early"
    break
  }
  Start-Sleep -Seconds 2
}

if (-not $ff.HasExited) {
  try {
    $ff.StandardInput.Write("q")
    $ff.StandardInput.Flush()
  } catch {}
  if (-not $ff.WaitForExit(10000)) {
    $ff.Kill()
  }
}

Start-Process -FilePath "wsl.exe" -ArgumentList "-e","bash","-lc","bash '/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh' >/dev/null 2>&1" -WindowStyle Hidden

if (-not (Test-Path $Out)) {
  Write-Host "FAIL: no video"
  if (Test-Path $FfLog) { Get-Content $FfLog -Tail 40 }
  exit 1
}
$len = (Get-Item $Out).Length
Write-Host ("VIDEO size={0} bricks_done={1} path={2}" -f $len, $done, $Out)
Write-Host "LIVE_SESSION_VIDEO_READY"
if ($done -and ($len -gt 500000)) { exit 0 } else { exit 2 }
