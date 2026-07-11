import tkinter as tk
from tkinter import filedialog, OptionMenu, StringVar, Button, Label, Frame
from PIL import Image, ImageTk
import cv2
import numpy as np
import os


class ImageFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Filtering Tool - Color Output")
        self.root.geometry("1000x600")

        # Variables
        self.image_path = None
        self.original_img = None   # BGR numpy array
        self.filtered_img = None   # BGR numpy array

        # Filter options
        self.filter_options = [
            "Mean",
            "Median",
            "Min",
            "Max",
            "Gaussian Blur",
            "Laplacian",
            "Sobel X",
            "Sobel Y",
            "Prewitt X",
            "Prewitt Y",
            "Unsharp Masking",
            "Sharpen",
            "Emboss"
        ]
        self.selected_filter = StringVar(root)
        self.selected_filter.set("Mean")

        # --- Top Control Frame ---
        control_frame = Frame(root)
        control_frame.pack(pady=10)

        Button(control_frame, text="📂 Upload Image", command=self.upload_image,
               font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=5)

        OptionMenu(control_frame, self.selected_filter, *self.filter_options).pack(side=tk.LEFT, padx=5)

        Button(control_frame, text="⚡ Apply Filter", command=self.apply_filter,
               font=("Arial", 10), bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        Button(control_frame, text="💾 Save Output", command=self.save_image,
               font=("Arial", 10), bg="#2196F3", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        # --- Image Display Frames ---
        display_frame = Frame(root)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Original Image
        left_frame = Frame(display_frame, bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        Label(left_frame, text="Original Image", font=("Arial", 12, "bold")).pack()
        self.original_label = Label(left_frame, bg="#f0f0f0")
        self.original_label.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Filtered Image
        right_frame = Frame(display_frame, bd=2, relief=tk.SUNKEN)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        Label(right_frame, text="Filtered Image (Color)", font=("Arial", 12, "bold")).pack()
        self.filtered_label = Label(right_frame, bg="#f0f0f0")
        self.filtered_label.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Status bar
        self.status_label = Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Store image references
        self.original_photo = None
        self.filtered_photo = None

    def update_status(self, msg):
        self.status_label.config(text=msg)

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if not file_path:
            return

        self.image_path = file_path
        self.original_img = cv2.imread(file_path)
        if self.original_img is None:
            self.update_status("❌ Failed to load image!")
            return

        self.update_status(f"✅ Loaded: {os.path.basename(file_path)}")
        self.display_image(self.original_img, self.original_label, is_original=True)
        self.filtered_label.config(image="")
        self.filtered_label.image = None
        self.filtered_img = None

    def display_image(self, img_bgr, target_label, is_original=True):
        if img_bgr is None:
            return

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        max_size = 400
        w, h = pil_img.size
        if w > h:
            new_w = min(w, max_size)
            new_h = int(h * (new_w / w))
        else:
            new_h = min(h, max_size)
            new_w = int(w * (new_h / h))
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(pil_img)
        target_label.config(image=photo)
        if is_original:
            self.original_photo = photo
        else:
            self.filtered_photo = photo

    def apply_filter(self):
        if self.original_img is None:
            self.update_status("⚠️ Please upload an image first!")
            return

        filter_type = self.selected_filter.get()
        self.update_status(f"⏳ Applying {filter_type} (color output)...")

        img = self.original_img.copy()
        result = None

        # ---------- SMOOTHING (preserve color by default) ----------
        if filter_type == "Mean":
            result = cv2.blur(img, (5, 5))

        elif filter_type == "Median":
            result = cv2.medianBlur(img, 5)

        elif filter_type == "Gaussian Blur":
            result = cv2.GaussianBlur(img, (5, 5), 0)

        # ---------- MORPHOLOGICAL (now applied per channel → color) ----------
        elif filter_type == "Min":
            kernel = np.ones((5, 5), np.uint8)
            result = cv2.erode(img, kernel)          # works on multi-channel

        elif filter_type == "Max":
            kernel = np.ones((5, 5), np.uint8)
            result = cv2.dilate(img, kernel)         # works on multi-channel

        # ---------- EDGE DETECTION (now per channel → color edges) ----------
        elif filter_type == "Laplacian":
            res = cv2.Laplacian(img, cv2.CV_64F)     # 3‑channel output
            result = np.uint8(np.absolute(res))

        elif filter_type == "Sobel X":
            res = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
            result = np.uint8(np.absolute(res))

        elif filter_type == "Sobel Y":
            res = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
            result = np.uint8(np.absolute(res))

        elif filter_type == "Prewitt X":
            kernel_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
            res = cv2.filter2D(img, cv2.CV_64F, kernel_x)   # per‑channel
            result = np.uint8(np.absolute(res))

        elif filter_type == "Prewitt Y":
            kernel_y = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], dtype=np.float32)
            res = cv2.filter2D(img, cv2.CV_64F, kernel_y)   # per‑channel
            result = np.uint8(np.absolute(res))

        # ---------- SHARPENING / MASKING (already color) ----------
        elif filter_type == "Unsharp Masking":
            blurred = cv2.GaussianBlur(img, (0, 0), 3.0)
            result = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

        elif filter_type == "Sharpen":
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            result = cv2.filter2D(img, -1, kernel)

        elif filter_type == "Emboss":
            kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
            result = cv2.filter2D(img, -1, kernel)

        else:
            self.update_status("⚠️ Unknown filter selected.")
            return

        if result is None:
            self.update_status("❌ Filter application failed.")
            return

        self.filtered_img = result
        self.display_image(result, self.filtered_label, is_original=False)
        self.update_status(f"✅ Applied {filter_type} (color output) successfully!")

    def save_image(self):
        if self.filtered_img is None:
            self.update_status("⚠️ No filtered image to save. Apply a filter first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg"), ("All files", "*.*")]
        )
        if not file_path:
            return

        cv2.imwrite(file_path, self.filtered_img)
        self.update_status(f"💾 Saved to: {os.path.basename(file_path)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageFilterApp(root)
    root.mainloop()
