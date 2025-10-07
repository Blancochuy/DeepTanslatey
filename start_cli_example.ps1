# Quick Start Script - CLI Mode with AirPods
# Ejemplo: Transcribir de Inglés a Español usando AirPods

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Audio Transcription & Translation" -ForegroundColor Cyan
Write-Host "  CLI Mode - AirPods Example" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Green
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "[WARN] Virtual environment not found" -ForegroundColor Yellow
    Write-Host "[INFO] Using system Python" -ForegroundColor Yellow
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found" -ForegroundColor Red
    Write-Host "        Create a .env file with:" -ForegroundColor Yellow
    Write-Host "        DEEPGRAM_API_KEY=your_key" -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "[INFO] Configuration:" -ForegroundColor Green
Write-Host "       Device: AirPods (or similar)" -ForegroundColor White
Write-Host "       Source: English (en)" -ForegroundColor White
Write-Host "       Target: Spanish (es)" -ForegroundColor White
Write-Host "       Translator: Google Translate" -ForegroundColor White
Write-Host ""

# Start transcription
Write-Host "[INFO] Starting transcription..." -ForegroundColor Green
Write-Host "       Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python main.py --device airpods --src en --tgt es --translator google

Write-Host ""
Write-Host "[INFO] Transcription stopped" -ForegroundColor Green
