# Dataset Download Instructions

Run the following commands in your PowerShell terminal to download and extract the datasets.
Make sure you are in the `backend/datasets` folder.

```powershell
# 1. Navigate to datasets directory
cd backend/datasets

# 2. Download UAV-RSOD (V2 for Obstacle Detection - 1.7 GB)
Invoke-WebRequest -Uri "https://zenodo.org/records/12606374/files/V2%20UAV-RSOD_Dataset%20for%20Obstacle%20Detection.zip?download=1" -OutFile "uav_rsod.zip"

# Extract UAV-RSOD
Expand-Archive -Path "uav_rsod.zip" -DestinationPath "uav_rsod" -Force

# 3. Download RailFOD23 (6.06 GB)
# Note: Figshare direct links can expire or block automated scripts. 
# If this command fails, please download it manually via your browser:
# Navigate to: https://doi.org/10.6084/m9.figshare.24180738 and click "Download (6.06 GB)"
# Save the 'RailFOD23.zip' file to `backend/datasets/`
Invoke-WebRequest -Uri "https://figshare.com/ndownloader/articles/24180738/versions/1" -OutFile "railfod23.zip"

# Extract RailFOD23
Expand-Archive -Path "railfod23.zip" -DestinationPath "railfod23" -Force
```
