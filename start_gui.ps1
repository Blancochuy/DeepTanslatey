# Quick Start Script - GUI Mode
# Double-click este archivo o ejecuta: .\start_gui.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Audio Transcription & Translation" -ForegroundColor Cyan
Write-Host "  GUI Mode" -ForegroundColor Cyan
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
if (Test-Path ".env") {
    Write-Host "[INFO] .env file found" -ForegroundColor Green
} else {
    Write-Host "[WARN] .env file not found" -ForegroundColor Yellow
    Write-Host "       Create a .env file with:" -ForegroundColor Yellow
    Write-Host "       DEEPGRAM_API_KEY=your_key" -ForegroundColor Yellow
    Write-Host ""
    
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

Write-Host ""
Write-Host "[INFO] Starting GUI..." -ForegroundColor Green
Write-Host ""

# Start the GUI
python main_new.py --gui

Write-Host ""
Write-Host "[INFO] GUI closed" -ForegroundColor Green
