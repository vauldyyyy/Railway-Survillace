from ultralytics import YOLOWorld
import cv2
class ZeroShotDetector:
    def __init__(self):
        print("[YOLO-World] Initializing Zero-Shot Open-Vocabulary Engine (yolov8s-worldv2.pt)...")
        try:
            self.model = YOLOWorld('yolov8s-worldv2.pt')
            print("[YOLO-World] Weights loaded.")
        except Exception as e:
            print(f"[YOLO-World-Error] Failed to initialize model. Falling back/Requires ultralytics: {e}")
            self.model = None

        # Pre-configured Master Text Prompts for Railway Environment
        self.default_classes = [
            "unattended backpack on platform",
            "person on railway track",
            "metal debris on track",
            "plastic bag on track",
            "person loitering near platform edge",
            "fire or smoke",
            "suspicious abandoned luggage",
            "person" # Required implicitly for the ReID Tracker pipeline
        ]
        self.set_classes(self.default_classes)

    def set_classes(self, new_classes):
        """
        Dynamically hot-swaps the neural network's detection vocabulary
        in real-time during the live Hackathon without requiring a reboot.
        """
        # Ensure 'person' is always present for ReID compatibility, 
        # unless it was explicitly included in the new classes by the user.
        if "person" not in new_classes:
            new_classes.append("person")
            
        print(f"[YOLO-World] Target Vocabulary Hot-Swapped: {new_classes}")
        if self.model:
            self.model.set_classes(new_classes)
        self.current_classes = new_classes

    def _get_severity(self, class_name):
        """Maps semantic text to SOC operational severity levels."""
        if class_name in ["person on railway track", "fire or smoke"]:
            return "critical"
        elif class_name in ["metal debris on track"]:
            return "warning"
        return "info"

    def detect(self, frame, conf_threshold=0.15):
        """
        Executes a zero-shot inference pass over the target frame using the active vocabulary.
        Returns mapped dictionaries containing the bounding boxes and operational severity.
        """
        if not self.model:
            return []

        # YOLO-World native prediction sweep
        results = self.model.predict(frame, conf=conf_threshold, verbose=False)
        detections = []
        
        for r in results:
            boxes = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            class_ids = r.boxes.cls.int().cpu().numpy()
            
            for box, conf, cls_id in zip(boxes, confs, class_ids):
                # Retrieve the exact text prompt that triggered this detection
                class_name = self.current_classes[cls_id]
                
                detections.append({
                    "class_name": class_name,
                    "severity": self._get_severity(class_name),
                    "confidence": float(conf),
                    "box": [int(v) for v in box]
                })
                
        return detections
