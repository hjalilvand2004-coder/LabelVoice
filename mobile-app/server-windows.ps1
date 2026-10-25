# ============================================================
#  LabelVoice - Smart Label Reader (Portable) - Windows launcher
#  Lightweight local HTTP server built on TcpListener.
#  No Python, no PyQt, no installation, no admin rights.
#
#  Start:  double-click "START-WINDOWS.bat"
#  Stop :  close this console window (or press Ctrl+C)
#
#  NOTE: console messages are English ON PURPOSE.
#  Windows PowerShell 5.1 parses .ps1 files WITHOUT a BOM using the
#  legacy ANSI code page, so non-ASCII text breaks the parser.
#  A pure-ASCII script runs on every Windows, in every language.
#  (The web app itself is fully Persian / RTL.)
# ============================================================

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $root

# ---- v2.8.0: version banner + outdated-copy check (pure ASCII on purpose) ----
# Why: users kept launching OLD extracted folders via START-WINDOWS.bat and
# reported "the new feature is missing". The folder version is shown and
# compared with the latest GitHub release; on mismatch the download page
# opens automatically so the user can grab the current ZIP.
$appVersion = 'unknown'
$verFile = Join-Path $root 'VERSION.txt'
if (Test-Path $verFile) {
  $appVersion = (Get-Content $verFile -TotalCount 1).Trim()
}
Write-Host ''
Write-Host ('  Folder version : v' + $appVersion)
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $latest = Invoke-RestMethod -Uri 'https://api.github.com/repos/hjalilvand2004-coder/LabelVoice/releases/latest' -TimeoutSec 6 -Headers @{ 'User-Agent' = 'LabelVoice-Launcher' }
  $latestTag = $latest.tag_name
  Write-Host ('  Latest release : ' + $latestTag)
  if ($latestTag -and ($latestTag -ne ('v' + $appVersion))) {
    Write-Host ''
    Write-Host '  ===================================================='
    Write-Host '   WARNING: THIS COPY IS OUTDATED.'
    Write-Host '   Newer features (e.g. the OpenCV steps viewer and'
    Write-Host '   the raw OCR reading panel) are MISSING here.'
    Write-Host ('   Please download version ' + $latestTag + ' and extract it to')
    Write-Host '   a NEW folder, then run START-WINDOWS.bat from there:'
    Write-Host '   https://github.com/hjalilvand2004-coder/LabelVoice/releases/latest'
    Write-Host '   (opening the download page in your browser...)'
    Write-Host '  ==================================================== '
    try { Start-Process 'https://github.com/hjalilvand2004-coder/LabelVoice/releases/latest' } catch {}
  }
} catch {
  Write-Host '  Latest release : (offline - update check skipped)'
}
Write-Host ''

# ---- find a free port in 8765..8775 ------------------------
$port = $null
foreach ($p in 8765..8775) {
  $c = $null
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', $p)
    $c.Close()
  } catch { $port = $p; break } finally { if ($c) { $c.Dispose() } }
}
if (-not $port) { Write-Host 'No free port found (8765..8775).'; exit 1 }

$mime = @{
  '.html' = 'text/html; charset=utf-8'
  '.js'   = 'text/javascript; charset=utf-8'
  '.css'  = 'text/css; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'
  '.webmanifest' = 'application/manifest+json; charset=utf-8'
  '.png'  = 'image/png'
  '.jpg'  = 'image/jpeg'
  '.jpeg' = 'image/jpeg'
  '.svg'  = 'image/svg+xml'
  '.ico'  = 'image/x-icon'
  '.wasm' = 'application/wasm'
  '.gz'   = 'application/gzip'
  '.ttf'  = 'font/ttf'
  '.woff' = 'font/woff'
  '.woff2'= 'font/woff2'
}

$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
$listener.Start()
Write-Host '============================================'
Write-Host (' LabelVoice is running:  http://127.0.0.1:{0}/' -f $port)
Write-Host ' Keep this window OPEN while using the app.'
Write-Host ' Closing this window stops the server.'
Write-Host '============================================'
Start-Process ('http://127.0.0.1:{0}/' -f $port)

