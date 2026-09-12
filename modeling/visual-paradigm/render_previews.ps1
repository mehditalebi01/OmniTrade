param(
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"
$modelRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$previewRoot = Join-Path $modelRoot "previews"
$profileRoot = "D:\Applications\ChromeHeadlessOmniTrade"

if (-not (Test-Path -LiteralPath $Chrome)) {
    throw "Chrome was not found at $Chrome"
}

Get-ChildItem -LiteralPath $previewRoot -File | Where-Object { $_.Name -match '^[FU].*\.svg$' } | ForEach-Object {
    $source = Get-Content -LiteralPath $_.FullName -Raw
    if ($source -notmatch '<svg[^>]+width="(?<width>\d+)"[^>]+height="(?<height>\d+)"') {
        throw "Cannot read the SVG canvas size: $($_.FullName)"
    }
    $width = [int]$Matches.width
    $height = [int]$Matches.height
    $target = [IO.Path]::ChangeExtension($_.FullName, ".png")
    $uri = [Uri]::new($_.FullName).AbsoluteUri
    $profile = "$profileRoot-$($_.BaseName)"
    & $Chrome --headless=new --disable-gpu --hide-scrollbars --no-pdf-header-footer `
        --user-data-dir="$profile" --window-size="$width,$height" --screenshot="$target" $uri | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $target)) {
        throw "Chrome failed to render $($_.Name)"
    }
}

Get-ChildItem -LiteralPath $previewRoot -File | Where-Object { $_.Name -match '^[FU].*\.png$' } | Select-Object Name, Length
