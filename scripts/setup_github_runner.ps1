<#
.SYNOPSIS
    GitHub Actions Self-Hosted Runner Setup Script for Windows (autochattiktok)
.DESCRIPTION
    Installs and configures a GitHub Actions self-hosted runner on Windows within a Netbird mesh network context.
.EXAMPLE
    .\scripts\setup_github_runner.ps1 -RunnerToken "YOUR_GITHUB_RUNNER_TOKEN"
    .\scripts\setup_github_runner.ps1 -RunnerToken "YOUR_GITHUB_RUNNER_TOKEN" -RunnerName "runner-windows-netbird" -RunnerDir "C:\actions-runner-autochat"
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true, Position=0)]
    [string]$RunnerToken,

    [Parameter(Mandatory=$false, Position=1)]
    [string]$RunnerDir = "C:\actions-runner-autochat",

    [Parameter(Mandatory=$false, Position=2)]
    [string]$RunnerName = "runner-windows-netbird",

    [Parameter(Mandatory=$false)]
    [string]$RepoUrl = "https://github.com/cobacobiy/autochattiktok",

    [Parameter(Mandatory=$false)]
    [string]$RunnerVersion = "2.322.0",

    [Parameter(Mandatory=$false)]
    [string]$Labels = "self-hosted,windows,staging,test,netbird,autochattiktok"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " GitHub Actions Windows Runner Setup (Netbird Network)" -ForegroundColor Cyan
Write-Host " Target Repository : $RepoUrl" -ForegroundColor Yellow
Write-Host " Target Directory  : $RunnerDir" -ForegroundColor Yellow
Write-Host " Runner Name        : $RunnerName" -ForegroundColor Yellow
Write-Host " Runner Labels      : $Labels" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Netbird status if netbird CLI is available
try {
    $netbirdCmd = Get-Command netbird -ErrorAction SilentlyContinue
    if ($netbirdCmd) {
        Write-Host "[+] Checking Netbird connection status..." -ForegroundColor Green
        netbird status
    } else {
        Write-Host "[!] Note: 'netbird' CLI command not found in PATH. Ensure Netbird client is connected." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[!] Could not query Netbird CLI. Continuing runner setup..." -ForegroundColor Yellow
}

# 2. Create runner directory
if (!(Test-Path -Path $RunnerDir)) {
    Write-Host "[+] Creating directory: $RunnerDir" -ForegroundColor Green
    New-Item -ItemType Directory -Path $RunnerDir -Force | Out-Null
}

Set-Location -Path $RunnerDir

# 3. Download and extract runner release
$ZipFile = "actions-runner-win-x64-$RunnerVersion.zip"
$DownloadUrl = "https://github.com/actions/runner/releases/download/v$RunnerVersion/$ZipFile"

if (!(Test-Path -Path "config.cmd")) {
    Write-Host "[+] Downloading GitHub Actions Runner v$RunnerVersion..." -ForegroundColor Green
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipFile -UseBasicParsing

    Write-Host "[+] Extracting runner package..." -ForegroundColor Green
    Expand-Archive -Path $ZipFile -DestinationPath . -Force
    Remove-Item -Path $ZipFile -Force
}

# 4. Configure runner & Install Windows Service
Write-Host "[+] Configuring GitHub Actions Runner & Installing Windows Service..." -ForegroundColor Green
.\config.cmd --url $RepoUrl --token $RunnerToken --name $RunnerName --labels $Labels --work "_work" --runAsService --unattended --replace

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " GitHub Actions Runner installed and started as service successfully!" -ForegroundColor Green
Write-Host " Status Check: Get-Service actions.runner.*" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
