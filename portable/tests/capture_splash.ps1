param([string]$Launcher,[string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Runtime.InteropServices;
public class CaptureWindow {
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]public static extern IntPtr FindWindow(string cls,string title);
 [DllImport("user32.dll")]public static extern bool GetWindowRect(IntPtr window,out RECT rect);
 public struct RECT {public int Left,Top,Right,Bottom;}
}
'@
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$process=Start-Process -FilePath $Launcher -ArgumentList '--splash-demo-ms','4500' -PassThru
try {
 foreach($i in 0..2){
  Start-Sleep -Milliseconds 500
  $window=[CaptureWindow]::FindWindow('DSComparePortableSplash',$null)
  if($window -eq [IntPtr]::Zero){throw 'Startup window not created'}
  $rect=New-Object CaptureWindow+RECT
  if(-not [CaptureWindow]::GetWindowRect($window,[ref]$rect)){throw 'Cannot inspect startup window'}
  $bitmap=New-Object Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
  $graphics=[Drawing.Graphics]::FromImage($bitmap)
  try {$graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,$bitmap.Size);$bitmap.Save((Join-Path $Output "startup-$i.png"),[Drawing.Imaging.ImageFormat]::Png)}finally{$graphics.Dispose();$bitmap.Dispose()}
 }
 $process.WaitForExit();if($process.ExitCode -ne 0){throw 'Startup window demo failed'}
}finally{if(-not $process.HasExited){$process.Kill()}}
Write-Host 'NATIVE_SPLASH_WINDOW_PASS'
