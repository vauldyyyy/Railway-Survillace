# ==========================================
# Phase 2: Mass Dataset Acquisition Script
# ==========================================

Write-Host "Starting automated download of Tier 2 Research Datasets..." -ForegroundColor Cyan

# 1. Provide Kaggle instructions for UCF-Crime
Write-Host "`n[1] UCF-Crime Dataset (Suspicious Behavior / Vandalism)" -ForegroundColor Yellow
Write-Host "To download the massive UCF-Crime dataset via Kaggle API, ensure you have your kaggle.json installed."
Write-Host "Running: kaggle datasets download -d odins0n/ucf-crime-dataset -p ./datasets/raw_videos/ucf_crime --unzip"
try {
    kaggle datasets download -d odins0n/ucf-crime-dataset -p ./datasets/raw_videos/ucf_crime --unzip
} catch {
    Write-Host "Kaggle CLI not installed or missing credentials. Please download manually from: https://www.kaggle.com/datasets/odins0n/ucf-crime-dataset" -ForegroundColor Red
}

# 2. Provide WGET for UCF-QNRF 
Write-Host "`n[2] UCF-QNRF Dataset (High-Density Crowd Counting)" -ForegroundColor Yellow
$qnrf_dir = "./datasets/raw_videos/ucf_qnrf"
New-Item -ItemType Directory -Force -Path $qnrf_dir | Out-Null
Write-Host "Please download the UCF-QNRF dataset manually via the academic portal as it requires authentication:"
Write-Host "Link: https://www.crcv.ucf.edu/data/ucf-qnrf/" -ForegroundColor Cyan

# 3. Provide Instructions for Tier 4 (Pexels) Negative Samples
Write-Host "`n[3] Negative Sample Mining" -ForegroundColor Yellow
Write-Host "Do not forget negative samples! Download 20-30 clear railway clips from Pexels with NO THREATS present."
Write-Host "Place them in: ./datasets/raw_videos/negative_samples/" -ForegroundColor Cyan

Write-Host "`nOnce datasets are downloaded, run: python backend/scripts/extract_frames.py" -ForegroundColor Green
