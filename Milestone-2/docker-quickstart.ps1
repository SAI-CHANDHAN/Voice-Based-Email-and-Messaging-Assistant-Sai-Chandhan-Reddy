#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick-start script to build and run the voice assistant in Docker
.DESCRIPTION
    This script automates Docker build and run for the voice-based assistant
.EXAMPLE
    .\docker-quickstart.ps1
#>

param()

$ProjectDir = (Get-Location).ProviderPath
$ImageName = 'voice-assistant:latest'
$ContainerName = 'voice-app'

Write-Host '========================================' -ForegroundColor Cyan
Write-Host 'Voice Assistant Docker Quick-Start' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

# 1) Check docker installed
Write-Host '[1/4] Checking Docker installation...' -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'ERROR: Docker is not installed or not in PATH' -ForegroundColor Red
    Write-Host 'Download Docker Desktop: https://www.docker.com/products/docker-desktop/' -ForegroundColor Yellow
    exit 1
}
try {
    $ver = (& docker --version)
    Write-Host ('✓ Docker found: ' + $ver) -ForegroundColor Green
} catch {
    Write-Host 'WARNING: docker command exists but failed to run' -ForegroundColor Yellow
}
Write-Host ''

# 2) Check daemon
Write-Host '[2/4] Checking Docker daemon...' -ForegroundColor Yellow
try {
    & docker ps > $null 2>&1
    Write-Host '✓ Docker daemon is running' -ForegroundColor Green
} catch {
    Write-Host 'ERROR: Docker daemon is not running' -ForegroundColor Red
    Write-Host 'Start Docker Desktop from Windows Start menu' -ForegroundColor Yellow
    exit 1
}
Write-Host ''

# 3) Build image
Write-Host '[3/4] Building Docker image (this may take a few minutes)...' -ForegroundColor Yellow
& docker build -t $ImageName .
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: Docker build failed' -ForegroundColor Red
    exit 1
}
Write-Host '✓ Image built successfully' -ForegroundColor Green
Write-Host ''

# 4) Stop existing container if present, then run
Write-Host '[4/4] Starting container...' -ForegroundColor Yellow
$ExistingContainer = & docker ps -a --filter "name=$ContainerName" --format '{{.ID}}' 2>$null
if ($ExistingContainer) {
    Write-Host 'Stopping existing container...' -ForegroundColor Gray
    & docker stop $ContainerName > $null 2>&1
    & docker rm $ContainerName > $null 2>&1
}

$InstancePath = Join-Path $ProjectDir 'instance'
if (-not (Test-Path $InstancePath)) { New-Item -ItemType Directory -Path $InstancePath | Out-Null }

# Use simple concatenation for the volume argument to avoid quoting problems
$volArg = $InstancePath + ':/app/instance'
& docker run -p 5000:5000 -v $volArg --name $ContainerName $ImageName

Write-Host ''
Write-Host 'Container stopped. To restart:' -ForegroundColor Cyan
Write-Host ('  docker start ' + $ContainerName) -ForegroundColor Gray
Write-Host ''
