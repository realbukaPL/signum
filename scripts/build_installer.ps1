# Buduje aplikację (PyInstaller) i instalator Windows (Inno Setup).
# Użycie (z katalogu głównego repozytorium):
#   powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

# Wersja z jednego źródła prawdy: src/signum/__init__.py
$version = & $python -c "import signum; print(signum.__version__)"
Write-Host "=== Signum $version ===" -ForegroundColor Cyan

Write-Host "[1/3] PyInstaller (dist\Signum)..." -ForegroundColor Cyan
& $python -m PyInstaller (Join-Path $root "packaging\signum.spec") `
    --noconfirm --distpath (Join-Path $root "dist") --workpath (Join-Path $root "build")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller zakończył się błędem" }

Write-Host "[2/3] Test dymny zbudowanego exe..." -ForegroundColor Cyan
$exe = Join-Path $root "dist\Signum\Signum.exe"
if (-not (Test-Path $exe)) { throw "Brak $exe" }
$smoke = Start-Process -FilePath $exe -ArgumentList "--self-test" -Wait -PassThru -WindowStyle Hidden
if ($smoke.ExitCode -ne 0) {
    throw "Test spakowanego runtime'u zakończył się kodem $($smoke.ExitCode)"
}

Write-Host "[3/3] Inno Setup..." -ForegroundColor Cyan
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Nie znaleziono ISCC.exe — zainstaluj Inno Setup 6" }

& $iscc (Join-Path $root "installer\signum.iss") /DMyAppVersion=$version
if ($LASTEXITCODE -ne 0) { throw "ISCC zakończył się błędem" }

$setup = Join-Path $root "installer\output\Signum-Setup-$version.exe"
Write-Host "Gotowe: $setup" -ForegroundColor Green
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash
Write-Host "SHA-256: $hash" -ForegroundColor Green
$signature = Get-AuthenticodeSignature -LiteralPath $setup
if ($signature.Status -ne "Valid") {
    Write-Warning "Instalator nie ma ważnego podpisu Authenticode. Nie publikuj go jako oficjalnego wydania bez podpisania certyfikatem wydawcy."
}