$utf8 = New-Object System.Text.UTF8Encoding($false)
while ($true) {
  $client = $listener.AcceptTcpClient()
  try {
    $stream = $client.GetStream()
    $stream.ReadTimeout = 5000
    $buf = New-Object byte[] 8192
    $sb = New-Object System.Text.StringBuilder
    do {
      $n = $stream.Read($buf, 0, $buf.Length)
      if ($n -le 0) { break }
      [void]$sb.Append($utf8.GetString($buf, 0, $n))
    } while (-not $sb.ToString().Contains("`r`n`r`n") -and $sb.Length -lt 32768)

    $reqLine = ($sb.ToString() -split "`r`n")[0]
    if (-not $reqLine) { $client.Close(); continue }
    $parts = $reqLine -split ' '
    $method = $parts[0]
    $rawPath = if ($parts.Count -gt 1) { $parts[1] } else { '/' }

    if ($method -notin @('GET', 'HEAD')) {
      $hdr = $utf8.GetBytes("HTTP/1.1 405 Method Not Allowed`r`nContent-Length: 0`r`nConnection: close`r`n`r`n")
      $stream.Write($hdr, 0, $hdr.Length)
      $client.Close(); continue
    }

    # strip query string; block directory traversal
    $path = [Uri]::UnescapeDataString(($rawPath -split '\?')[0]) -replace '/', '\'
    if ($path -eq '\' -or $path -eq '') {
      # v1.8.3 fix: root index may live in different layouts (portable ZIP = webapp/index.html)
      $path = '\index.html'
      foreach ($cand in @('\index.html', '\webapp\index.html', '\START-HERE.html')) {
        $candFull = [IO.Path]::GetFullPath((Join-Path $root $cand.TrimStart('\')))
        if (Test-Path -LiteralPath $candFull -PathType Leaf) { $path = $cand; break }
      }
    }
    $full = [IO.Path]::GetFullPath((Join-Path $root $path.TrimStart('\')))
    if (-not $full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
      $hdr = $utf8.GetBytes("HTTP/1.1 403 Forbidden`r`nContent-Length: 0`r`nConnection: close`r`n`r`n")
      $stream.Write($hdr, 0, $hdr.Length)
      $client.Close(); continue
    }

    if (Test-Path -LiteralPath $full -PathType Leaf) {
      $ext = [IO.Path]::GetExtension($full).ToLowerInvariant()
      $type = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'application/octet-stream' }
      $bytes = [IO.File]::ReadAllBytes($full)
      $hdrText = "HTTP/1.1 200 OK`r`nContent-Type: $type`r`nContent-Length: $($bytes.Length)`r`nCache-Control: no-cache`r`nConnection: close`r`n`r`n"
      $hdr = $utf8.GetBytes($hdrText)
      $stream.Write($hdr, 0, $hdr.Length)
      if ($method -eq 'GET') { $stream.Write($bytes, 0, $bytes.Length) }
    } else {
      # v1.8.3 fix: friendly 404 page (pure ASCII per design note) with instant redirect
      $body = $utf8.GetBytes('<!DOCTYPE html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/index.html"><title>LabelVoice</title></head><body style="font-family:Tahoma,sans-serif;text-align:center;padding:48px;background:#f4f7fb;color:#1a2b3c"><h2>Page not found - redirecting to the app...</h2><p><a href="/index.html">Open the app (index.html)</a></p></body></html>')
      $hdr = $utf8.GetBytes("HTTP/1.1 404 Not Found`r`nContent-Type: text/html; charset=utf-8`r`nContent-Length: $($body.Length)`r`nCache-Control: no-cache`r`nConnection: close`r`n`r`n")
      $stream.Write($hdr, 0, $hdr.Length)
      $stream.Write($body, 0, $body.Length)
    }
  } catch {
    Write-Host ('Request error: {0}' -f $_.Exception.Message)
  } finally {
    $client.Close()
  }
}

