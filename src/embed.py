"""
Embedding – creates a single .pkl file with embedded SHA-256 hash of pHash.
Includes visualization of DWT sub‑bands and feature values.
"""

import cv2
import numpy as np
import pywt
import pickle
import hashlib
import os
import sys
import argparse
import base64
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from skimage import img_as_float
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

def derive_encryption_key(master_key):
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b'encryption-key-for-secret', backend=default_backend())
    key = hkdf.derive(master_key)
    return base64.urlsafe_b64encode(key)

def extract_wavelet_features(region):
    return {'mean': float(np.mean(region)),
            'variance': float(np.var(region)),
            'energy': float(np.sum(region ** 2))}

def compute_perceptual_hash(image_path):
    try:
        from PIL import Image
        import imagehash
        img = Image.open(image_path).convert('L')
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        return str(imagehash.phash(img, hash_size=16))
    except ImportError:
        print("⚠️ imagehash not installed. Using SHA-256 fallback.")
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (128, 128))
        return hashlib.sha256(resized.tobytes()).hexdigest()

def generate_embedding_visualization(image_path, regions, all_features, mapping_entries, output_path='embedding_visualization.png'):
    """
    Generate a clean visualization showing:
    - Original cover image
    - 2×2 grid of DWT sub‑bands (LL2, LH2, HL2, HH2)
    - Feature vectors (mean, variance, energy) for each sub‑band
    - No binary secret parts are displayed
    """
    # Load original image
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Create figure: 2 rows, 3 columns (original spans top row, sub‑bands in bottom 2×2)
    fig = plt.figure(figsize=(12, 10))
    gs = gridspec.GridSpec(2, 3, height_ratios=[1.2, 1], width_ratios=[1, 1, 1])
    
    # ---- Top row: Original image (spans 3 columns) ----
    ax_orig = plt.subplot(gs[0, :])
    ax_orig.imshow(img_rgb)
    ax_orig.set_title('Original Cover Image (StyleGAN2‑ADA)', fontsize=14, fontweight='bold')
    ax_orig.axis('off')
    
    # ---- Bottom row: 2×2 grid of sub‑bands ----
    gs_sub = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs[1, :], wspace=0.1, hspace=0.1)
    
    region_names = ['LL2', 'LH2', 'HL2', 'HH2']
    for i, name in enumerate(region_names):
        row = i // 2
        col = i % 2
        ax = plt.subplot(gs_sub[row, col])
        # Normalize sub‑band for display
        band = regions[name]
        band_display = (band - band.min()) / (band.max() - band.min() + 1e-10)
        ax.imshow(band_display, cmap='gray')
        ax.set_title(f'{name} Sub‑band', fontsize=12, fontweight='bold')
        ax.axis('off')
        
        # Overlay feature values
        feat = all_features[name]
        textstr = f"μ = {feat['mean']:.4f}\nσ² = {feat['variance']:.4f}\nE = {feat['energy']:.2f}"
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
    
    # Add a caption at the bottom about the mapping
    fig.text(0.5, 0.02, 
             "Feature vectors (mean, variance, energy) are extracted from each sub‑band and mapped to secret binary fragments.",
             ha='center', fontsize=11, style='italic')
    
    plt.suptitle('Embedding Visualization: DWT Sub‑bands & Feature Extraction', fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"✅ Embedding visualization saved: {output_path}")

