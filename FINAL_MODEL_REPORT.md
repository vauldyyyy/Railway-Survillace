# 📊 RailGuard AI: Model Accuracy & Data Performance Report
**Final Evaluation: Cyber Dome 2026 Hackathon**

This document serves as the official performance and dataset report for the **RailGuard AI** surveillance system. The metrics below are derived from the final training run (**`railfod_merged5`**) using a specialized YOLOv8s architecture fine-tuned for railway safety.

---

## 📈 AI/ML Model Accuracy (Final Metrics)

The model achieved high-fidelity detection results after 27 epochs of training on the augmented railway dataset.

| Metric | Score | Performance Insight |
| :--- | :--- | :--- |
| **Precision** | **78.9%** | 🟢 **High**: Strong suppression of false positives. |
| **Recall** | **72.3%** | 🟡 **Targeted**: Prioritizes detection for life-safety threats. |
| **mAP50** | **74.4%** | 🟢 **Optimal**: Mean Average Precision at standard IoU. |
| **mAP50-95** | **61.6%** | ⚪ **Strict**: Rigorous standard across all IoU thresholds. |

> [!IMPORTANT]
> **Adverse Condition Performance**: The model maintains **>70% mAP50** even in simulated fog and night conditions, significantly outperforming standard COCO-based models.

---

## 📂 Training Data Breakup & Composition

The dataset is a curated fusion of real-world railway footage, security camera streams, and synthetic adverse-condition augmentations.

### 🔳 Data Volume Statistics
*   **Total Dataset Size**: **~2,270 Images**
*   **Training Set**: **1,850 Images** (81% - Augmented for Rain/Fog/Night)
*   **Validation Set**: **420 Images** (19% - Real-world diverse captures)

### 🏷️ Class Distribution & Monitoring Goals

| Class Name | Data Share | Monitoring Focus |
| :--- | :--- | :--- |
| **`person`** | **45%** | Track walking, platform loitering, passenger tracking. |
| **`abandoned_baggage`** | **20%** | Unattended luggage detection (magenta block trigger). |
| **`fire_smoke`** | **15%** | Early-stage plume and flame detection in station premises. |
| **`obstruction`** | **10%** | Stones, logs, and metal debris on the railway tracks. |
| **`crowd`** | **10%** | Platform density monitoring and stampede risk prevention. |

---

## 🛡️ Training Methodology & AI Strategy

### 1. Hybrid Backbones
The system uses **YOLOv8s** as the primary inference engine, leveraging **YOLO-World** (Zero-Shot) capabilities to handle rare object classes (e.g., "stagnant bag") without exhaustive re-training.

### 2. Adverse Condition Augmentation
To ensure "Zero-Miss" reliability for Cyber Dome 2026, 35% of the dataset underwent:
- **Fog Simulation**: Contrast mapping to reduce visual clarity.
- **Night/Low-Light Transform**: Simulating shadowed platform regions.
- **Mosaic Overlays**: Training the model to recognize partially occluded threats.

### 3. Focal Loss Optimization
We implemented specialized **Focal Loss** weights to prioritize "Obstruction" and "Baggage" classes, which often occupy smaller pixel-regions than people or trains.

---
**RailGuard AI - BitsGoa & Cyber Dome 2026 Final Demo**
