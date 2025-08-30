# PowerShell Build Script for H.264 Streaming Server
# Alternative to Makefile for Windows users who prefer native PowerShell

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [string]$Port = "8080",
    [string]$VideoDir = "./videos"
)

$ImageName = "h264-streaming-server"
$ContainerName = "h264-streaming-server"

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  build       - Build the Docker image"
    Write-Host "  run         - Run the container with default settings"
    Write-Host "  run-dev     - Run container in development mode"
    Write-Host "  run-prod    - Run with nginx proxy (production)"
    Write-Host "  stop        - Stop the running container"
    Write-Host "  clean       - Remove container and image"
    Write-Host "  logs        - View container logs"
    Write-Host "  shell       - Get shell access to running container"
    Write-Host "  test        - Test the streaming endpoint"
    Write-Host "  setup       - Create necessary directories"
    Write-Host "  status      - Show container status"
    Write-Host "  health      - Check container health"
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor Yellow
    Write-Host "  .\build.ps1 setup"
    Write-Host "  .\build.ps1 build"
    Write-Host "  .\build.ps1 run"
    Write-Host "  .\build.ps1 test"
}

function Setup-Directories {
    Write-Host "Creating directories..." -ForegroundColor Blue
    
    if (!(Test-Path $VideoDir)) {
        New-Item -ItemType Directory -Path $VideoDir -Force | Out-Null
        Write-Host "Created: $VideoDir" -ForegroundColor Green
    }
    
    if (!(Test-Path "config")) {
        New-Item -ItemType Directory -Path "config" -Force | Out-Null
        Write-Host "Created: config" -ForegroundColor Green
    }
    
    if (!(Test-Path "ssl")) {
        New-Item -ItemType Directory -Path "ssl" -Force | Out-Null
        Write-Host "Created: ssl" -ForegroundColor Green
    }
    
    Write-Host "Setup complete!" -ForegroundColor Green
    Write-Host "Place your video files in $VideoDir/"
    Write-Host "Rename your main video to 'video.mp4' or update the configuration"
}

function Build-Image {
    Write-Host "Building Docker image..." -ForegroundColor Blue
    docker build -t $ImageName .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Build completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
}

function Run-Container {
    Setup-Directories
    Write-Host "Starting container..." -ForegroundColor Blue
    
    # Stop existing container if running
    docker stop $ContainerName 2>$null | Out-Null
    docker rm $ContainerName 2>$null | Out-Null
    
    docker run -d `
        --name $ContainerName `
        -p "${Port}:8080" `
        -v "${VideoDir}:/app/videos:ro" `
        --restart unless-stopped `
        $ImageName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Container started successfully!" -ForegroundColor Green
        Write-Host "Access the stream at: http://localhost:$Port/stream.h264"
    } else {
        Write-Host "Failed to start container!" -ForegroundColor Red
    }
}

function Run-Development {
    Setup-Directories
    Write-Host "Starting development container..." -ForegroundColor Blue
    
    docker run --rm -it `
        --name "$ContainerName-dev" `
        -p "${Port}:8080" `
        -v "${VideoDir}:/app/videos:ro" `
        -v "${PWD}:/app" `
        $ImageName `
        python direct_stream_server.py --video /app/videos/video.mp4 --port 8080
}

function Run-Production {
    Setup-Directories
    Write-Host "Starting production environment..." -ForegroundColor Blue
    docker-compose --profile production up -d
}

function Stop-Container {
    Write-Host "Stopping container..." -ForegroundColor Blue
    docker stop $ContainerName 2>$null | Out-Null
    docker rm $ContainerName 2>$null | Out-Null
    Write-Host "Container stopped" -ForegroundColor Green
}

function Clean-All {
    Write-Host "Cleaning up Docker resources..." -ForegroundColor Blue
    docker stop $ContainerName 2>$null | Out-Null
    docker rm $ContainerName 2>$null | Out-Null
    docker rmi $ImageName 2>$null | Out-Null
    docker-compose down --volumes --remove-orphans 2>$null | Out-Null
    Write-Host "Cleanup completed" -ForegroundColor Green
}

function Show-Logs {
    Write-Host "Showing container logs (Ctrl+C to exit)..." -ForegroundColor Blue
    docker logs -f $ContainerName
}

function Open-Shell {
    Write-Host "Opening shell in container..." -ForegroundColor Blue
    docker exec -it $ContainerName /bin/bash
}

function Test-Endpoint {
    Write-Host "Testing streaming endpoint..." -ForegroundColor Blue
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/stream.h264" -Method Head -TimeoutSec 5
        Write-Host "✓ Server is responding (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "✗ Server not responding: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Test with media players:" -ForegroundColor Yellow
    Write-Host "  ffplay http://localhost:$Port/stream.h264"
    Write-Host "  vlc http://localhost:$Port/stream.h264"
}

function Show-Status {
    Write-Host "Container status:" -ForegroundColor Blue
    docker ps -a --filter name=$ContainerName
    
    Write-Host "`nContainer stats:" -ForegroundColor Blue
    docker stats $ContainerName --no-stream 2>$null
}

function Check-Health {
    Write-Host "Checking container health..." -ForegroundColor Blue
    try {
        docker exec $ContainerName curl -f http://localhost:8080/ 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Health check passed" -ForegroundColor Green
        } else {
            Write-Host "✗ Health check failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { Setup-Directories }
    "build" { Build-Image }
    "run" { Run-Container }
    "run-dev" { Run-Development }
    "run-prod" { Run-Production }
    "stop" { Stop-Container }
    "clean" { Clean-All }
    "logs" { Show-Logs }
    "shell" { Open-Shell }
    "test" { Test-Endpoint }
    "status" { Show-Status }
    "health" { Check-Health }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
