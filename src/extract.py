"""
Extraction – tries all pHashes within Hamming distance 3 of the computed pHash.
The .pkl stores only the hash of the original pHash, so image is required.
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
from itertools import combinations
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

def hamming_distance(hex1, hex2):
    if len(hex1) != len(hex2):
        if len(hex1) < len(hex2):
            hex1 = hex1.zfill(len(hex2))
        else:
            hex2 = hex2.zfill(len(hex1))
    return bin(int(hex1, 16) ^ int(hex2, 16)).count('1')

def generate_candidates(phash_hex, max_dist=3):
    """Generate all hex strings within Hamming distance <= max_dist from the given pHash."""
    # Convert hex to binary string (length = 64 hex * 4 = 256 bits)
    bin_str = bin(int(phash_hex, 16))[2:].zfill(256)
    n = len(bin_str)
    candidates = [phash_hex]  # original
    # We'll generate up to distance 3
    for dist in range(1, max_dist+1):
        for positions in combinations(range(n), dist):
            # flip bits at positions
            bits = list(bin_str)
            for pos in positions:
                bits[pos] = '1' if bits[pos] == '0' else '0'
            cand_bin = ''.join(bits)
            cand_hex = hex(int(cand_bin, 2))[2:].zfill(64)
            candidates.append(cand_hex)
    return candidates

def extract_secret_data(image_path, mapping_info_path, hmac_key=None):
    print("\n=== EXTRACTION (Image‑tied decryption, pHash brute‑force) ===")
    print(f"Image: {image_path}")
    print(f"Mapping: {mapping_info_path}")

    # ---------- Load .pkl ----------
    with open(mapping_info_path, 'rb') as f:
        mapping_dict = pickle.load(f)

    # ---------- Image verification via pHash candidates ----------
    if mapping_dict.get('encrypted', False):
        if hmac_key is None:
            raise ValueError("Encrypted mapping but no HMAC key provided.")

        # Compute pHash of received image
        received_phash = compute_perceptual_hash(image_path)
        stored_phash_hash = mapping_dict['phash_hash']

        # Generate all candidates within Hamming distance 3 (adjustable)
        MAX_DIST = 3
        candidates = generate_candidates(received_phash, max_dist=MAX_DIST)
        print(f"\n🔍 Trying {len(candidates)} candidate pHashes (max distance {MAX_DIST})...")

        found_key = False
        mapping_entries = None
        for i, cand_phash in enumerate(candidates):
            # Verify hash matches stored
            if hashlib.sha256(cand_phash.encode()).hexdigest() != stored_phash_hash:
                continue
            # Try to decrypt using this pHash
            combined_key = hmac_key + cand_phash.encode()
            enc_key = derive_encryption_key(combined_key)
            fernet = Fernet(enc_key)
            try:
                mapping_entries = pickle.loads(fernet.decrypt(mapping_dict['encrypted_entries']))
                print(f"✅ Decryption successful with candidate pHash (distance = {hamming_distance(received_phash, cand_phash)} bits).")
                found_key = True
                break
            except Exception:
                continue

        if not found_key:
            print("❌ No candidate pHash matched the stored hash. Image does not match.")
            return None, None, 0.0, False
    else:
        mapping_entries = mapping_dict['mapping_entries']
        print("⚠️ Mapping is in plaintext.")

    # ---------- Nearest‑neighbor matching ----------
    region_order = mapping_dict.get('region_order', ['LL2', 'LH2', 'HL2', 'HH2'])
    norm_params = mapping_dict['norm_params']

    # Process received image for feature extraction
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

    query_features = {}
    for name in region_order:
        query_features[name] = extract_wavelet_features(regions[name])

    recovered_parts = []
    confidence = 100.0
    match_count = 0
    threshold = 0.8   # tolerant

    print("\nNearest-neighbor matching (threshold = {:.2f}):".format(threshold))
    for name in region_order:
        q = query_features[name]
        q_mean_norm = (q['mean'] - norm_params['mean_min']) / (norm_params['mean_max'] - norm_params['mean_min'])
        q_var_norm = (q['variance'] - norm_params['var_min']) / (norm_params['var_max'] - norm_params['var_min'])
        q_energy_norm = (q['energy'] - norm_params['energy_min']) / (norm_params['energy_max'] - norm_params['energy_min'])

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

        print(f"  {name}: best distance = {best_dist:.4f} (threshold = {threshold:.2f})")

        if best_part is not None and best_dist <= threshold:
            recovered_parts.append(best_part)
            match_count += 1
            print(f"    ✅ Match accepted.")
        else:
            print(f"    ❌ Match rejected (distance > threshold).")
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
    if hmac_key is not None:
        print("DH key: ✅ used for decryption")
    return plaintext_secret, None, confidence, hash_match

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True)
    parser.add_argument('-m', '--mapping', required=True)
    parser.add_argument('--key', help='HMAC key (hex or file)')
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
