import pywt
import numpy as np

def perform_dwt_decomposition(image, wavelet='haar'):
    """Perform 2-level DWT on each RGB channel"""
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input must be an RGB image")
    
    coeffs = {}
    for i, ch in enumerate(['R', 'G', 'B']):
        # Level 1 DWT
        LL1, (HL1, LH1, HH1) = pywt.dwt2(image[:, :, i], wavelet)
        # Level 2 DWT
        LL2, (HL2, LH2, HH2) = pywt.dwt2(LL1, wavelet)
        
        coeffs[ch] = {
            'LL2': LL2, 'HL2': HL2, 'LH2': LH2, 'HH2': HH2,
            'HL1': HL1, 'LH1': LH1, 'HH1': HH1,
            'LL1_shape': LL1.shape  # Store shape for reconstruction
        }
    
    return coeffs

def reconstruct_image(coeffs, wavelet='haar'):
    """Reconstruct image from modified coefficients"""
    reconstructed_channels = []
    
    for ch in ['R', 'G', 'B']:
        # Level 2 reconstruction
        LL2 = coeffs[ch]['LL2']
        HL2 = coeffs[ch]['HL2']
        LH2 = coeffs[ch]['LH2']
        HH2 = coeffs[ch]['HH2']
        LL1 = pywt.idwt2((LL2, (HL2, LH2, HH2)), wavelet)
        
        # Ensure correct shape
        LL1 = LL1[:coeffs[ch]['LL1_shape'][0], :coeffs[ch]['LL1_shape'][1]]
        
        # Level 1 reconstruction
        HL1 = coeffs[ch]['HL1']
        LH1 = coeffs[ch]['LH1']
        HH1 = coeffs[ch]['HH1']
        channel = pywt.idwt2((LL1, (HL1, LH1, HH1)), wavelet)
        
        reconstructed_channels.append(channel)
    
    # Combine channels and clip to valid range
    reconstructed = np.stack(reconstructed_channels, axis=-1)
    return np.clip(reconstructed, 0, 255).astype('uint8')
