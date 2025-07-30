import numpy as np
from skimage.filters.rank import entropy
from skimage.morphology import disk

def calculate_global_entropy(image):
    """Calculate global entropy of an RGB image"""
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input must be an RGB image")
    
    channel_entropies = []
    for ch in range(3):  # Process each channel (R, G, B)
        channel = image[:, :, ch]
        channel_ent = entropy(channel.astype('uint8'), disk(5))
        channel_entropies.append(np.mean(channel_ent))
    
    return np.mean(channel_entropies)
