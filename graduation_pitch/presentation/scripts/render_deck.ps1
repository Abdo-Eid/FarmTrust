param(
  [string]$InputHtml = "farmtrust_deck.html",
  [string]$OutputPdf = "output\pdf\farmtrust_deck.pdf",
  [string]$CompactPdf = "output\pdf\farmtrust_deck_compact.pdf",
  [int]$CompactDpi = 150,
  [ValidateRange(1,100)]
  [int]$JpegQuality = 88,
  [switch]$NoCompact
)

$ErrorActionPreference = "Stop"

function Resolve-FromRoot([string]$Path) {
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }
  return (Join-Path $script:Root $Path)
}

function Get-FirstExistingPath([string[]]$Paths) {
  foreach ($path in $Paths) {
    if ($path -and (Test-Path -LiteralPath $path)) {
      return $path
    }
  }
  return $null
}

function Get-CommandPathOrNull([string]$Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

function Get-FreeTcpPort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  $port = $listener.LocalEndpoint.Port
  $listener.Stop()
  return $port
}

function Invoke-HttpStringWithRetry($Client, [string]$Url) {
  for ($try = 1; $try -le 4; $try++) {
    try {
      return $Client.GetStringAsync($Url).GetAwaiter().GetResult()
    } catch {
      if ($try -eq 4) { throw }
      Start-Sleep -Milliseconds (400 * $try)
    }
  }
}

function Invoke-HttpBytesWithRetry($Client, [string]$Url) {
  for ($try = 1; $try -le 4; $try++) {
    try {
      return $Client.GetByteArrayAsync($Url).GetAwaiter().GetResult()
    } catch {
      if ($try -eq 4) { throw }
      Start-Sleep -Milliseconds (400 * $try)
    }
  }
}

