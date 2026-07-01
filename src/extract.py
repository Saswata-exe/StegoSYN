"""
Coverless Steganography – Extraction with HMAC verification + Decryption.
If the mapping file contains encrypted secret, decryption is performed.
"""

import cv2
import numpy as np
import pywt
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
    """Must be identical to the one in embed.py."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'encryption-key-for-secret',
        backend=default_backend()
    )
    key = hkdf.derive(hmac_key)
    return base64.urlsafe_b64encode(key)

def extract_secret_data(image_path, mapping_info_path, hmac_key=None):
    print("\n" + "="*60)
    print("COVERLESS STEGANOGRAPHY - EXTRACTION (HMAC + DECRYPTION)")
    print("="*60)
    
    # ---------- Load & verify mapping file ----------
    print("1. Loading mapping file...")
    if hmac_key:
        with open(mapping_info_path, 'rb') as f:
            file_bytes = f.read()
        sig_path = mapping_info_path.replace('.pkl', '.sig')
        if not os.path.exists(sig_path):
            print(f"❌ ERROR: Signature file '{sig_path}' not found.")
            sys.exit(1)
        with open(sig_path, 'r') as f:
            stored_sig = f.read().strip()
        computed_sig = hmac.new(hmac_key, file_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_sig, stored_sig):
            print("❌ HMAC MISMATCH – MAPPING FILE HAS BEEN TAMPERED WITH!")
            sys.exit(1)
        else:
            print("   ✓ HMAC verification successful. Mapping file is authentic.")
        mapping_dict = pickle.loads(file_bytes)
    else:
        print("⚠️ No HMAC key – integrity not checked.")
        with open(mapping_info_path, 'rb') as f:
            mapping_dict = pickle.load(f)
    
    print(f"   ✓ Mapping file loaded: {mapping_info_path}")
    stored_hash = mapping_dict.get('secret_hash', None)
    if stored_hash:
        print(f"   ✓ Stored secret hash: {stored_hash}")
    
    # Handle old format
    if 'region_mappings' not in mapping_dict:
        print("   ⚠ Old mapping format. Adapting...")
        region_mappings = [{'region': 'LL2', 'features': mapping_dict['features'], 'secret_part': mapping_dict['secret_binary']}]
    else:
        region_mappings = mapping_dict['region_mappings']
    
    # ---------- Process image ----------
    print("\n2. Processing received image...")
    img_color = cv2.imread(image_path)
    if img_color is None:
        print(f"❌ ERROR: Could not load image {image_path}")
        sys.exit(1)
    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    img_float = img_as_float(img_gray)
    
    # DWT
    print("3. Applying DWT...")
    wavelet_type = mapping_dict.get('wavelet_type', 'haar')
    level = mapping_dict.get('decomposition_level', 2)
    if level == 2:
        LL1, (LH1, HL1, HH1) = pywt.dwt2(img_float, wavelet_type)
        LL2, (LH2, HL2, HH2) = pywt.dwt2(LL1, wavelet_type)
        extracted_regions = {'LL2': LL2, 'LH2': LH2, 'HL2': HL2, 'HH2': HH2}
    else:
        LL1, (LH1, HL1, HH1) = pywt.dwt2(img_float, wavelet_type)
        extracted_regions = {'LL1': LL1, 'LH1': LH1, 'HL1': HL1, 'HH1': HH1}
    print(f"   ✓ DWT applied (wavelet={wavelet_type}, level={level})")
    
    # ---------- Feature comparison ----------
    print("4. Extracting and comparing features...")
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
        else:
            features['mean'] = np.mean(region)
            features['variance'] = np.var(region)
            hist, _ = np.histogram(region.flatten(), bins=256, range=(region.min(), region.max()))
            prob = hist / hist.sum()
            prob = prob[prob > 0]
            features['entropy'] = -np.sum(prob * np.log2(prob))
        return features
    
    overall_score = 0.0
    recovered_parts = []
    print("   " + "-"*65)
    for rm in region_mappings:
        region_name = rm['region']
        if region_name not in extracted_regions:
            print(f"   ⚠ Region {region_name} not found. Skipping.")
            continue
        extracted_feat = extract_features(extracted_regions[region_name], region_name)
        stored_feat = rm['features']
        diffs = {}
        for key in stored_feat.keys():
            orig = stored_feat[key]
            if key not in extracted_feat:
                diffs[key] = 100.0
                continue
            extr = extracted_feat[key]
            diff_percent = (abs(orig - extr) / (abs(orig) + 1e-10)) * 100
            diffs[key] = diff_percent
        avg_diff = np.mean(list(diffs.values()))
        match_score = max(0, 100 - avg_diff)
        overall_score += match_score
        
        if region_name in ['LL2', 'LH2']:
            print(f"   {region_name:4} | Match: {match_score:6.2f}% | Mean diff: {diffs['mean']:6.2f}% | Var diff: {diffs['variance']:6.2f}%")
        elif region_name == 'HL2':
            print(f"   {region_name:4} | Match: {match_score:6.2f}% | Aspect diff: {diffs['aspect_ratio']:6.2f}% | TotEnergy diff: {diffs['total_energy']:6.2f}% | RMS diff: {diffs['rms_energy']:6.2f}%")
        else:
            print(f"   {region_name:4} | Match: {match_score:6.2f}% | Mean diff: {diffs['mean']:6.2f}% | Var diff: {diffs['variance']:6.2f}%")
        recovered_parts.append(rm['secret_part'])
    print("   " + "-"*65)
    if region_mappings:
        overall_score /= len(region_mappings)
    
    # ---------- Recover binary and decrypted text ----------
    recovered_binary = ''.join(recovered_parts)
    # Get the plaintext secret (either from encryption or plaintext)
    plaintext_secret = None
    if hmac_key and 'encrypted_secret' in mapping_dict:
        try:
            enc_key = derive_encryption_key(hmac_key)
            fernet = Fernet(enc_key)
            plaintext_secret = fernet.decrypt(mapping_dict['encrypted_secret']).decode('utf-8')
            print("🔓 Secret decrypted successfully.")
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            plaintext_secret = None
    elif 'secret_text' in mapping_dict:
        plaintext_secret = mapping_dict['secret_text']   # legacy plaintext
    else:
        # If no plaintext and no encrypted, try to convert binary to text (fallback)
        try:
            chars = [recovered_binary[i:i+8] for i in range(0, len(recovered_binary), 8)]
            plaintext_secret = ''.join(chr(int(char, 2)) for char in chars)
        except:
            plaintext_secret = "EXTRACTION FAILED"
    
    # ---------- Verify hash ----------
    hash_match = False
    if stored_hash and plaintext_secret:
        computed_hash = hashlib.sha256(plaintext_secret.encode('utf-8')).hexdigest()
        hash_match = (computed_hash == stored_hash)
        hash_status = "✅ MATCH" if hash_match else "❌ MISMATCH"
    else:
        hash_status = "⚠️ No hash stored"
    
    # ---------- Results ----------
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"📨 Recovered secret: {plaintext_secret}")
    print(f"📊 Match confidence: {overall_score:.1f}%")
    print(f"🔐 Secret hash:       {hash_status}")
    if hmac_key:
        print(f"🔑 HMAC verification: ✅ Mapping file is authentic")
        print(f"🔒 Encryption:         ✅ Secret was decrypted using the key")
    else:
        print(f"🔑 HMAC verification: ⚠️ Not performed (no key)")
        print(f"🔒 Encryption:         ⚠️ Secret may be in plaintext")
    if hash_match and hmac_key:
        print("   ✅ Fully verified: secret is authentic and mapping file is trusted.")
    print("="*60)
    return plaintext_secret, None, overall_score, hash_match

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True)
    parser.add_argument('-m', '--mapping', required=True)
    parser.add_argument('--key', help='HMAC key (hex or file) – also used for decryption')
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
    try:
        secret, _, confidence, hash_ok = extract_secret_data(args.image, args.mapping, hmac_key)
        sys.exit(0 if hash_ok else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
