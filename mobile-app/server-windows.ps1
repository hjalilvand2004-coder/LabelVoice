# راه‌انداز بدون پایتون برای ویندوز — سرور HTTP محلی خیلی سبک با PowerShell
# (TcpListener؛ به هیچ نصب یا دسترسی مدیریتی نیاز ندارد)
# استفاده: دابل‌کلیک روی «شروع-در-ویندوز.bat»
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# یافتن پورت آزاد
$port = $null
foreach ($p in 8765..8775) {
  $c = $null
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', $p)
    $c.Close()
  } catch { $port = $p; break } finally { if ($c) { $c.Dispose() } }
}
if (-not $port) { Write-Host 'هیچ پورت آزادی یافت نشد.'; exit 1 }

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
Write-Host ("برچسب‌خوان موبایل روی http://127.0.0.1:{0}/ در حال اجراست — برای بستن، این پنجره را ببندید." -f $port)
Start-Process ("http://127.0.0.1:{0}/" -f $port)

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

    # مسیر بدون query و بدون پیمایش دایرکتوری
    $path = [Uri]::UnescapeDataString(($rawPath -split '\?')[0]) -replace '/', '\'
    if ($path -eq '\' -or $path -eq '') { $path = '\index.html' }
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
      $body = $utf8.GetBytes('404 Not Found')
      $hdr = $utf8.GetBytes("HTTP/1.1 404 Not Found`r`nContent-Type: text/plain; charset=utf-8`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n")
      $stream.Write($hdr, 0, $hdr.Length)
      $stream.Write($body, 0, $body.Length)
    }
  } catch {
    Write-Host ("خطای پردازش درخواست: {0}" -f $_.Exception.Message)
  } finally {
    $client.Close()
  }
}
