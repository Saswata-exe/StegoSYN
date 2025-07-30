import cv2
import numpy as np

def generate_mask_image(image, selected_blocks, output_path="embedding_mask.png"):
    """Generate visualization of embedding regions"""
    mask = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
    
    # Colors for each channel (BGR-A format)
    colors = {
        'R': (0, 0, 255, 128),
        'G': (0, 255, 0, 128),
        'B': (255, 0, 0, 128)
    }
    
    for ch in ['R', 'G', 'B']:
        for block in selected_blocks[ch]:
            i, j = block['coords']
            x1, y1 = j * 4, i * 4  # Scale to original image size
            x2, y2 = x1 + 32, y1 + 32
            cv2.rectangle(mask, (x1, y1), (x2, y2), colors[ch], -1)
    
    # Overlay on original image
    overlay = cv2.cvtColor(image, cv2.COLOR_RGB2BGRA)
    combined = cv2.addWeighted(overlay, 1.0, mask, 0.5, 0)
    cv2.imwrite(output_path, combined)
    return combined
