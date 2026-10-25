using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

class FocusMuJoCo {
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)] struct RECT { public int Left, Top, Right, Bottom; }

  static int Main() {
    foreach (var p in Process.GetProcesses()) {
      string t = "";
      try { t = p.MainWindowTitle; } catch { continue; }
      if (string.IsNullOrEmpty(t)) continue;
      if (t.IndexOf("MuJoCo", StringComparison.OrdinalIgnoreCase) < 0) continue;
      IntPtr h = p.MainWindowHandle;
      if (h == IntPtr.Zero) continue;
      ShowWindow(h, 3); // SW_MAXIMIZE
      SetForegroundWindow(h);
      RECT r;
      GetWindowRect(h, out r);
      Console.WriteLine("TITLE=" + t);
      Console.WriteLine("HWND=" + h.ToInt64());
      Console.WriteLine(string.Format("RECT={0},{1},{2},{3}", r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top));
      return 0;
    }
    Console.WriteLine("NOT_FOUND");
    return 1;
  }
}
