import cv2
import pywt
import matplotlib.pyplot as plt
import os

image_path = input("Enter the image filename (with extension): ").strip()
wavelet_type = input("Enter wavelet type (e.g., haar, db2, sym4): ").strip()

if not os.path.exists(image_path):
    print(f"Error: '{image_path}' not found in current directory.")
    exit()

image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

try:
    coeffs2 = pywt.dwt2(image, wavelet_type)
    LL, (LH, HL, HH) = coeffs2
except Exception as e:
    print(f"Error: Failed to apply wavelet '{wavelet_type}'. Reason: {e}")
    exit()

titles = ['LL - Approximation', 'LH - Vertical Detail',
          'HL - Horizontal Detail', 'HH - Diagonal Detail']
subbands = [LL, LH, HL, HH]

plt.figure(figsize=(10, 8))

for i in range(4):
    plt.subplot(2, 2, i + 1)
    plt.imshow(subbands[i], cmap='gray')
    plt.title(titles[i])
    plt.axis('off')

plt.suptitle(f"2D DWT of '{image_path}' using '{wavelet_type}' Wavelet", fontsize=14)
plt.tight_layout()
plt.subplots_adjust(top=0.90)
plt.show()
