param([string]$Launcher,[string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Runtime.InteropServices;
public class CaptureWindow {
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]public static extern IntPtr FindWindow(string cls,IntPtr title);
 [DllImport("user32.dll")]public static extern bool GetWindowRect(IntPtr window,out RECT rect);
 public struct RECT {public int Left,Top,Right,Bottom;}
}
'@
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$process=Start-Process -FilePath $Launcher -ArgumentList '--splash-demo-ms','6000' -PassThru
try {
 $deadline=[DateTime]::UtcNow.AddSeconds(20)
 do {
  $window=[CaptureWindow]::FindWindow('DSComparePortableSplash',[IntPtr]::Zero)
  if($window -ne [IntPtr]::Zero){break}
  if($process.HasExited){throw "Startup demo exited before capture: $($process.ExitCode)"}
  Start-Sleep -Milliseconds 100
 } while([DateTime]::UtcNow -lt $deadline)
 if($window -eq [IntPtr]::Zero){throw 'Startup window not created within 20 seconds'}
 foreach($i in 0..2){
  Start-Sleep -Milliseconds 400
  $rect=New-Object CaptureWindow+RECT
  if(-not [CaptureWindow]::GetWindowRect($window,[ref]$rect)){throw 'Cannot inspect startup window'}
  $bitmap=New-Object Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
  $graphics=[Drawing.Graphics]::FromImage($bitmap)
  try {$graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,$bitmap.Size);$bitmap.Save((Join-Path $Output "startup-$i.png"),[Drawing.Imaging.ImageFormat]::Png)}finally{$graphics.Dispose();$bitmap.Dispose()}
 }
 $process.WaitForExit();if($process.ExitCode -ne 0){throw 'Startup window demo failed'}
}finally{if(-not $process.HasExited){$process.Kill()}}
Write-Host 'NATIVE_SPLASH_WINDOW_PASS'
