import numpy as np
from skimage.filters.rank import entropy
from skimage.morphology import disk

def select_blocks_for_embedding(coeffs, global_entropy):
    """Select 8x8 blocks in LH2/HL2 with local entropy > threshold"""
    E_threshold = 0.5 * global_entropy + 2.0
    selected_blocks = {'R': [], 'G': [], 'B': []}
    
    for ch in ['R', 'G', 'B']:
        for subband in ['LH2', 'HL2']:
            coeff = coeffs[ch][subband]
            for i in range(0, coeff.shape[0] - 8, 8):
                for j in range(0, coeff.shape[1] - 8, 8):
                    block = coeff[i:i+8, j:j+8]
                    local_ent = entropy(block.astype('uint8'), disk(3)).mean()
                    
                    if local_ent > E_threshold:
                        selected_blocks[ch].append({
                            'subband': subband,
                            'coords': (i, j),
                            'entropy': local_ent
                        })
    
    return selected_blocks
