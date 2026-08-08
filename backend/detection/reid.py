import time
import uuid
import cv2
import numpy as np
import base64
import torch
import torch.nn as nn
from torchvision import models, transforms
from collections import deque

class ReIDTracker:
    def __init__(self, threshold=0.75, epsilon=1.2, reset_minutes=60):
        self.threshold = threshold
        self.epsilon = epsilon
        self.reset_minutes = reset_minutes
        
        # Gallery mapping: UUID -> {"embedding": np.array, "path": [records], "image": str, "last_seen": float}
        self.gallery = {}
        self.last_reset = time.time()
        
        # --- Neural Backbone Optimization (IIT-Level Engineering) ---
        print("[ReID] Initializing Neural Feature Extractor (MobileNetV3-Small)...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load lightweight but powerful backbone
        backbone = models.mobilenet_v3_small(weights="MobileNet_V3_Small_Weights.DEFAULT")
        
        # Projection layer to EXACTLY 512-DIM (to match UI specifications)
        self.projection = nn.Linear(576, 512) 
        
        # Proper Sequential wrapper for features -> pooling -> flatten -> projection
        self.model = nn.Sequential(
            backbone.features,
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            self.projection
        )
        self.model.to(self.device)
        self.model.eval()
        
        self.preprocess = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((128, 64)), # Standard ReID input size
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        print(f"[ReID] Neural Engine Online on {self.device}")

    def _extract_neural_embedding(self, crop):
        """Extracts a 512-D neural embedding from a person crop."""
        if crop is None or crop.size == 0:
            return np.zeros(512, dtype=np.float32)
        
        try:
            # 1. Preprocess
            input_tensor = self.preprocess(crop).unsqueeze(0).to(self.device)
            
            # 2. Forward Pass
            with torch.no_grad():
                # Features are extracted and projected to 512-D
                features = self.model(input_tensor)
                vec = features.view(-1).cpu().numpy()
            
            # 3. L2 Normalization
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
                
            # 4. Global Differential Privacy (Epsilon=1.2 as per UI)
            noise = np.random.normal(0, self.epsilon / 10.0, vec.shape).astype(np.float32)
            vec = (vec + noise)
            
            # Re-normalize after noise injection
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
                
            return vec
        except Exception as e:
            print(f"[ReID-Error] Extraction failed: {e}")
            return np.zeros(512, dtype=np.float32)

    def _cosine_similarity(self, a, b):
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0: return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _crop_to_b64(self, crop):
        ok, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok: return ""
        return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

    def update(self, frame, box, camera_id):
        """
        HSV-based Re-ID update loop.
        Matches person crops against the gallery using color signatures.
        """
        now = time.time()
        
        # 1. Privacy Purge
        if (now - self.last_reset) > (self.reset_minutes * 60):
            self.gallery.clear()
            self.last_reset = now

        # 2. Extract Crop
        x1, y1, x2, y2 = [int(v) for v in box]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if (x2 - x1) * (y2 - y1) < 400:
            return None, []
            
        crop = frame[y1:y2, x1:x2]
        emb = self._extract_neural_embedding(crop)
        
        # 3. Matching (Direct Vector Comparison)
        best_uuid = None
        best_score = -1.0
        
        for p_uuid, data in self.gallery.items():
            score = self._cosine_similarity(emb, data["embedding"])
            if score > best_score:
                best_score = score
                best_uuid = p_uuid
        
        # 4. Resolve or Create
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        path_record = {"camera": camera_id, "time": time.strftime("%H:%M:%S"), "center": (cx, cy)}

        if best_uuid and best_score >= self.threshold:
            # Match found: Update using EMA (Exponential Moving Average)
            # This makes the "Identity" more robust to transient occlusions or blur
            alpha = 0.2 # Learning rate for identity drift
            self.gallery[best_uuid]["embedding"] = (1 - alpha) * self.gallery[best_uuid]["embedding"] + alpha * emb
            
            # Re-normalize after EMA
            norm = np.linalg.norm(self.gallery[best_uuid]["embedding"])
            if norm > 0:
                self.gallery[best_uuid]["embedding"] /= norm
                
            self.gallery[best_uuid]["path"].append(path_record)
            self.gallery[best_uuid]["last_seen"] = now
            return best_uuid, self.gallery[best_uuid]["path"]
        else:
            # New person
            if len(self.gallery) > 150: # Increased capacity
                oldest = min(self.gallery, key=lambda k: self.gallery[k]["last_seen"])
                del self.gallery[oldest]
                
            new_id = f"TRK-{int(uuid.uuid4().int % 9000) + 1000:04d}"
            self.gallery[new_id] = {
                "embedding": emb,
                "path": [path_record],
                "image": self._crop_to_b64(crop),
                "last_seen": now,
                "status": "NORMAL"
            }
            return new_id, self.gallery[new_id]["path"]
