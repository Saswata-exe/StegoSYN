import tkinter as tk
from tkinter import filedialog, messagebox
import difflib
import hashlib
import os
import threading

class FileComparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text File Comparator (Optimized)")
        self.root.geometry("600x300")
        self.root.resizable(False, False)

        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.compare_thread = None

        self.create_widgets()

    def create_widgets(self):
        # File 1
        tk.Label(self.root, text="File 1:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        tk.Entry(self.root, textvariable=self.file1_path, width=50).grid(row=0, column=1, padx=5, pady=10)
        tk.Button(self.root, text="Browse...", command=lambda: self.browse_file(1)).grid(row=0, column=2, padx=5, pady=10)

        # File 2
        tk.Label(self.root, text="File 2:").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        tk.Entry(self.root, textvariable=self.file2_path, width=50).grid(row=1, column=1, padx=5, pady=10)
        tk.Button(self.root, text="Browse...", command=lambda: self.browse_file(2)).grid(row=1, column=2, padx=5, pady=10)

        # Compare button
        self.compare_btn = tk.Button(self.root, text="Compare", command=self.start_comparison,
                                      bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.compare_btn.grid(row=2, column=1, pady=15)

        # Status / progress label
        self.status_label = tk.Label(self.root, text="", font=("Arial", 10), fg="blue")
        self.status_label.grid(row=3, column=0, columnspan=3, pady=5)

        # Result display
        self.result_label = tk.Label(self.root, text="", font=("Arial", 12, "bold"))
        self.result_label.grid(row=4, column=0, columnspan=3, pady=5)

        self.detail_label = tk.Label(self.root, text="", font=("Arial", 10), fg="gray")
        self.detail_label.grid(row=5, column=0, columnspan=3)

    def browse_file(self, file_num):
        file_path = filedialog.askopenfilename(
            title=f"Select File {file_num}",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            if file_num == 1:
                self.file1_path.set(file_path)
            else:
                self.file2_path.set(file_path)

    def get_file_hash(self, file_path):
        """Compute MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def compare_files_async(self):
        """Perform comparison in a separate thread."""
        path1 = self.file1_path.get().strip()
        path2 = self.file2_path.get().strip()

        if not path1 or not path2:
            self.root.after(0, lambda: messagebox.showwarning("Incomplete", "Please select both files."))
            self.reset_ui()
            return

        # Step 1: Quick file size check
        size1 = os.path.getsize(path1)
        size2 = os.path.getsize(path2)

        if size1 == size2:
            # Step 2: Compare hashes for exact match
            self.update_status("Hashing files...")
            hash1 = self.get_file_hash(path1)
            hash2 = self.get_file_hash(path2)
            if hash1 == hash2:
                self.root.after(0, lambda: self.show_result(100.0, True))
                self.reset_ui()
                return

        # Step 3: Not identical; compute similarity using line-based quick_ratio
        self.update_status("Reading and comparing files (this may take a moment)...")
        try:
            with open(path1, 'r', encoding='utf-8') as f1, open(path2, 'r', encoding='utf-8') as f2:
                lines1 = f1.readlines()
                lines2 = f2.readlines()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Could not read files:\n{str(e)}"))
            self.reset_ui()
            return

        if not lines1 and not lines2:
            similarity = 100.0
        elif not lines1 or not lines2:
            similarity = 0.0
        else:
            # Use quick_ratio on line sequences – much faster for large files
            matcher = difflib.SequenceMatcher(None, lines1, lines2)
            similarity = matcher.quick_ratio() * 100

        # Check if exactly identical (character-by-character) – only possible if sizes and hashes matched earlier,
        # but we already returned, so this is for completeness.
        exact = False
        if similarity == 100.0:
            # Re-read as a single string to confirm exact match (but this is rare if hashes didn't match)
            with open(path1, 'r', encoding='utf-8') as f1, open(path2, 'r', encoding='utf-8') as f2:
                content1 = f1.read()
                content2 = f2.read()
            exact = (content1 == content2)

        self.root.after(0, lambda: self.show_result(similarity, exact))

    def show_result(self, similarity, exact):
        self.result_label.config(text=f"Similarity: {similarity:.2f}%")
        if exact:
            detail = "✓ The files are exactly identical (character-by-character)."
        elif similarity == 100.0:
            # Should not happen if not exact, but keep fallback
            detail = "The files are 100% similar but not exactly identical (check for hidden characters)."
        else:
            detail = "✗ The files are not completely identical."
        self.detail_label.config(text=detail)
        self.status_label.config(text="Done")

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def reset_ui(self):
        self.compare_btn.config(state=tk.NORMAL)
        self.root.config(cursor="")

    def start_comparison(self):
        if self.compare_thread and self.compare_thread.is_alive():
            return
        self.compare_btn.config(state=tk.DISABLED)
        self.result_label.config(text="")
        self.detail_label.config(text="")
        self.status_label.config(text="Starting comparison...")
        self.root.config(cursor="watch")
        self.compare_thread = threading.Thread(target=self.compare_files_async)
        self.compare_thread.daemon = True
        self.compare_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileComparatorApp(root)
    root.mainloop()