def embed_secret_data(image_path, secret_text, output_dir=None,
                      ll2_weight=0.5, lh2_weight=0.2, hl2_weight=0.2, hh2_weight=0.1,
                      hmac_key=None, embed_percent=100.0):
    if abs(ll2_weight + lh2_weight + hl2_weight + hh2_weight - 1.0) > 1e-6:
        raise ValueError("Weights must sum to 1.0")
    if embed_percent < 100.0:
        new_len = max(1, int(len(secret_text) * embed_percent / 100.0))
        secret_text = secret_text[:new_len]
        print(f"✂️ Embedding {embed_percent:.1f}% of secret")

    print("\n=== EMBEDDING (Image-derived key, pHash not stored) ===")
    print(f"Secret: {secret_text[:50]}...")

    secret_bytes = secret_text.encode('utf-8')
    secret_binary = ''.join(format(b, '08b') for b in secret_bytes)
    secret_hash = hashlib.sha256(secret_text.encode('utf-8')).hexdigest()

    # --- Compute pHash of the image ---
    phash_hex = compute_perceptual_hash(image_path)
    print(f"✅ pHash: {phash_hex[:16]}... (not stored)")

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(gray)
    coeffs1 = pywt.dwt2(img_float, 'haar')
    LL1, (LH1, HL1, HH1) = coeffs1
    coeffs2 = pywt.dwt2(LL1, 'haar')
    LL2, (LH2, HL2, HH2) = coeffs2
    region_names = ['LL2', 'LH2', 'HL2', 'HH2']
    regions = {'LL2': LL2, 'LH2': LH2, 'HL2': HL2, 'HH2': HH2}
    all_features = {}
    print("\nExtracting wavelet features:")
    for name in region_names:
        all_features[name] = extract_wavelet_features(regions[name])
        print(f"  {name}: mean={all_features[name]['mean']:.6f}, "
              f"var={all_features[name]['variance']:.6f}, "
              f"energy={all_features[name]['energy']:.3f}")

    total_bits = len(secret_binary)
    weights = [ll2_weight, lh2_weight, hl2_weight, hh2_weight]
    cum_weights = np.cumsum(weights)
    parts = []
    start = 0
    for i, w in enumerate(weights):
        end = int(round(total_bits * cum_weights[i]))
        if i == len(weights)-1:
            end = total_bits
        parts.append(secret_binary[start:end])
        start = end

    mapping_entries = []
    for i, name in enumerate(region_names):
        mapping_entries.append({'region': name,
                                'vector': all_features[name],
                                'secret_part': parts[i]})

    all_means = [e['vector']['mean'] for e in mapping_entries]
    all_vars = [e['vector']['variance'] for e in mapping_entries]
    all_energies = [e['vector']['energy'] for e in mapping_entries]
    norm_params = {
        'mean_min': min(all_means),
        'mean_max': max(all_means) if max(all_means) != min(all_means) else min(all_means)+1e-6,
        'var_min': min(all_vars),
        'var_max': max(all_vars) if max(all_vars) != min(all_vars) else min(all_vars)+1e-6,
        'energy_min': min(all_energies),
        'energy_max': max(all_energies) if max(all_energies) != min(all_energies) else min(all_energies)+1e-6,
    }

    if hmac_key is not None:
        combined_key = hmac_key + phash_hex.encode()
        enc_key = derive_encryption_key(combined_key)
        fernet = Fernet(enc_key)
        encrypted = fernet.encrypt(pickle.dumps(mapping_entries))

        phash_hash = hashlib.sha256(phash_hex.encode()).hexdigest()

        mapping_dict = {
            'encrypted_entries': encrypted,
            'encrypted': True,
            'phash_hash': phash_hash,
            'norm_params': norm_params,
            'image_shape': gray.shape,
            'region_order': region_names,
            'split_weights': {'LL2': ll2_weight, 'LH2': lh2_weight,
                              'HL2': hl2_weight, 'HH2': hh2_weight},
            'secret_hash': secret_hash,
            'timestamp': str(np.datetime64('now'))
        }
        print("🔒 Encrypted with key derived from DH key + image pHash (pHash not stored).")
    else:
        mapping_dict = {
            'mapping_entries': mapping_entries,
            'encrypted': False,
            'phash_hash': None,
            'norm_params': norm_params,
            'image_shape': gray.shape,
            'region_order': region_names,
            'split_weights': {'LL2': ll2_weight, 'LH2': lh2_weight,
                              'HL2': hl2_weight, 'HH2': hh2_weight},
            'secret_hash': secret_hash,
            'timestamp': str(np.datetime64('now'))
        }
        print("⚠️ No HMAC key – plaintext mapping (insecure).")

    feature_hash = hash(tuple(all_features['LL2'].values()) + tuple(all_features['LH2'].values()) +
                        tuple(all_features['HL2'].values()) + tuple(all_features['HH2'].values()))
    mapping_dict['feature_hash'] = feature_hash

    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    mapping_filename = os.path.join(output_dir, f"mapping_{feature_hash}.pkl")
    with open(mapping_filename, 'wb') as f:
        pickle.dump(mapping_dict, f)
    print(f"✅ Mapping saved: {mapping_filename}")

    # ---- Generate visualization ----
    viz_path = os.path.join(output_dir, 'embedding_visualization.png')
    generate_embedding_visualization(image_path, regions, all_features, mapping_entries, viz_path)

    return mapping_dict, all_features, gray

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True)
    parser.add_argument('-s', '--secret', help='Secret text')
    parser.add_argument('--secret_file', help='Read secret from file')
    parser.add_argument('-o', '--output', default=None)
    parser.add_argument('--ll2_weight', type=float, default=0.5)
    parser.add_argument('--lh2_weight', type=float, default=0.2)
    parser.add_argument('--hl2_weight', type=float, default=0.2)
    parser.add_argument('--hh2_weight', type=float, default=0.1)
    parser.add_argument('--key', help='HMAC key (hex or file)')
    parser.add_argument('--percent', type=float, default=100.0)
    args = parser.parse_args()

    secret = None
    if args.secret_file:
        with open(args.secret_file, 'r', encoding='utf-8') as f:
            secret = f.read().strip()
    elif args.secret:
        secret = args.secret
    else:
        print("Error: provide secret")
        sys.exit(1)

    key = None
    if args.key:
        if os.path.exists(args.key):
            with open(args.key, 'rb') as f:
                key = f.read()
        else:
            key = bytes.fromhex(args.key)

    embed_secret_data(args.image, secret, args.output,
                      args.ll2_weight, args.lh2_weight, args.hl2_weight, args.hh2_weight,
                      key, args.percent)

if __name__ == "__main__":
    main()
