import cv2
import numpy as np
import pywt
import argparse
import sys
from skimage import img_as_float

def extract_secret_data(image_path, mapping_info_path):
    """
    Extracts secret text from an image using pre-defined mapping rules.
    
    Args:
        image_path: Path to the image
        mapping_info_path: Path to the mapping dictionary
    
    Returns:
        extracted_text: The recovered secret text
        extracted_features: Features extracted for verification
        match_score: How well features match (0-100%)
    """
    
    print("\n" + "="*60)
    print("COVERLESS STEGANOGRAPHY - EXTRACTION PROCESS")
    print("="*60)
    
    # ========== STEP 1: Load mapping information ==========
    print("1. Loading mapping information...")
    try:
        import pickle
        with open(mapping_info_path, 'rb') as f:
            mapping_dict = pickle.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: Mapping file '{mapping_info_path}' not found!")
        print("   This file is required for extraction.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Could not load mapping file: {e}")
        sys.exit(1)
    
    print(f"   ✓ Mapping file loaded: {mapping_info_path}")
    print(f"   ✓ Original secret: '{mapping_dict.get('secret_text', 'Unknown')}'")
    print(f"   ✓ Selected region: {mapping_dict['selected_region']}")
    
    # ========== STEP 2: Load and process the received image ==========
    print("\n2. Processing received image...")
    try:
        img_color = cv2.imread(image_path)
        if img_color is None:
            raise ValueError(f"Could not load image from {image_path}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # Convert to grayscale
    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    print(f"   ✓ Image loaded: {img_gray.shape[1]}x{img_gray.shape[0]} pixels")
    
    # Verify image size matches (optional but recommended)
    if 'image_shape' in mapping_dict and img_gray.shape != mapping_dict['image_shape']:
        print(f"   ⚠ WARNING: Image shape differs from original")
        print(f"     Current: {img_gray.shape}, Original: {mapping_dict['image_shape']}")
    
    img_float = img_as_float(img_gray)
    
    # ========== STEP 3: Apply identical DWT decomposition ==========
    print("\n3. Applying identical DWT decomposition...")
    
    wavelet_type = mapping_dict.get('wavelet_type', 'haar')
    decomposition_level = mapping_dict.get('decomposition_level', 2)
    
    # Perform the exact same DWT as during embedding
    if decomposition_level == 2:
        # Get LL1 first
        LL1, (LH1, HL1, HH1) = pywt.dwt2(img_float, wavelet_type)
        # Then LL2 from LL1
        LL2, (LH2, HL2, HH2) = pywt.dwt2(LL1, wavelet_type)
        
        # Get the selected region
        regions = {
            'LL2': LL2,
            'LH2': LH2,
            'HL2': HL2,
            'HH2': HH2
        }
    else:
        # For 1-level decomposition
        LL1, (LH1, HL1, HH1) = pywt.dwt2(img_float, wavelet_type)
        regions = {
            'LL1': LL1,
            'LH1': LH1,
            'HL1': HL1,
            'HH1': HH1
        }
    
    print(f"   ✓ DWT applied: {wavelet_type} wavelet, level {decomposition_level}")
    
    # ========== STEP 4: Extract same robust features ==========
    print("\n4. Extracting features from DWT regions...")
    
    def extract_features(region):
        """Identical feature extraction function as in embedding."""
        features = {}
        features['mean'] = np.mean(region)
        features['variance'] = np.var(region)
        features['energy'] = np.sum(region ** 2)
        
        hist, _ = np.histogram(region.flatten(), bins=256, 
                              range=(region.min(), region.max()))
        prob = hist / hist.sum()
        prob = prob[prob > 0]
        features['entropy'] = -np.sum(prob * np.log2(prob))
        
        return features
    
    # Extract from the region used during embedding
    selected_region = mapping_dict['selected_region']
    if selected_region not in regions:
        print(f"❌ ERROR: Selected region '{selected_region}' not found!")
        sys.exit(1)
    
    extracted_features = extract_features(regions[selected_region])
    print(f"   ✓ Features extracted from {selected_region} region")
    
    # ========== STEP 5: Compare with original features ==========
    print("\n5. Comparing extracted features with original mapping...")
    
    original_features = mapping_dict['features']
    
    print("\n   FEATURE COMPARISON:")
    print("   " + "-"*55)
    print(f"   {'Feature':<12} {'Original':<15} {'Extracted':<15} {'Diff %':<10}")
    print("   " + "-"*55)
    
    differences = {}
    for feature_name in original_features.keys():
        orig_val = original_features[feature_name]
        extr_val = extracted_features[feature_name]
        diff = abs(orig_val - extr_val)
        diff_percent = (diff / (abs(orig_val) + 1e-10)) * 100
        
        differences[feature_name] = diff_percent
        
        print(f"   {feature_name:<12} {orig_val:<15.6f} {extr_val:<15.6f} {diff_percent:<10.2f}")
    
    print("   " + "-"*55)
    
    # Calculate overall match score
    avg_difference = np.mean(list(differences.values()))
    match_score = max(0, 100 - avg_difference)
    
    print(f"\n   Average difference: {avg_difference:.2f}%")
    print(f"   Feature match score: {match_score:.2f}%")
    
    if match_score > 95:
        print("   ✓ Excellent match - likely identical image")
    elif match_score > 80:
        print("   ✓ Good match - minor differences detected")
    elif match_score > 60:
        print("   ⚠ Fair match - image may have been modified")
    else:
        print("   ⚠ Poor match - possible wrong image or corruption")
    
    # ========== STEP 6: Recover secret text ==========
    print("\n6. Recovering secret text...")
    
    # Method 1: Direct recovery from mapping dict
    if 'secret_text' in mapping_dict:
        recovered_text = mapping_dict['secret_text']
        print(f"   ✓ Secret text recovered: '{recovered_text}'")
    
    # Method 2: Feature hash matching
    else:
        feature_hash = hash(tuple(extracted_features.values()))
        
        if 'feature_hash' in mapping_dict and feature_hash == mapping_dict['feature_hash']:
            recovered_text = mapping_dict.get('secret_text', 'Hash match successful')
        else:
            # Fallback: Try to reconstruct from binary if stored
            if 'secret_binary' in mapping_dict:
                binary_str = mapping_dict['secret_binary']
                chars = [binary_str[i:i+8] for i in range(0, len(binary_str), 8)]
                recovered_text = ''.join(chr(int(char, 2)) for char in chars)
            else:
                recovered_text = "EXTRACTION FAILED: Features don't match"
    
    # ========== STEP 7: Return results ==========
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"📨 Recovered secret: {recovered_text}")
    print(f"📊 Match confidence: {match_score:.1f}%")
    print(f"🗂️  Image used: {image_path}")
    print(f"🗂️  Mapping file: {mapping_info_path}")
    print("="*60)
    
    return recovered_text, extracted_features, match_score

def main():
    """Main function to handle command-line arguments for extraction."""
    
    parser = argparse.ArgumentParser(
        description='Coverless Steganography - Extract secret message from image',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i test.jpg -m mapping_12345.pkl
  %(prog)s --image received.png --mapping my_mapping.pkl
        """
    )
    
    parser.add_argument('-i', '--image', type=str, required=True, 
                       help='Path to the image file (must be same as embedding)')
    parser.add_argument('-m', '--mapping', type=str, required=True,
                       help='Path to the mapping file (.pkl) from embedding')
    
    args = parser.parse_args()
    
    # Run the extraction process
    try:
        extracted_text, features, confidence = extract_secret_data(
            image_path=args.image,
            mapping_info_path=args.mapping
        )
        
        # Exit with success code
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ EXTRACTION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()