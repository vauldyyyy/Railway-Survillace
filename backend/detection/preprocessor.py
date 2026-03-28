# backend/detection/preprocessor.py
import cv2
import numpy as np

class AdverseConditionPreprocessor:
    """
    Runs before YOLO on every frame.
    Detects condition -> applies targeted enhancement.
    Based on AWD-YOLO and IA-YOLO research (2024-2025).
    """

    def detect_condition(self, frame):
        """Auto-detect what condition we're in using brightness and contrast."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        std_brightness  = np.std(gray)
        
        if mean_brightness < 60:
            return "night"
        elif std_brightness < 35 and mean_brightness > 100:
            return "fog"
        elif mean_brightness < 100 and std_brightness > 50:
            return "rain"
        else:
            return "normal"

    def enhance_night(self, frame):
        """CLAHE (Contrast Limited Adaptive Histogram Equalization) + Gamma correction for low-light."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # CLAHE on luminance channel only
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Gamma correction (gamma < 1 brightens)
        gamma = 0.6
        table = np.array([
            ((i / 255.0) ** gamma) * 255
            for i in np.arange(256)
        ]).astype("uint8")
        return cv2.LUT(enhanced, table)

    def enhance_fog(self, frame):
        """Fast Dark Channel Prior Dehazing."""
        # Fast dehazing using dark channel
        dark = np.min(frame, axis=2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dark = cv2.erode(dark, kernel)
        
        # Estimate atmospheric light
        flat = dark.flatten()
        top_idx = np.argsort(flat)[-int(0.001 * len(flat)):]
        atm = np.mean(frame.reshape(-1, 3)[top_idx], axis=0)
        
        # Estimate transmission
        norm = frame.astype(float) / atm
        t = 1 - 0.9 * np.min(norm, axis=2)
        t = np.clip(t, 0.1, 1.0)
        
        # Recover scene radiance
        t3 = np.stack([t, t, t], axis=2)
        dehazed = (frame.astype(float) - atm) / t3 + atm
        return np.clip(dehazed, 0, 255).astype(np.uint8)

    def enhance_rain(self, frame):
        """Bilateral filter to remove rain streaks while preserving critical object edges."""
        # Bilateral filter - preserves object edges
        derained = cv2.bilateralFilter(frame, 9, 75, 75)
        
        # Sharpen after derain to recover potential detail loss
        kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
        return cv2.filter2D(derained, -1, kernel)

    def process(self, frame):
        """Main entry point - auto-detect and enhance the frame."""
        condition = self.detect_condition(frame)
        
        if condition == "night":
            enhanced = self.enhance_night(frame)
        elif condition == "fog":
            enhanced = self.enhance_fog(frame)
        elif condition == "rain":
            enhanced = self.enhance_rain(frame)
        else:
            enhanced = frame
            
        return enhanced, condition

# Singleton instance
preprocessor = AdverseConditionPreprocessor()
