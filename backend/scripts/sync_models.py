import os
import sys
import requests
import argparse
from pathlib import Path

def download_file(url, dest_path):
    """
    Downloads a file from a URL to a destination path, handling Google Drive's "Virus Scan" redirects.
    """
    print(f"🚀 Initializing sync for: {dest_path.name}")
    
    # Handle Google Drive share links by converting them to direct download links
    if 'drive.google.com' in url:
        if 'file/d/' in url:
            file_id = url.split('file/d/')[1].split('/')[0]
        elif 'id=' in url:
            file_id = url.split('id=')[1].split('&')[0]
        else:
            print("❌ Error: Could not extract File ID from Google Drive link.")
            return False
        url = f'https://drive.google.com/uc?export=download&id={file_id}'
        print(f"🔗 Detected Google Drive link. Converting to direct download: {file_id}")

    try:
        session = requests.Session()
        # First request to get cookies and potential confirmation token
        response = session.get(url, stream=True)
        
        # Check for Google's "Virus Scan" / "Confirmation" page
        confirm_token = None
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                confirm_token = value
                break
        
        if confirm_token:
            params = {'id': file_id, 'confirm': confirm_token}
            response = session.get('https://drive.google.com/uc?export=download', params=params, stream=True)
            print("⚠️ Large file detected. Bypass token applied.")

        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 10 \
            * 1024 * 1024 # 10MB
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            downloaded = 0
            for data in response.iter_content(block_size):
                f.write(data)
                downloaded += len(data)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r📥 Downloading... {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB)", end="")
            print("\n✅ Sync Complete.")
        return True
    except Exception as e:
        print(f"\n❌ Sync Failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="RailGuard AI — Colab-to-Local Model Sync")
    parser.add_argument("--url", help="URL of the model weights (Direct or Google Drive Share Link)")
    parser.add_argument("--model", default="yolov8s-worldv2.pt", help="Filename to save as (e.g. yolov8s.pt)")
    parser.add_argument("--dest", default="backend", help="Destination folder (relative to project root)")

    args = parser.parse_args()

    if not args.url:
        print("💡 Usage: python backend/scripts/sync_models.py --url <YOUR_COLAB_URL>")
        print("   If you don't have a URL, check your Google Drive Share Link for 'RailGuard_Adverse_GoldMaster.pt'")
        return

    dest_dir = Path(args.dest).resolve()
    dest_path = dest_dir / args.model
    
    download_file(args.url, dest_path)

if __name__ == "__main__":
    main()
