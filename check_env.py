import torch
import tensorflow as tf
try:
    import ultralytics
    print("Ultralytics installed")
    ultralytics.checks()
except ImportError:
    print("Ultralytics NOT installed")

print(f"PyTorch GPU: {torch.cuda.is_available()}")
print(f"TensorFlow GPU: {tf.config.list_physical_devices('GPU')}")
