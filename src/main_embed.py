import cv2
import numpy as np
import os
from global_entropy import calculate_global_entropy
from dwt_transform import perform_dwt_decomposition, reconstruct_image
from block_selection import select_blocks_for_embedding
from embedding import embed_data
from visualization import generate_mask_image

def embed_secret_data():
    print("\n=== DWT Steganography Embedder ===")
    
    # Input validation
    while True:
        image_path = input("Enter cover image path: ").strip('"')
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError()
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            break
        except:
            print("Error: Invalid image path or format")

    while True:
        secret_path = input("Enter secret text file path: ").strip('"')
        try:
            with open(secret_path, 'r') as f:
                secret = f.read()
            break
        except:
            print("Error: File not found or inaccessible")

    # Force PNG extension for output
    output_path = input("Output stego image path [default: stego.png]: ").strip('"') or "stego.png"
    output_path = os.path.splitext(output_path)[0] + ".png"  # Ensure .png extension
    
    mask_path = input("Mask output path [default: mask.png]: ").strip('"') or "mask.png"
    mask_path = os.path.splitext(mask_path)[0] + ".png"  # Ensure .png extension

    # Embedding pipeline
    global_ent = calculate_global_entropy(image)
    coeffs = perform_dwt_decomposition(image)
    blocks = select_blocks_for_embedding(coeffs, global_ent)
    modified_coeffs = embed_data(coeffs, blocks, secret)
    stego_image = reconstruct_image(modified_coeffs)
    
    # Save outputs with explicit PNG writer
    try:
        if not cv2.imwrite(output_path, cv2.cvtColor(stego_image, cv2.COLOR_RGB2BGR)):
            raise ValueError(f"Failed to write {output_path}")
        print(f"\nStego image saved to {output_path}")
        
        generate_mask_image(image, blocks, mask_path)
        print(f"Embedding mask saved to {mask_path}")
    except Exception as e:
        print(f"\nCritical error saving files: {str(e)}")
        print("Possible causes:")
        print("- Invalid output path")
        print("- Permission denied")
        print("- Disk full")

if __name__ == "__main__":
    embed_secret_data()
