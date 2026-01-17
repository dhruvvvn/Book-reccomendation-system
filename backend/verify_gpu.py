
import torch
import sys

def verify():
    print("--- GPU Verification ---")
    print(f"PyTorch Version: {torch.__version__}")
    
    if torch.cuda.is_available():
        print("✅ CUDA IS AVAILABLE!")
        print(f"Device Count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            try:
                props = torch.cuda.get_device_properties(i)
                print(f"  Memory: {props.total_memory / 1024**3:.2f} GB")
            except:
                pass
        print("Optimization: ENABLED (Ingestion will be fast)")
        sys.exit(0)
    else:
        print("❌ CUDA IS NOT AVAILABLE.")
        print("Ingestion will be slow (CPU mode).")
        sys.exit(1)

if __name__ == "__main__":
    verify()