function Get-EmbeddedGoogleFontsCss([string]$FontUrl) {
  $client = [System.Net.Http.HttpClient]::new()
  $client.Timeout = [TimeSpan]::FromSeconds(60)
  $client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149 Safari/537.36")
  try {
    $fontCss = Invoke-HttpStringWithRetry $client $FontUrl
    $urls = [regex]::Matches($fontCss, "url\((https://[^)]+\.woff2)\)") |
      ForEach-Object { $_.Groups[1].Value } |
      Sort-Object -Unique

    foreach ($url in $urls) {
      $bytes = Invoke-HttpBytesWithRetry $client $url
      $dataUrl = "url(`"data:font/woff2;base64,$([Convert]::ToBase64String($bytes))`")"
      $fontCss = $fontCss.Replace("url($url)", $dataUrl)
    }

    return @{
      Css = $fontCss
      Count = $urls.Count
    }
  } finally {
    $client.Dispose()
  }
}

function New-PrintHtml([string]$InputPath, [string]$OutputPath) {
  $html = Get-Content -LiteralPath $InputPath -Raw
  $fontLinkPattern = '<link\s+href="(https://fonts\.googleapis\.com/css2\?[^"]+)"\s+rel="stylesheet"\s*/?>'
  $fontUrlMatch = [regex]::Match($html, $fontLinkPattern)

  if ($fontUrlMatch.Success) {
    Write-Host "Embedding Google Fonts..."
    $fontData = Get-EmbeddedGoogleFontsCss $fontUrlMatch.Groups[1].Value
    $fontBlock = "`n<style id=`"embedded-google-fonts-for-pdf`">`n$($fontData.Css)`n</style>`n"
    $html = [regex]::Replace($html, '<link\s+rel="preconnect"\s+href="https://fonts\.googleapis\.com"\s*/?>\s*', "")
    $html = [regex]::Replace($html, '<link\s+rel="preconnect"\s+href="https://fonts\.gstatic\.com"\s+crossorigin\s*/?>\s*', "")
    $html = [regex]::Replace($html, $fontLinkPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $fontBlock }, 1)
    Write-Host "Embedded $($fontData.Count) font files."
  } else {
    Write-Warning "No Google Fonts stylesheet link found. Rendering with fonts already available to Chrome."
  }

  $printCss = @'

/* --- PDF render overrides injected in temporary copy only --- */
@media print {
  @page { size: 16in 9in; margin: 0; }
  html, body {
    width: 16in;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: #000 !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  .deck,
  .deck.present,
  .deck.overview {
    position: static !important;
    inset: auto !important;
    display: block !important;
    padding: 0 !important;
    margin: 0 !important;
    width: 16in !important;
    background: #000 !important;
  }
  .deck.present .slide,
  .deck.present .slide:not(.is-active),
  .deck.present .slide.is-active,
  .deck.overview .slide,
  .slide {
    display: block !important;
    position: relative !important;
    width: 16in !important;
    height: 9in !important;
    aspect-ratio: auto !important;
    margin: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    outline: 0 !important;
    break-after: page !important;
    page-break-after: always !important;
    animation: none !important;
  }
  .slide:last-of-type {
    break-after: auto !important;
    page-break-after: auto !important;
  }
  .navbar { display: none !important; }
}
'@

  if ($html -notmatch "</style>") {
    throw "Could not find </style> in $InputPath"
  }

  $html = $html -replace "</style>", ($printCss + "`n</style>")
  Set-Content -LiteralPath $OutputPath -Value $html -Encoding UTF8
}

function Copy-RenderAssets([string]$RenderDir) {
  foreach ($dir in @("assets", "imgs")) {
    $source = Join-Path $Root $dir
    if (Test-Path -LiteralPath $source) {
      Copy-Item -LiteralPath $source -Destination (Join-Path $RenderDir $dir) -Recurse -Force
    }
  }
}

function Invoke-ChromePrintToPdf([string]$ChromePath, [string]$NodePath, [string]$PrintHtmlPath, [string]$OutPdfPath) {
  $renderDir = Split-Path -Parent $PrintHtmlPath
  $scriptPath = Join-Path $renderDir "print_cdp.js"
  $port = Get-FreeTcpPort

  $nodeScript = @'
const fs = require('fs');
const http = require('http');
const [,, port, targetUrl, outPdf] = process.argv;

function requestJson(method, url) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, {method}, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { reject(new Error(data)); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

(async () => {
  const base = `http://127.0.0.1:${port}`;
  const tab = await requestJson('PUT', `${base}/json/new?${encodeURIComponent(targetUrl)}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  let loadResolve;
  const loadPromise = new Promise(resolve => loadResolve = resolve);

  ws.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (msg.method === 'Page.loadEventFired' && loadResolve) loadResolve();
    if (msg.id && pending.has(msg.id)) {
      const callbacks = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? callbacks.reject(new Error(JSON.stringify(msg.error))) : callbacks.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  function send(method, params = {}) {
    const callId = ++id;
    ws.send(JSON.stringify({id: callId, method, params}));
    return new Promise((resolve, reject) => pending.set(callId, {resolve, reject}));
  }

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setEmulatedMedia', {media: 'print'});
  await send('Page.navigate', {url: targetUrl});
  await loadPromise;

  const fonts = await send('Runtime.evaluate', {
    awaitPromise: true,
    returnByValue: true,
    expression: `(async () => {
      await document.fonts.ready;
      await new Promise(resolve => setTimeout(resolve, 1000));
      return {
        archivo: document.fonts.check('80px "Archivo Black"', 'THANK'),
        yellowtail: document.fonts.check('80px "Yellowtail"', 'You'),
        plexSans: document.fonts.check('20px "IBM Plex Sans"', 'FarmTrust'),
        plexMono: document.fonts.check('20px "IBM Plex Mono"', 'FarmTrust'),
        status: document.fonts.status
      };
    })()`
  });
  console.log('Font status: ' + JSON.stringify(fonts.result.value));

  const pdf = await send('Page.printToPDF', {
    landscape: true,
    displayHeaderFooter: false,
    printBackground: true,
    preferCSSPageSize: true,
    paperWidth: 16,
    paperHeight: 9,
    marginTop: 0,
    marginRight: 0,
    marginBottom: 0,
    marginLeft: 0,
    scale: 1
  });

  fs.writeFileSync(outPdf, Buffer.from(pdf.data, 'base64'));
  await send('Page.close').catch(() => {});
  ws.close();
})();
'@

  Set-Content -LiteralPath $scriptPath -Value $nodeScript -Encoding UTF8

  $userDataDir = Join-Path $renderDir "chrome-profile"
  New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null

  $chromeArgs = @(
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--allow-file-access-from-files",
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=$port",
    "--user-data-dir=$userDataDir",
    "about:blank"
  )

  $chrome = Start-Process -FilePath $ChromePath -ArgumentList $chromeArgs -PassThru -WindowStyle Hidden
  try {
    $ready = $false
    for ($i = 0; $i -lt 80; $i++) {
      try {
        Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/version" -TimeoutSec 1 | Out-Null
        $ready = $true
        break
      } catch {
        Start-Sleep -Milliseconds 250
      }
    }
    if (-not $ready) {
      throw "Chrome remote debugging did not start on port $port"
    }

    $targetUrl = ([System.Uri](Resolve-Path -LiteralPath $PrintHtmlPath).Path).AbsoluteUri
    & $NodePath $scriptPath $port $targetUrl $OutPdfPath
    if ($LASTEXITCODE -ne 0) {
      throw "Node CDP print script failed with exit code $LASTEXITCODE"
    }
  } finally {
    if ($chrome -and -not $chrome.HasExited) {
      Stop-Process -Id $chrome.Id -Force
    }
  }
}

function New-CompactPdf([string]$SourcePdf, [string]$OutPdf, [string]$PpmPath, [string]$PythonPath, [int]$Dpi, [int]$Quality) {
  $compactDir = Join-Path $Root "tmp\pdfs\compact"
  if (Test-Path -LiteralPath $compactDir) {
    Remove-Item -LiteralPath $compactDir -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $compactDir | Out-Null

  & $PpmPath -jpeg -jpegopt "quality=$Quality,progressive=y,optimize=y" -r $Dpi $SourcePdf (Join-Path $compactDir "slide")
  if ($LASTEXITCODE -ne 0) {
    throw "pdftoppm failed while creating compact slide images"
  }

  $pythonScript = @'
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

img_dir = Path(sys.argv[1])
out_pdf = Path(sys.argv[2])
images = sorted(img_dir.glob("slide-*.jpg"))
if not images:
    raise SystemExit("No slide JPEGs found")

page_w, page_h = 16 * 72, 9 * 72
c = canvas.Canvas(str(out_pdf), pagesize=(page_w, page_h), pageCompression=1)
for img_path in images:
    c.drawImage(ImageReader(str(img_path)), 0, 0, width=page_w, height=page_h, preserveAspectRatio=False, anchor="c")
    c.showPage()
c.save()
print(f"wrote {out_pdf} from {len(images)} images")
'@

  $pythonScriptPath = Join-Path $compactDir "make_compact_pdf.py"
  Set-Content -LiteralPath $pythonScriptPath -Value $pythonScript -Encoding UTF8
  & $PythonPath $pythonScriptPath $compactDir $OutPdf
  if ($LASTEXITCODE -ne 0) {
    throw "Python compact PDF builder failed with exit code $LASTEXITCODE"
  }
}

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$InputHtmlPath = Resolve-FromRoot $InputHtml
$OutputPdfPath = Resolve-FromRoot $OutputPdf
$CompactPdfPath = Resolve-FromRoot $CompactPdf

if (-not (Test-Path -LiteralPath $InputHtmlPath)) {
  throw "Input HTML not found: $InputHtmlPath"
}

$runtimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$ChromePath = Get-FirstExistingPath @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)
$NodePath = Get-FirstExistingPath @(
  (Join-Path $runtimeRoot "node\bin\node.exe"),
  (Get-CommandPathOrNull "node")
)
$PythonPath = Get-FirstExistingPath @(
  (Join-Path $runtimeRoot "python\python.exe"),
  (Get-CommandPathOrNull "python")
)
$PdfInfoPath = Get-FirstExistingPath @(
  (Join-Path $runtimeRoot "native\poppler\Library\bin\pdfinfo.exe"),
  (Get-CommandPathOrNull "pdfinfo")
)
$PdfToPpmPath = Get-FirstExistingPath @(
  (Join-Path $runtimeRoot "native\poppler\Library\bin\pdftoppm.exe"),
  (Get-CommandPathOrNull "pdftoppm")
)

foreach ($tool in @(
  @{ Name = "Chrome or Edge"; Path = $ChromePath },
  @{ Name = "Node.js"; Path = $NodePath },
  @{ Name = "Python"; Path = $PythonPath },
  @{ Name = "pdfinfo"; Path = $PdfInfoPath },
  @{ Name = "pdftoppm"; Path = $PdfToPpmPath }
)) {
  if (-not $tool.Path) {
    throw "Missing required tool: $($tool.Name)"
  }
}

$slideCount = ([regex]::Matches((Get-Content -LiteralPath $InputHtmlPath -Raw), '<section class="slide')).Count
Write-Host "Rendering $slideCount slides from $InputHtmlPath"

$tmpDir = Join-Path $Root "tmp\pdfs"
$renderDir = Join-Path $env:TEMP "farmtrust_pdf_render"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
if (Test-Path -LiteralPath $renderDir) {
  Remove-Item -LiteralPath $renderDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPdfPath -Parent) | Out-Null

$printHtmlPath = Join-Path $tmpDir "farmtrust_deck.print.html"
New-PrintHtml $InputHtmlPath $printHtmlPath

$renderHtmlPath = Join-Path $renderDir "farmtrust_deck.print.html"
Copy-Item -LiteralPath $printHtmlPath -Destination $renderHtmlPath -Force
Copy-RenderAssets $renderDir

$tempFullPdf = Join-Path $renderDir "farmtrust_deck.pdf"
Invoke-ChromePrintToPdf $ChromePath $NodePath $renderHtmlPath $tempFullPdf
Copy-Item -LiteralPath $tempFullPdf -Destination $OutputPdfPath -Force

Write-Host "Full PDF:"
& $PdfInfoPath $OutputPdfPath | Select-String -Pattern "^Pages:|^Page size:|^File size:"

if (-not $NoCompact) {
  New-Item -ItemType Directory -Force -Path (Split-Path $CompactPdfPath -Parent) | Out-Null
  New-CompactPdf $OutputPdfPath $CompactPdfPath $PdfToPpmPath $PythonPath $CompactDpi $JpegQuality
  Write-Host "Compact PDF:"
  & $PdfInfoPath $CompactPdfPath | Select-String -Pattern "^Pages:|^Page size:|^File size:"
}

Write-Host "Done."
Write-Host "Full:    $OutputPdfPath"
if (-not $NoCompact) {
  Write-Host "Compact: $CompactPdfPath"
}
