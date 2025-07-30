import numpy as np
from reedsolo import RSCodec
import zlib

def add_error_protection(data):
    """Add Reed-Solomon (RS255,223) and CRC32 checksum"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Reed-Solomon encoding (32 parity bytes)
    rs = RSCodec(32)
    rs_encoded = rs.encode(data)
    
    # Add CRC32 checksum
    crc = zlib.crc32(rs_encoded).to_bytes(4, 'big')
    protected_data = rs_encoded + crc
    
    return protected_data

def embed_data(coeffs, selected_blocks, secret_data):
    """Embed data using QIM with distortion compensation"""
    protected_data = add_error_protection(secret_data)
    binary_data = ''.join(format(byte, '08b') for byte in protected_data)
    data_index = 0
    
    Q_values = {'R': 12, 'G': 20, 'B': 16}  # Channel-specific Q
    
    for ch in ['R', 'G', 'B']:
        for block_info in selected_blocks[ch]:
            i, j = block_info['coords']
            subband = block_info['subband']
            Q = Q_values[ch]
            
            for x in range(8):
                for y in range(8):
                    if data_index >= len(binary_data):
                        break
                    
                    C = coeffs[ch][subband][i+x, j+y]
                    quantized_val = np.round(C / Q) * Q
                    bit = int(binary_data[data_index])
                    coeffs[ch][subband][i+x, j+y] = quantized_val + (Q / 2.5) * (2 * bit - 1)
                    
                    # Distortion compensation
                    if y+1 < 8:
                        C_prime = coeffs[ch][subband][i+x, j+y+1]
                        coeffs[ch][subband][i+x, j+y+1] = C_prime - (Q / 5.0) * (2 * bit - 1)
                    
                    data_index += 1

    return coeffs
