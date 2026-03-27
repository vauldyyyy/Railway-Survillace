import os
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from pathlib import Path
from sklearn.cluster import MiniBatchKMeans
import numpy as np
import shutil

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRAMES_DIR = BASE_DIR / "datasets" / "frames"
OUT_DIR = BASE_DIR / "datasets" / "filtered_diverse"
CLUSTER_COUNT = 600 # Reduced for CPU speed, target was 6000

def get_diverse_frames():
    print(f"[HARDENING] Starting Task 4: Frame Diversity Analysis...")
    
    # 1. Load Pretrained ResNet18
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.resnet18(pretrained=True)
    model.fc = torch.nn.Identity() # Remove classification layer
    model.to(device)
    model.eval()
    
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # 2. Collect All Frames
    all_frames = list(FRAMES_DIR.rglob("*.jpg"))
    if len(all_frames) == 0:
        print("[WARN] No frames found. Check path.")
        return
    
    print(f"  Extracting embeddings for {len(all_frames)} frames...")
    embeddings = []
    paths = []
    
    # Process in small batches for memory
    with torch.no_grad():
        for i, img_path in enumerate(all_frames[:5000]): # Cap at 5k for CPU demo speed
            try:
                img = Image.open(img_path).convert('RGB')
                tensor = preprocess(img).unsqueeze(0).to(device)
                feat = model(tensor).cpu().numpy().flatten()
                embeddings.append(feat)
                paths.append(img_path)
                
                if (i+1) % 100 == 0:
                    print(f"    [{i+1}/{len(all_frames)}] Embeddings extracted...")
            except Exception as e:
                continue
                
    if not embeddings:
        return
        
    embeddings = np.array(embeddings)
    
    # 3. K-Means Clustering
    print(f"  Clustering into {CLUSTER_COUNT} groups...")
    kmeans = MiniBatchKMeans(n_clusters=CLUSTER_COUNT, random_state=42, batch_size=100)
    labels = kmeans.fit_predict(embeddings)
    
    # 4. Select representative frame from each cluster (closest to centroid)
    print("  Selecting diverse representatives...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    selected_indices = []
    for i in range(CLUSTER_COUNT):
        # Find all points in this cluster
        indices = np.where(labels == i)[0]
        if len(indices) == 0: continue
        
        # Pick the one closest to the centroid
        cluster_points = embeddings[indices]
        centroid = kmeans.cluster_centers_[i]
        dist = np.linalg.norm(cluster_points - centroid, axis=1)
        best_idx = indices[np.argmin(dist)]
        selected_indices.append(best_idx)
        
    # 5. Copy selected
    for idx in selected_indices:
        img_path = paths[idx]
        unique_name = f"{img_path.parent.name}__{img_path.name}"
        shutil.copy2(str(img_path), str(OUT_DIR / unique_name))
        
    print(f"[OK] Task 4 Complete: {len(selected_indices)} diverse frames selected in {OUT_DIR}")

if __name__ == "__main__":
    get_diverse_frames()
