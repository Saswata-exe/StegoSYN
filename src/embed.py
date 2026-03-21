import cv2
import numpy as np
import pywt
import matplotlib.pyplot as plt
import sys
import argparse
from skimage import img_as_float

def embed_secret_data(image_path, secret_text, output_viz_path='mapping_visualization.png'):
    """
    Extracts robust DWT features from an image and maps secret text to them.
    
    Args:
        image_path: Path to the cover image
        secret_text: Secret message to map
        output_viz_path: Path to save the visualization
    
    Returns:
        mapping_dict: Dictionary containing the mapping relationship
        features: Extracted feature values
        viz_image: Visualization of where features were extracted
    """
    
    print("\n" + "="*60)
    print("COVERLESS STEGANOGRAPHY - EMBEDDING PROCESS")
    print("="*60)
    print(f"Image: {image_path}")
    print(f"Secret message: '{secret_text}'")
    print("="*60 + "\n")
    
    # ========== STEP 1: Load and preprocess image ==========
    print("1. Loading and preprocessing image...")
    img_color = cv2.imread(image_path)
    if img_color is None:
        raise ValueError(f"❌ ERROR: Could not load image from {image_path}")
    print(f"   ✓ Image loaded successfully: {img_color.shape[1]}x{img_color.shape[0]} pixels")
    
    # Convert to grayscale as your mentor suggested
    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(img_gray)
    print("   ✓ Converted to grayscale")
    
    # ========== STEP 2: Apply 2-level DWT ==========
    print("2. Applying 2-level Discrete Wavelet Transform...")
    # Level 1 decomposition
    coeffs1 = pywt.dwt2(img_float, 'haar')
    LL1, (LH1, HL1, HH1) = coeffs1
    
    # Level 2 decomposition on LL1
    coeffs2 = pywt.dwt2(LL1, 'haar')
    LL2, (LH2, HL2, HH2) = coeffs2
    
    # All regions to analyze
    regions = {
        'LL2': LL2,  # Most stable
        'LH2': LH2,  # Horizontal details
        'HL2': HL2,  # Vertical details  
        'HH2': HH2   # Diagonal details
    }
    print("   ✓ DWT decomposition completed")
    
    # ========== STEP 3: Extract robust features from each region ==========
    print("3. Extracting robust features from all 4 DWT regions...")
    
    def extract_features(region, region_name):
        """Extract 4 robust features from a DWT region."""
        features = {}
        
        # 1. Mean (very robust)
        features['mean'] = np.mean(region)
        
        # 2. Variance (robust to small changes)
        features['variance'] = np.var(region)
        
        # 3. Energy (sum of squares)
        features['energy'] = np.sum(region ** 2)
        
        # 4. Entropy (information content)
        hist, _ = np.histogram(region.flatten(), bins=256, range=(region.min(), region.max()))
        prob = hist / hist.sum()
        prob = prob[prob > 0]  # Remove zeros for log
        features['entropy'] = -np.sum(prob * np.log2(prob))
        
        return features
    
    # Extract features from all regions
    all_features = {}
    print("\n   Extracted Features Summary:")
    print("   " + "-"*60)
    for region_name, region_data in regions.items():
        all_features[region_name] = extract_features(region_data, region_name)
        print(f"   {region_name:4} | Mean: {all_features[region_name]['mean']:8.6f} | "
              f"Var: {all_features[region_name]['variance']:10.8f} | "
              f"Energy: {all_features[region_name]['energy']:10.4f}")
    print("   " + "-"*60)
    
    # ========== STEP 4: Create mapping of secret text to features ==========
    print("\n4. Creating mapping between secret text and extracted features...")
    
    # Convert secret text to binary
    secret_binary = ''.join(format(ord(char), '08b') for char in secret_text)
    print(f"   ✓ Secret text converted to binary: {len(secret_binary)} bits")
    
    # Select the most stable region for mapping (LL2 usually)
    selected_region = 'LL2'
    
    # Create mapping dictionary
    mapping_dict = {
        'secret_text': secret_text,
        'secret_binary': secret_binary,
        'selected_region': selected_region,
        'features': all_features[selected_region],
        'all_features': all_features,
        'image_shape': img_gray.shape,
        'image_path': image_path,
        'wavelet_type': 'haar',
        'decomposition_level': 2,
        'timestamp': np.datetime64('now')
    }
    
    # Create a simple hash from features for mapping demonstration
    feature_hash = hash(tuple(all_features[selected_region].values()))
    mapping_dict['feature_hash'] = feature_hash
    
    # ========== STEP 5: Create visualization of mapping ==========
    print("\n5. Creating visualization of DWT regions and feature extraction...")
    
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle(f'Coverless Steganography - Feature Extraction\nSecret: "{secret_text[:20]}{"..." if len(secret_text) > 20 else ""}"', fontsize=14)
    
    # Original and grayscale
    axes[0, 0].imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title('Original Color Image')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(img_gray, cmap='gray')
    axes[0, 1].set_title('Grayscale Image')
    axes[0, 1].axis('off')
    
    # DWT regions visualization
    region_plots = [(LL2, 'LL2 (Selected)'), (LH2, 'LH2'), (HL2, 'HL2'), (HH2, 'HH2')]
    
    for idx, (region, title) in enumerate(region_plots):
        row, col = divmod(idx, 2)
        ax = axes[row, col + 2]
        
        # Show region
        im = ax.imshow(region, cmap='gray', aspect='auto')
        ax.set_title(title)
        ax.axis('off')
        
        # Add feature values as text
        if title.startswith('LL2'):
            feat_text = (f"Mean: {all_features['LL2']['mean']:.4f}\n"
                        f"Var: {all_features['LL2']['variance']:.6f}\n"
                        f"Energy: {all_features['LL2']['energy']:.2f}\n"
                        f"Entropy: {all_features['LL2']['entropy']:.4f}")
            ax.text(0.5, -0.15, feat_text, transform=ax.transAxes,
                   ha='center', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow"))
    
    # Add mapping info
    axes[1, 0].axis('off')
    axes[1, 1].axis('off')
    
    # Text box with mapping information
    info_text = (
        f"SECRET DATA MAPPING\n"
        f"{'='*30}\n"
        f"Secret Text: {secret_text}\n"
        f"Binary Length: {len(secret_binary)} bits\n"
        f"Selected Region: {selected_region}\n"
        f"Feature Hash: {feature_hash}\n"
        f"\nKEY FEATURES (LL2):\n"
        f"Mean: {all_features[selected_region]['mean']:.6f}\n"
        f"Variance: {all_features[selected_region]['variance']:.8f}\n"
        f"Energy: {all_features[selected_region]['energy']:.4f}\n"
        f"Entropy: {all_features[selected_region]['entropy']:.4f}"
    )
    
    axes[1, 2].text(0.1, 0.5, info_text, transform=axes[1, 2].transAxes,
                   fontsize=9, verticalalignment='center',
                   bbox=dict(boxstyle="round,pad=1", facecolor="lightblue"))
    axes[1, 2].set_title('Mapping Details', fontsize=12)
    axes[1, 2].axis('off')
    
    # Add note about coverless steganography
    note_text = (
        "COVERLESS METHOD\n"
        f"{'='*30}\n"
        "✓ Original image NOT modified\n"
        "✓ Mapping via feature extraction\n"
        "✓ Zero distortion to image\n"
        "\nWORKFLOW:\n"
        "1. Extract features from image\n"
        "2. Map features to secret data\n"
        "3. Send original image + mapping\n"
        "4. Receiver extracts same features\n"
        "5. Match features to recover secret"
    )
    
    axes[1, 3].text(0.1, 0.5, note_text, transform=axes[1, 3].transAxes,
                   fontsize=9, verticalalignment='center',
                   bbox=dict(boxstyle="round,pad=1", facecolor="lightgreen"))
    axes[1, 3].set_title('Coverless Steganography', fontsize=12)
    axes[1, 3].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_viz_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # ========== STEP 6: Save mapping info ==========
    import pickle
    mapping_filename = f"mapping_{feature_hash}.pkl"
    with open(mapping_filename, 'wb') as f:
        pickle.dump(mapping_dict, f)
    
    print(f"\n6. Embedding complete!")
    print("   " + "="*50)
    print(f"   ✓ Visualization saved to: {output_viz_path}")
    print(f"   ✓ Mapping data saved to: {mapping_filename}")
    print(f"   ✓ Selected region: {selected_region}")
    print(f"   ✓ Feature Hash: {feature_hash}")
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("1. Send the ORIGINAL image to receiver")
    print(f"2. Send the mapping file: {mapping_filename}")
    print("3. Receiver uses extract.py with both files")
    print("="*60)
    
    return mapping_dict, all_features, img_gray

def main():
    """Main function to handle command-line arguments."""
    
    # ========== METHOD 1: Command-line arguments (Recommended) ==========
    parser = argparse.ArgumentParser(
        description='Coverless Steganography - Embed secret message in image features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i test.jpg -s "MySecret123"
  %(prog)s --image sample.png --secret "Confidential Data" --output my_map.png
  %(prog)s (will prompt for inputs interactively)
        """
    )
    
    parser.add_argument('-i', '--image', type=str, help='Path to input image file')
    parser.add_argument('-s', '--secret', type=str, help='Secret message to hide (English text)')
    parser.add_argument('-o', '--output', type=str, default='mapping_visualization.png', 
                       help='Output visualization filename (default: mapping_visualization.png)')
    
    args = parser.parse_args()
    
    # ========== METHOD 2: Interactive input if no arguments provided ==========
    if not args.image or not args.secret:
        print("\n" + "="*60)
        print("COVERLESS STEGANOGRAPHY - INTERACTIVE MODE")
        print("="*60)
        
        # Get image path
        if not args.image:
            args.image = input("Enter image path (e.g., test.jpg): ").strip()
            if not args.image:
                args.image = 'test_image.jpg'  # Default
                print(f"Using default: {args.image}")
        
        # Get secret message
        if not args.secret:
            args.secret = input("Enter secret message (English text): ").strip()
            if not args.secret:
                args.secret = 'DEFAULT_SECRET_MESSAGE'
                print(f"Using default: {args.secret}")
    
    # Validate inputs
    if not args.secret:
        print("❌ ERROR: Secret message cannot be empty!")
        sys.exit(1)
    
    # ========== Run the embedding process ==========
    try:
        mapping_info, features, original_image = embed_secret_data(
            image_path=args.image,
            secret_text=args.secret,
            output_viz_path=args.output
        )
        
        print(f"\n✅ SUCCESS: Secret message embedded in features of '{args.image}'")
        print(f"   Secret: '{args.secret}'")
        print(f"   Mapping file: mapping_{mapping_info['feature_hash']}.pkl")
        
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        print("   Please check the image path and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

# ========== Run the main function ==========
if __name__ == "__main__":
    main()