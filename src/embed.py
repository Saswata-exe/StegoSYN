"""
Embedding – pure DWT features (mean, variance, energy) from each sub‑band.
Normalized feature vectors and nearest‑neighbor matching.
"""

import cv2
import numpy as np
import pywt
import pickle
import hashlib
import hmac
import os
import sys
import argparse
import base64
from skimage import img_as_float
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

def derive_encryption_key(hmac_key):
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b'encryption-key-for-secret', backend=default_backend())
    key = hkdf.derive(hmac_key)
    return base64.urlsafe_b64encode(key)

def extract_wavelet_features(region):
    """Extract mean, variance, energy directly from wavelet coefficients."""
    return {
        'mean': float(np.mean(region)),
        'variance': float(np.var(region)),
        'energy': float(np.sum(region ** 2))
    }

def embed_secret_data(image_path, secret_text, output_dir=None,
                      ll2_weight=0.5, lh2_weight=0.2, hl2_weight=0.2, hh2_weight=0.1,
                      hmac_key=None, embed_percent=100.0):
    if abs(ll2_weight + lh2_weight + hl2_weight + hh2_weight - 1.0) > 1e-6:
        raise ValueError("Weights must sum to 1.0")

    if embed_percent < 100.0:
        new_len = max(1, int(len(secret_text) * embed_percent / 100.0))
        secret_text = secret_text[:new_len]
        print(f"✂️ Embedding {embed_percent:.1f}% of secret")

    print("\n=== EMBEDDING (Pure DWT Features + Normalized Distance) ===")
    print(f"Secret: '{secret_text[:50]}'")

    secret_bytes = secret_text.encode('utf-8')
    secret_binary = ''.join(format(byte, '08b') for byte in secret_bytes)
    print(f"Binary length: {len(secret_binary)} bits")

    secret_hash = hashlib.sha256(secret_text.encode('utf-8')).hexdigest()
    print(f"Hash: {secret_hash[:16]}...")

    # Load image, DWT
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not found")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(gray)

    coeffs1 = pywt.dwt2(img_float, 'haar')
    LL1, (LH1, HL1, HH1) = coeffs1
    coeffs2 = pywt.dwt2(LL1, 'haar')
    LL2, (LH2, HL2, HH2) = coeffs2

    region_names = ['LL2', 'LH2', 'HL2', 'HH2']
    regions = {'LL2': LL2, 'LH2': LH2, 'HL2': HL2, 'HH2': HH2}

    # Extract wavelet features from each region
    all_vectors = {}
    print("\nExtracting wavelet features from each sub‑band:")
    for name in region_names:
        all_vectors[name] = extract_wavelet_features(regions[name])
        print(f"  {name}: mean={all_vectors[name]['mean']:.6f}, "
              f"var={all_vectors[name]['variance']:.6f}, "
              f"energy={all_vectors[name]['energy']:.3f}")

    # Split secret binary by weights
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

    # Build mapping entries
    mapping_entries = []
    for i, name in enumerate(region_names):
        mapping_entries.append({
            'region': name,
            'vector': all_vectors[name],
            'secret_part': parts[i]
        })
        print(f"  {name}: vector={all_vectors[name]} → {parts[i][:20]}...")

    # Compute normalization ranges
    all_means = [e['vector']['mean'] for e in mapping_entries]
    all_vars = [e['vector']['variance'] for e in mapping_entries]
    all_energies = [e['vector']['energy'] for e in mapping_entries]

    norm_params = {
        'mean_min': min(all_means),
        'mean_max': max(all_means) if max(all_means) != min(all_means) else min(all_means) + 1e-6,
        'var_min': min(all_vars),
        'var_max': max(all_vars) if max(all_vars) != min(all_vars) else min(all_vars) + 1e-6,
        'energy_min': min(all_energies),
        'energy_max': max(all_energies) if max(all_energies) != min(all_energies) else min(all_energies) + 1e-6,
    }

    feature_hash = hash(tuple(all_vectors['LL2'].values()) + tuple(all_vectors['LH2'].values()) +
                        tuple(all_vectors['HL2'].values()) + tuple(all_vectors['HH2'].values()))

    mapping_dict = {
        'mapping_entries': mapping_entries,
        'norm_params': norm_params,
        'image_shape': gray.shape,
        'region_order': region_names,
        'split_weights': {'LL2': ll2_weight, 'LH2': lh2_weight,
                          'HL2': hl2_weight, 'HH2': hh2_weight},
        'secret_hash': secret_hash,
        'feature_hash': feature_hash,
        'timestamp': str(np.datetime64('now')),
        'encrypted': False
    }

    if hmac_key:
        enc_key = derive_encryption_key(hmac_key)
        fernet = Fernet(enc_key)
        mapping_dict['encrypted_entries'] = fernet.encrypt(pickle.dumps(mapping_entries))
        mapping_dict['encrypted'] = True
        del mapping_dict['mapping_entries']
    else:
        mapping_dict['encrypted'] = False

    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    mapping_filename = os.path.join(output_dir, f"mapping_{feature_hash}.pkl")
    with open(mapping_filename, 'wb') as f:
        pickle.dump(mapping_dict, f)
    print(f"\n✅ Mapping saved: {mapping_filename}")

    if hmac_key:
        with open(mapping_filename, 'rb') as f:
            file_bytes = f.read()
        sig = hmac.new(hmac_key, file_bytes, hashlib.sha256).hexdigest()
        sig_filename = os.path.join(output_dir, f"mapping_{feature_hash}.sig")
        with open(sig_filename, 'w') as f:
            f.write(sig)
        print(f"✅ Signature saved: {sig_filename}")

    print("="*60 + "\n")
    return mapping_dict, all_vectors, gray

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
    parser.add_argument('--key', help='HMAC key')
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

