# Windows System Validation Script for H.264 Streaming Server
# Checks if all prerequisites are available

Write-Host "H.264 Streaming Server - System Validation" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "✗ Python not found or not in PATH" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "✗ Python not found or not in PATH" -ForegroundColor Red
    $allGood = $false
}

# Check FFmpeg
Write-Host "Checking FFmpeg..." -ForegroundColor Yellow
try {
    $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ FFmpeg found: $($ffmpegVersion -replace 'ffmpeg version ', '')" -ForegroundColor Green
    } else {
        Write-Host "✗ FFmpeg not found or not in PATH" -ForegroundColor Red
        Write-Host "  Download from: https://ffmpeg.org/download.html" -ForegroundColor Gray
        $allGood = $false
    }
} catch {
    Write-Host "✗ FFmpeg not found or not in PATH" -ForegroundColor Red
    Write-Host "  Download from: https://ffmpeg.org/download.html" -ForegroundColor Gray
    $allGood = $false
}

# Check Docker (optional)
Write-Host "Checking Docker (optional)..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
        
        # Check if Docker daemon is running
        try {
            docker info 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Docker daemon is running" -ForegroundColor Green
            } else {
                Write-Host "⚠ Docker is installed but daemon is not running" -ForegroundColor Yellow
                Write-Host "  Start Docker Desktop to use containerized deployment" -ForegroundColor Gray
            }
        } catch {
            Write-Host "⚠ Docker is installed but daemon is not running" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠ Docker not found (optional for local development)" -ForegroundColor Yellow
        Write-Host "  Install Docker Desktop for containerized deployment" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠ Docker not found (optional for local development)" -ForegroundColor Yellow
    Write-Host "  Install Docker Desktop for containerized deployment" -ForegroundColor Gray
}

# Check if server files exist
Write-Host "Checking project files..." -ForegroundColor Yellow
$requiredFiles = @(
    "direct_stream_server.py",
    "start_server.bat",
    "build.ps1",
    "Dockerfile"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✓ $file found" -ForegroundColor Green
    } else {
        Write-Host "✗ $file missing" -ForegroundColor Red
        $allGood = $false
    }
}

# Check if videos directory exists
if (Test-Path "videos") {
    Write-Host "✓ videos directory found" -ForegroundColor Green
    
    $videoFiles = Get-ChildItem -Path "videos" -Include "*.mp4", "*.mkv", "*.avi", "*.mov" -File
    if ($videoFiles.Count -gt 0) {
        Write-Host "✓ Found $($videoFiles.Count) video file(s) in videos directory" -ForegroundColor Green
        foreach ($video in $videoFiles) {
            Write-Host "  - $($video.Name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠ No video files found in videos directory" -ForegroundColor Yellow
        Write-Host "  Add video files to test streaming" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ videos directory not found" -ForegroundColor Yellow
    Write-Host "  Run: .\build.ps1 setup (or manually create videos folder)" -ForegroundColor Gray
}

# Check port availability
Write-Host "Checking port 8080 availability..." -ForegroundColor Yellow
try {
    $portInUse = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "⚠ Port 8080 is currently in use" -ForegroundColor Yellow
        Write-Host "  Use --port parameter to specify a different port" -ForegroundColor Gray
    } else {
        Write-Host "✓ Port 8080 is available" -ForegroundColor Green
    }
} catch {
    Write-Host "✓ Port 8080 appears to be available" -ForegroundColor Green
}

Write-Host ""
Write-Host "Validation Summary:" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "✓ All essential components are ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick start commands:" -ForegroundColor Yellow
    Write-Host "  Local:  python direct_stream_server.py --video videos/your-video.mp4" -ForegroundColor White
    Write-Host "  Docker: .\build.ps1 setup && .\build.ps1 build && .\build.ps1 run" -ForegroundColor White
} else {
    Write-Host "✗ Some components are missing. Please install the required prerequisites." -ForegroundColor Red
}

Write-Host ""
Write-Host "For detailed setup instructions, see README.md" -ForegroundColor Gray
