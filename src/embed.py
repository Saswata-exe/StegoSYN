"""
Coverless Steganography – Embedding with HMAC + Encryption.
If HMAC key is provided, the secret is encrypted before storage.
"""

import cv2
import numpy as np
import pywt
import matplotlib.pyplot as plt
import sys
import argparse
import pickle
import hashlib
import hmac
import os
import base64
from skimage import img_as_float
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

def derive_encryption_key(hmac_key):
    """Derive a 32-byte encryption key from the HMAC key using HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'encryption-key-for-secret',
        backend=default_backend()
    )
    key = hkdf.derive(hmac_key)
    return base64.urlsafe_b64encode(key)  # Fernet expects base64

def embed_secret_data(image_path, secret_text, output_viz_path='mapping_visualization.png',
                      ll2_weight=0.5, lh2_weight=0.2, hl2_weight=0.2, hh2_weight=0.1,
                      hmac_key=None):
    if abs(ll2_weight + lh2_weight + hl2_weight + hh2_weight - 1.0) > 1e-6:
        raise ValueError("Weights must sum to 1.0")
    
    print("\n" + "="*60)
    print("COVERLESS STEGANOGRAPHY - EMBEDDING (HMAC + ENCRYPTION)")
    print("="*60)
    print(f"Image: {image_path}")
    print(f"Secret: '{secret_text}'")
    print(f"Weights: LL2={ll2_weight:.2f}, LH2={lh2_weight:.2f}, HL2={hl2_weight:.2f}, HH2={hh2_weight:.2f}")
    if hmac_key:
        print(f"HMAC key: {hmac_key.hex()[:16]}...")
        print("🔒 Secret will be encrypted in the mapping file.")
    else:
        print("⚠️ No HMAC key – secret stored in plaintext and no integrity protection.")
    print("="*60 + "\n")
    
    # Compute hash of plaintext secret
    secret_hash = hashlib.sha256(secret_text.encode('utf-8')).hexdigest()
    print(f"✓ Secret SHA-256 hash: {secret_hash[:16]}...")
    
    # Load and preprocess image
    img_color = cv2.imread(image_path)
    if img_color is None:
        raise ValueError(f"Could not load image {image_path}")
    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(img_gray)
    
    # DWT 2-level
    coeffs1 = pywt.dwt2(img_float, 'haar')
    LL1, (LH1, HL1, HH1) = coeffs1
    coeffs2 = pywt.dwt2(LL1, 'haar')
    LL2, (LH2, HL2, HH2) = coeffs2
    regions = {'LL2': LL2, 'LH2': LH2, 'HL2': HL2, 'HH2': HH2}
    
    def extract_features(region, name):
        features = {}
        if name in ['LL2', 'LH2']:
            features['mean'] = np.mean(region)
            features['variance'] = np.var(region)
            features['energy'] = np.sum(region ** 2)
            hist, _ = np.histogram(region.flatten(), bins=256, range=(region.min(), region.max()))
            prob = hist / hist.sum()
            prob = prob[prob > 0]
            features['entropy'] = -np.sum(prob * np.log2(prob))
        elif name == 'HL2':
            h, w = region.shape
            features['aspect_ratio'] = h / w if w != 0 else 1.0
            features['total_energy'] = np.sum(region ** 2)
            features['rms_energy'] = np.sqrt(np.mean(region ** 2))
        else:  # HH2
            features['mean'] = np.mean(region)
            features['variance'] = np.var(region)
            hist, _ = np.histogram(region.flatten(), bins=256, range=(region.min(), region.max()))
            prob = hist / hist.sum()
            prob = prob[prob > 0]
            features['entropy'] = -np.sum(prob * np.log2(prob))
        return features
    
    all_features = {name: extract_features(regions[name], name) for name in regions}
    
    # Split secret
    secret_binary = ''.join(format(ord(c), '08b') for c in secret_text)
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
    if sum(len(p) for p in parts) != total_bits:
        parts[-1] = secret_binary[sum(len(p) for p in parts[:-1]):]
    
    region_names = ['LL2', 'LH2', 'HL2', 'HH2']
    region_mappings = []
    for i, name in enumerate(region_names):
        region_mappings.append({
            'region': name,
            'features': all_features[name],
            'secret_part': parts[i]
        })
    
    # Build mapping dictionary
    mapping_dict = {
        'secret_hash': secret_hash,       # hash of plaintext (for verification)
        'secret_binary': secret_binary,
        'region_mappings': region_mappings,
        'all_features': all_features,
        'image_shape': img_gray.shape,
        'image_path': image_path,
        'wavelet_type': 'haar',
        'decomposition_level': 2,
        'split_weights': {'LL2': ll2_weight, 'LH2': lh2_weight, 'HL2': hl2_weight, 'HH2': hh2_weight},
        'timestamp': np.datetime64('now')
    }
    feature_hash = hash(tuple(all_features['LL2'].values()) + tuple(all_features['LH2'].values()) +
                        tuple(all_features['HL2'].values()) + tuple(all_features['HH2'].values()))
    mapping_dict['feature_hash'] = feature_hash
    
    # Encrypt the secret if key is provided
    if hmac_key:
        enc_key = derive_encryption_key(hmac_key)
        fernet = Fernet(enc_key)
        encrypted = fernet.encrypt(secret_text.encode('utf-8'))
        mapping_dict['encrypted_secret'] = encrypted
        # No plaintext stored
    else:
        mapping_dict['secret_text'] = secret_text   # plaintext (for backward compatibility)
    
    # Save .pkl
    mapping_filename = f"mapping_{feature_hash}.pkl"
    with open(mapping_filename, 'wb') as f:
        pickle.dump(mapping_dict, f)
    print(f"✓ Mapping file saved: {mapping_filename}")
    
    # HMAC signature
    if hmac_key:
        with open(mapping_filename, 'rb') as f:
            file_bytes = f.read()
        sig = hmac.new(hmac_key, file_bytes, hashlib.sha256).hexdigest()
        sig_filename = f"mapping_{feature_hash}.sig"
        with open(sig_filename, 'w') as f:
            f.write(sig)
        print(f"✓ HMAC signature saved: {sig_filename}")
    else:
        print("⚠️ No signature created.")
    
    # Simple visualisation
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, f"Mapping created\nSecret: {'🔒 Encrypted' if hmac_key else secret_text[:20]+'...'}", ha='center', va='center')
    ax.set_title("Embedding Summary")
    ax.axis('off')
    plt.savefig(output_viz_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✓ Visualization saved: {output_viz_path}")
    
    print("\n" + "="*60)
    print("EMBEDDING COMPLETE")
    print("="*60)
    print(f"Image:              {image_path} (unmodified)")
    print(f"Mapping file:       {mapping_filename}")
    if hmac_key:
        print(f"Signature file:     {sig_filename}")
        print("🔒 Secret is encrypted – only the receiver with the key can read it.")
        print("🔑 The receiver must have the SAME HMAC/encryption key.")
    else:
        print("⚠️ Secret stored in plaintext – anyone with the mapping file can read it.")
    print(f"Secret hash:        {secret_hash}")
    print("="*60)
    return mapping_dict, all_features, img_gray

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True)
    parser.add_argument('-s', '--secret', required=True)
    parser.add_argument('-o', '--output', default='mapping_visualization.png')
    parser.add_argument('--ll2_weight', type=float, default=0.5)
    parser.add_argument('--lh2_weight', type=float, default=0.2)
    parser.add_argument('--hl2_weight', type=float, default=0.2)
    parser.add_argument('--hh2_weight', type=float, default=0.1)
    parser.add_argument('--key', help='HMAC key (hex or file) – enables encryption')
    args = parser.parse_args()
    hmac_key = None
    if args.key:
        try:
            if os.path.exists(args.key):
                with open(args.key, 'rb') as f:
                    hmac_key = f.read()
            else:
                hmac_key = bytes.fromhex(args.key)
        except:
            print("Error reading key.")
            sys.exit(1)
    embed_secret_data(args.image, args.secret, args.output,
                      args.ll2_weight, args.lh2_weight, args.hl2_weight, args.hh2_weight,
                      hmac_key)

if __name__ == "__main__":
    main()
