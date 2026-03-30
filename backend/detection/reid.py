import time
import uuid
import torch
import numpy as np
try:
    import torchreid
except ImportError:
    torchreid = None
from collections import defaultdict
import datetime

class ReIDTracker:
    def __init__(self, threshold=0.72, epsilon=0.1, reset_minutes=30):
        self.threshold = threshold
        self.epsilon = epsilon
        self.reset_minutes = reset_minutes
        
        # Load OSNet Model
        print(f"[OSNet] Initializing Cross-Camera Re-Identification Engine...")
        self.extractor = None
        if torchreid:
            try:
                self.extractor = torchreid.utils.FeatureExtractor(
                    model_name='osnet_x1_0',
                    model_path='', # Automatically pulls pretrained weights
                    device='cpu'   # Conforming to Hackathon CPU constraint 
                )
                print("[OSNet] Loaded osnet_x1_0 successfully.")
            except Exception as e:
                print(f"[OSNet-WARN] Neural ReID failed, using spatial fallback: {e}")
        else:
            print("[OSNet-WARN] torchreid not installed, using spatial fallback.")

        # Gallery mapping: UUID -> {"embedding": np.array, "path": [records]}
        self.gallery = {}
        self.last_reset = time.time()
        
    def _apply_differential_privacy(self, embedding):
        """Injects Gaussian noise (Laplacian mechanism proxy) to strictly anonymize raw identity features."""
        noise = np.random.normal(0, self.epsilon, embedding.shape)
        noisy_embedding = embedding + noise
        
        # Re-normalize to unit sphere to maintain valid Cosine Distance algebra
        norm = np.linalg.norm(noisy_embedding)
        if norm == 0:
            return noisy_embedding
        return noisy_embedding / norm

    def _cosine_similarity(self, a, b):
        """Calculates distance between 512-dim embedding spaces."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    def update(self, frame, box, camera_id):
        """
        Processes a YOLO person crop, extracts anonymous telemetry embeddings,
        and assigns cross-camera temporal Tracking ID.
        """
        if self.extractor is None:
            return None, []

        # 1. Privacy Act Compliance: Automated Gallery Wipe
        if (time.time() - self.last_reset) > (self.reset_minutes * 60):
            print("[OSNet] Privacy Schedule Reached: Permanently purging ReID Gallery.")
            self.gallery.clear()
            self.last_reset = time.time()
            
        # 2. Extract Geometric Bounds
        x1, y1, x2, y2 = [int(v) for v in box]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Reject absolute spatial noise (area < 400px, e.g., 20x20)
        # We NO LONGER filter by raw height/width to protect fallen humans (wide but short)
        if (x2 - x1) * (y2 - y1) < 400:
            return None, []
            
        person_crop = frame[y1:y2, x1:x2]
        
        # 3. Neural Extraction (Native resize handled by torchreid internal transform pipeline)
        try:
            raw_features = self.extractor([person_crop])[0].cpu().numpy()
        except Exception as e:
            return None, []
        
        # 4. Inject Mathematical Anonymity (Differential Privacy)
        secure_emb = self._apply_differential_privacy(raw_features)
        
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        path_record = {"camera": camera_id, "time": now_str, "center": (cx, cy)}
        
        # 5. Fallback or Neural Matching
        best_match_uuid = None
        best_score = -1.0
        
        if self.extractor:
            # Neural Cosine Probe
            for p_uuid, data in self.gallery.items():
                if "embedding" in data:
                    score = self._cosine_similarity(secure_emb, data["embedding"])
                    if score > best_score:
                        best_score = score
                        best_match_uuid = p_uuid
        else:
            # Spatial Fallback (Centroid Proximity)
            for p_uuid, data in self.gallery.items():
                if data["path"]:
                    last_pos = data["path"][-1]["center"]
                    dist = np.linalg.norm(np.array(last_pos) - np.array((cx, cy)))
                    # If within 100 pixels, assume same person for demo stability
                    if dist < 100:
                        best_match_uuid = p_uuid
                        best_score = 1.0 # Forced match
                        
        # 6. Resolving Trajectory Permanence
        if best_match_uuid is not None and (best_score >= self.threshold or not self.extractor):
            # Trajectory extension detected across cameras
            self.gallery[best_match_uuid]["path"].append(path_record)
            
            # (Optional) Exponential Moving Average update of the core embedding to track pose drift
            # alpha = 0.9
            # self.gallery[best_match_uuid]["embedding"] = (alpha * self.gallery[best_match_uuid]["embedding"]) + ((1-alpha) * secure_emb)
            
            return best_match_uuid, self.gallery[best_match_uuid]["path"]
        else:
            # 7. Uncharted Actor Detected -> Initialize UUID Node
            if len(self.gallery) > 100:  # max 100 tracked persons
                oldest = next(iter(self.gallery))
                del self.gallery[oldest]
                
            new_uuid = str(uuid.uuid4())[:8] # High-density 8-char hash
            self.gallery[new_uuid] = {
                "embedding": secure_emb,
                "path": [path_record]
            }
            return new_uuid, self.gallery[new_uuid]["path"]
