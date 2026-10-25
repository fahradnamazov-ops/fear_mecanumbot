using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

class FocusAndFrameMuJoCo {
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);

  const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
  const uint MOUSEEVENTF_LEFTUP = 0x0004;
  const int SW_MAXIMIZE = 3;

  [StructLayout(LayoutKind.Sequential)]
  struct RECT { public int Left, Top, Right, Bottom; }

  static void Click(int x, int y) {
    SetCursorPos(x, y);
    Thread.Sleep(80);
    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
    Thread.Sleep(40);
    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
    Thread.Sleep(120);
  }

  static int Main() {
    foreach (var p in Process.GetProcesses()) {
      string t = "";
      try { t = p.MainWindowTitle; } catch { continue; }
      if (string.IsNullOrEmpty(t)) continue;
      bool hit =
        t.IndexOf("MuJoCo", StringComparison.OrdinalIgnoreCase) >= 0 ||
        t.IndexOf("mecanumbot", StringComparison.OrdinalIgnoreCase) >= 0;
      if (!hit) continue;
      IntPtr h = p.MainWindowHandle;
      if (h == IntPtr.Zero) continue;

      ShowWindow(h, SW_MAXIMIZE);
      SetForegroundWindow(h);
      Thread.Sleep(400);

      RECT r;
      GetWindowRect(h, out r);
      int w = r.Right - r.Left;
      int ht = r.Bottom - r.Top;
      if (w < 640 || ht < 480) continue;

      // Click Run only. Do NOT Align or scroll-wheel:
      // launch_passive sets overview cam; wheel through RDP often ruins it.
      int runX = r.Left + 140;
      int runY = r.Top + 255;
      Click(runX, runY);

      GetWindowRect(h, out r);
      Console.WriteLine("TITLE=" + t);
      Console.WriteLine("HWND=" + h.ToInt64());
      Console.WriteLine(string.Format("RECT={0},{1},{2},{3}", r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top));
      Console.WriteLine("FRAMED=1");
      return 0;
    }
    Console.WriteLine("NOT_FOUND");
    return 1;
  }
}
