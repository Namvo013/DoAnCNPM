$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDirectory = Join-Path $projectRoot "backend-api"
$python = Join-Path $backendDirectory ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Backend Python environment not found: $python"
}

$internalToken = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
if ($LASTEXITCODE -ne 0 -or -not $internalToken) {
    throw "Could not generate the internal service token."
}

$env:INTERNAL_SERVICE_TOKEN = $internalToken
$env:PUBLIC_BASE_URL = "http://localhost:8000"
$env:PUBLIC_APP_URL = "http://localhost:8000"
$powershellExecutable = Join-Path $PSHOME "powershell.exe"

function Start-BackendService {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Role,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $env:SERVICE_ROLE = $Role
    $command = "Set-Location -LiteralPath '$backendDirectory'; & '$python' -m uvicorn app.main:app --host 127.0.0.1 --port $Port"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $process = Start-Process `
        -FilePath $powershellExecutable `
        -ArgumentList @("-NoExit", "-EncodedCommand", $encodedCommand) `
        -PassThru
    Write-Host "Started $Role service on port $Port (PID $($process.Id))."
}

Start-BackendService -Role "auth" -Port 8101
Start-Sleep -Seconds 2
Start-BackendService -Role "poi" -Port 8102
Start-BackendService -Role "presence" -Port 8103

$env:AUTH_SERVICE_URL = "http://127.0.0.1:8101"
$env:POI_SERVICE_URL = "http://127.0.0.1:8102"
$env:PRESENCE_SERVICE_URL = "http://127.0.0.1:8103"
Start-BackendService -Role "gateway" -Port 8000

Write-Host ""
Write-Host "Microservices started. Open http://localhost:8000/login.html"
Write-Host "Close each service window or press Ctrl+C in it to stop that service."
