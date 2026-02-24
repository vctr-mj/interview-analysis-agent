import torch

def main():
    print("=" * 40)
    print("Verificacion de PyTorch y CUDA")
    print("=" * 40)
    print(f"Version de PyTorch: {torch.__version__}")
    
    cuda_disponible = torch.cuda.is_available()
    print(f"CUDA disponible:    {cuda_disponible}")
    
    if cuda_disponible:
        version_cuda = torch.version.cuda
        print(f"Version de CUDA:    {version_cuda}")
        print(f"Dispositivo GPU:    {torch.cuda.get_device_name(0)}")
        print("\n¡Todo listo! Whisper usara tu GPU automaticamente.")
    else:
        print("\nNo se detecto CUDA. Whisper usara la CPU.")
        print("Si tienes una GPU NVIDIA, revisa las instrucciones")
        print("en el README.md para instalar PyTorch con soporte CUDA.")
    print("=" * 40)

if __name__ == "__main__":
    main()