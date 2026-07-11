"""
Extraction – pure DWT features with normalized nearest‑neighbor matching.
Tolerates JPEG compression, Prewitt, Mean, Max filters.
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
    return {
        'mean': float(np.mean(region)),
        'variance': float(np.var(region)),
        'energy': float(np.sum(region ** 2))
    }

def extract_secret_data(image_path, mapping_info_path, hmac_key=None):
    print("\n=== EXTRACTION (Pure DWT Features + Normalized Distance) ===")
    print(f"Image: {image_path}")
    print(f"Mapping: {mapping_info_path}")

    # Load and verify mapping
    if hmac_key:
        with open(mapping_info_path, 'rb') as f:
            file_bytes = f.read()
        sig_path = mapping_info_path.replace('.pkl', '.sig')
        if not os.path.exists(sig_path):
            raise FileNotFoundError("Signature file missing.")
        with open(sig_path, 'r') as f:
            stored_sig = f.read().strip()
        computed_sig = hmac.new(hmac_key, file_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_sig, stored_sig):
            raise ValueError("HMAC MISMATCH!")
        mapping_dict = pickle.loads(file_bytes)
    else:
        with open(mapping_info_path, 'rb') as f:
            mapping_dict = pickle.load(f)

    if mapping_dict.get('encrypted', False):
        if not hmac_key:
            raise ValueError("Encrypted mapping but no key.")
        enc_key = derive_encryption_key(hmac_key)
        fernet = Fernet(enc_key)
        mapping_entries = pickle.loads(fernet.decrypt(mapping_dict['encrypted_entries']))
    else:
        mapping_entries = mapping_dict['mapping_entries']

    region_order = mapping_dict.get('region_order', ['LL2', 'LH2', 'HL2', 'HH2'])
    norm_params = mapping_dict['norm_params']

    # Process received image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not found")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(gray)
    coeffs1 = pywt.dwt2(img_float, 'haar')
    LL1, (LH1, HL1, HH1) = coeffs1
    coeffs2 = pywt.dwt2(LL1, 'haar')
    LL2, (LH2, HL2, HH2) = coeffs2
    regions = {'LL2': LL2, 'LH2': LH2, 'HL2': HL2, 'HH2': HH2}

    # Threshold on normalized distance – tunable
    threshold_norm = 0.4   # Increase to 0.6 or 0.8 if still failing under heavy attacks

    recovered_parts = []
    confidence = 100.0
    match_count = 0

    print("\nNearest‑neighbor lookup results (normalized):")
    for name in region_order:
        query = extract_wavelet_features(regions[name])

        # Normalize query using stored norm_params
        q_mean_norm = (query['mean'] - norm_params['mean_min']) / (norm_params['mean_max'] - norm_params['mean_min'])
        q_var_norm = (query['variance'] - norm_params['var_min']) / (norm_params['var_max'] - norm_params['var_min'])
        q_energy_norm = (query['energy'] - norm_params['energy_min']) / (norm_params['energy_max'] - norm_params['energy_min'])

        best_dist = float('inf')
        best_part = None
        for entry in mapping_entries:
            if entry['region'] != name:
                continue
            v = entry['vector']
            v_mean_norm = (v['mean'] - norm_params['mean_min']) / (norm_params['mean_max'] - norm_params['mean_min'])
            v_var_norm = (v['variance'] - norm_params['var_min']) / (norm_params['var_max'] - norm_params['var_min'])
            v_energy_norm = (v['energy'] - norm_params['energy_min']) / (norm_params['energy_max'] - norm_params['energy_min'])
            dist = np.sqrt((q_mean_norm - v_mean_norm)**2 +
                           (q_var_norm - v_var_norm)**2 +
                           (q_energy_norm - v_energy_norm)**2)
            if dist < best_dist:
                best_dist = dist
                best_part = entry['secret_part']

        if best_part is not None and best_dist <= threshold_norm:
            recovered_parts.append(best_part)
            match_count += 1
            print(f"  {name}: ✅ Distance={best_dist:.4f} → {best_part[:20]}...")
        else:
            print(f"  {name}: ❌ No close match (dist={best_dist:.4f} > {threshold_norm})")
            confidence -= 25

    if match_count != 4:
        print(f"\n❌ Extraction failed – only {match_count}/4 regions matched.")
        return None, None, max(0, confidence), False

    recovered_binary = ''.join(recovered_parts)

    byte_array = bytearray()
    for i in range(0, len(recovered_binary), 8):
        chunk = recovered_binary[i:i+8]
        if len(chunk) == 8:
            byte_array.append(int(chunk, 2))
    try:
        plaintext_secret = bytes(byte_array).decode('utf-8')
    except UnicodeDecodeError:
        plaintext_secret = bytes(byte_array).decode('utf-8', errors='replace')

    stored_hash = mapping_dict.get('secret_hash')
    hash_match = False
    if stored_hash and plaintext_secret:
        computed_hash = hashlib.sha256(plaintext_secret.encode('utf-8')).hexdigest()
        hash_match = (computed_hash == stored_hash)

    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"Recovered secret: {plaintext_secret}")
    print(f"Confidence: {confidence:.2f}%")
    print(f"Hash match: {'✅' if hash_match else '❌'}")
    if hmac_key:
        print("HMAC: ✅ Authentic")
    return plaintext_secret, None, confidence, hash_match

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True)
    parser.add_argument('-m', '--mapping', required=True)
    parser.add_argument('--key', help='HMAC key')
    parser.add_argument('-o', '--output', help='Save secret to file')
    args = parser.parse_args()

    key = None
    if args.key:
        if os.path.exists(args.key):
            with open(args.key, 'rb') as f:
                key = f.read()
        else:
            key = bytes.fromhex(args.key)

    secret, _, confidence, hash_ok = extract_secret_data(args.image, args.mapping, key)
    if args.output and secret:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(secret)
        print(f"Secret saved to {args.output}")
    sys.exit(0 if hash_ok else 1)

if __name__ == "__main__":
    main()
