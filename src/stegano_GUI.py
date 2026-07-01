"""
Coverless Steganography GUI – with Diffie‑Hellman key exchange for HMAC.
"""
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from PIL import Image, ImageTk
import secrets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from embed import embed_secret_data
    from extract import extract_secret_data
    from dh_utils import generate_key_pair, compute_shared_secret, serialize_public_key
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class CoverlessSteganoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coverless Steganography – DH + HMAC")
        self.root.geometry("1300x850")
        self.root.configure(bg='#2c3e50')
        
        # GUI variables
        self.image_path = tk.StringVar()
        self.mapping_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # HMAC key (shared secret)
        self.hmac_key = None
        
        # DH state
        self.dh_private = None
        self.dh_public = None
        self.peer_public_bytes = None
        
        # Weight variables
        self.ll2_weight = tk.DoubleVar(value=0.5)
        self.lh2_weight = tk.DoubleVar(value=0.2)
        self.hl2_weight = tk.DoubleVar(value=0.2)
        self.hh2_weight = tk.DoubleVar(value=0.1)
        
        self.setup_style()
        self.create_widgets()
        self.setup_menu()
        
    def setup_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.bg = '#2c3e50'
        self.fg = '#ecf0f1'
        self.primary = '#3498db'
        
    def create_widgets(self):
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = tk.Frame(main, bg=self.bg)
        title.pack(fill=tk.X, pady=(0,20))
        tk.Label(title, text="🔐 Coverless Steganography – DH + HMAC",
                font=("Arial",20,"bold"), bg=self.bg, fg=self.primary).pack()
        tk.Label(title, text="Diffie‑Hellman key exchange → HMAC‑protected mapping",
                font=("Arial",11), bg=self.bg, fg=self.fg).pack()
        
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.create_dh_tab()
        self.create_embed_tab()
        self.create_extract_tab()
        self.create_help_tab()
        
        # Status
        status = tk.Frame(main, bg=self.bg, height=30)
        status.pack(fill=tk.X, pady=(10,0))
        tk.Label(status, textvariable=self.status_var, font=("Arial",10),
                bg='#34495e', fg=self.fg, anchor=tk.W, padx=10).pack(fill=tk.X)
        
    def create_scrollable_panel(self, parent):
        canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.bg)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return scrollable
        
    # ---------- DH tab ----------
    def create_dh_tab(self):
        dh_frame = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(dh_frame, text="🔑 DH Key Exchange")
        
        left = tk.Frame(dh_frame, bg=self.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        right = tk.Frame(dh_frame, bg=self.bg)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        scrollable = self.create_scrollable_panel(left)
        
        # 1. Generate
        gen_frame = ttk.LabelFrame(scrollable, text="1. Generate Key Pair", padding=10)
        gen_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(gen_frame, text="Generate DH Keys", command=self.dh_generate).pack(fill=tk.X)
        self.dh_pub_label = tk.Label(gen_frame, text="Public key not generated", wraplength=300, bg=self.bg, fg=self.fg)
        self.dh_pub_label.pack(fill=tk.X, pady=5)
        
        # 2. Export
        exp_frame = ttk.LabelFrame(scrollable, text="2. Export Public Key", padding=10)
        exp_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(exp_frame, text="Save Public Key", command=self.dh_export).pack(fill=tk.X)
        self.dh_export_label = tk.Label(exp_frame, text="No file saved", wraplength=300, bg=self.bg, fg=self.fg)
        self.dh_export_label.pack(fill=tk.X, pady=5)
        
        # 3. Import peer
        imp_frame = ttk.LabelFrame(scrollable, text="3. Import Peer's Public Key", padding=10)
        imp_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(imp_frame, text="Browse Peer Public Key", command=self.dh_import).pack(fill=tk.X)
        self.dh_peer_label = tk.Label(imp_frame, text="No file selected", wraplength=300, bg=self.bg, fg=self.fg)
        self.dh_peer_label.pack(fill=tk.X, pady=5)
        
        # 4. Compute shared secret
        comp_frame = ttk.LabelFrame(scrollable, text="4. Compute Shared Secret (HMAC Key)", padding=10)
        comp_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(comp_frame, text="Compute Shared Secret", command=self.dh_compute).pack(fill=tk.X)
        self.dh_shared_label = tk.Label(comp_frame, text="Not computed", wraplength=300, bg=self.bg, fg=self.fg)
        self.dh_shared_label.pack(fill=tk.X, pady=5)
        
        # 5. Use as HMAC key
        use_frame = ttk.LabelFrame(scrollable, text="5. Use as HMAC Key", padding=10)
        use_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(use_frame, text="→ Use Key in Embed Tab", command=self.dh_use_embed).pack(fill=tk.X, pady=2)
        ttk.Button(use_frame, text="→ Use Key in Extract Tab", command=self.dh_use_extract).pack(fill=tk.X, pady=2)
        self.dh_hmac_status = tk.Label(use_frame, text="HMAC key not set", wraplength=300, bg=self.bg, fg='lightgray')
        self.dh_hmac_status.pack(fill=tk.X, pady=5)
        
        # Right side – info
        info_frame = ttk.LabelFrame(right, text="How DH Works", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True)
        info = """
1. Both parties generate their own key pair.
2. Each exports their public key to a file.
3. They exchange these files (e.g., via email).
4. Each imports the other's public key.
5. Both compute the shared secret – it will be identical.
6. This shared secret is used as the HMAC key.
7. The HMAC key protects the mapping file integrity.
        """
        tk.Label(info_frame, text=info, font=("Courier",10), bg=self.bg, fg=self.fg, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=10)
        
    # ---------- DH callbacks ----------
    def dh_generate(self):
        try:
            self.dh_private, self.dh_public = generate_key_pair()
            self.dh_pub_label.config(text="Public key generated", fg='lightgreen')
            self.update_status("DH keys generated")
            messagebox.showinfo("Success", "Key pair generated.\nExport your public key and send it to your peer.")
        except Exception as e:
            messagebox.showerror("Error", f"Key generation failed: {e}")
            
    def dh_export(self):
        if self.dh_public is None:
            messagebox.showerror("Error", "Generate keys first.")
            return
        fn = filedialog.asksaveasfilename(defaultextension=".pub", filetypes=[("Public key","*.pub"),("All files","*.*")])
        if fn:
            pub_bytes = serialize_public_key(self.dh_public)
            with open(fn, 'wb') as f:
                f.write(pub_bytes)
            self.dh_export_label.config(text=f"Exported to {os.path.basename(fn)}")
            self.update_status(f"Public key exported to {fn}")
            
    def dh_import(self):
        fn = filedialog.askopenfilename(title="Select Peer's Public Key", filetypes=[("Public key","*.pub"),("All files","*.*")])
        if fn:
            with open(fn, 'rb') as f:
                self.peer_public_bytes = f.read()
            self.dh_peer_label.config(text=f"Loaded peer key from {os.path.basename(fn)}")
            self.update_status(f"Peer key imported from {fn}")
            
    def dh_compute(self):
        if self.dh_private is None:
            messagebox.showerror("Error", "Generate your keys first.")
            return
        if self.peer_public_bytes is None:
            messagebox.showerror("Error", "Import peer's public key first.")
            return
        try:
            shared = compute_shared_secret(self.dh_private, self.peer_public_bytes)
            self.hmac_key = shared
            self.dh_shared_label.config(text=f"Shared secret computed: {shared.hex()[:16]}...", fg='lightgreen')
            self.dh_hmac_status.config(text="HMAC key set (32 bytes)", fg='lightgreen')
            self.update_status("Shared secret computed")
            messagebox.showinfo("Success", "Shared secret computed.\nYou can now use it in Embed/Extract tabs.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compute shared secret: {e}")
            
    def dh_use_embed(self):
        if self.hmac_key is None:
            messagebox.showerror("Error", "Compute shared secret first.")
            return
        # Fill the embed key entry with hex
        self.embed_key_entry.delete(0, tk.END)
        self.embed_key_entry.insert(0, self.hmac_key.hex())
        self.key_status_label.config(text="HMAC key from DH", fg='lightgreen')
        self.update_status("HMAC key loaded into Embed tab")
        
    def dh_use_extract(self):
        if self.hmac_key is None:
            messagebox.showerror("Error", "Compute shared secret first.")
            return
        self.extract_key_entry.delete(0, tk.END)
        self.extract_key_entry.insert(0, self.hmac_key.hex())
        self.extract_key_status_label.config(text="HMAC key from DH", fg='lightgreen')
        self.update_status("HMAC key loaded into Extract tab")
        
    # ---------- Embed tab ----------
    def create_embed_tab(self):
        embed_frame = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(embed_frame, text="📤 Embed Secret")
        left_panel = tk.Frame(embed_frame, bg=self.bg)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        right_panel = tk.Frame(embed_frame, bg=self.bg)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        scrollable = self.create_scrollable_panel(left_panel)
        
        # Image
        img_frame = ttk.LabelFrame(scrollable, text="1. Cover Image", padding=10)
        img_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(img_frame, text="Browse Image", command=self.browse_image_embed).pack(fill=tk.X)
        self.img_path_label = tk.Label(img_frame, text="No image", wraplength=300, bg=self.bg, fg=self.fg)
        self.img_path_label.pack(fill=tk.X, pady=5)
        self.img_preview = tk.Label(img_frame, text="Preview", bg='#34495e', width=40, height=10)
        self.img_preview.pack(pady=5)
        
        # Secret
        secret_frame = ttk.LabelFrame(scrollable, text="2. Secret Message", padding=10)
        secret_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        self.secret_textbox = scrolledtext.ScrolledText(secret_frame, height=4, width=40,
                font=("Courier",10), bg='#34495e', fg='white', insertbackground='white')
        self.secret_textbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Weights
        w_frame = ttk.LabelFrame(scrollable, text="3. Split Weights", padding=10)
        w_frame.pack(fill=tk.X, pady=(0,10))
        winput = tk.Frame(w_frame, bg=self.bg)
        winput.pack(fill=tk.X, pady=2)
        tk.Label(winput, text="LL2:", bg=self.bg, fg=self.fg).pack(side=tk.LEFT, padx=(0,2))
        ttk.Spinbox(winput, from_=0.0, to=1.0, increment=0.05, textvariable=self.ll2_weight, width=6).pack(side=tk.LEFT, padx=(0,5))
        tk.Label(winput, text="LH2:", bg=self.bg, fg=self.fg).pack(side=tk.LEFT, padx=(0,2))
        ttk.Spinbox(winput, from_=0.0, to=1.0, increment=0.05, textvariable=self.lh2_weight, width=6).pack(side=tk.LEFT, padx=(0,5))
        tk.Label(winput, text="HL2:", bg=self.bg, fg=self.fg).pack(side=tk.LEFT, padx=(0,2))
        ttk.Spinbox(winput, from_=0.0, to=1.0, increment=0.05, textvariable=self.hl2_weight, width=6).pack(side=tk.LEFT, padx=(0,5))
        tk.Label(winput, text="HH2:", bg=self.bg, fg=self.fg).pack(side=tk.LEFT, padx=(0,2))
        ttk.Spinbox(winput, from_=0.0, to=1.0, increment=0.05, textvariable=self.hh2_weight, width=6).pack(side=tk.LEFT)
        
        # HMAC key
        key_frame = ttk.LabelFrame(scrollable, text="4. HMAC Key (from DH)", padding=10)
        key_frame.pack(fill=tk.X, pady=(0,10))
        tk.Label(key_frame, text="Key hex:", bg=self.bg, fg=self.fg).pack(anchor=tk.W)
        self.embed_key_entry = ttk.Entry(key_frame, width=50)
        self.embed_key_entry.pack(fill=tk.X, pady=2)
        btn_frame = tk.Frame(key_frame, bg=self.bg)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Load from File", command=self.load_key_embed).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Generate Random", command=self.generate_key_embed).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_key_embed).pack(side=tk.LEFT, padx=2)
        self.key_status_label = tk.Label(key_frame, text="No key loaded", bg=self.bg, fg='lightgray')
        self.key_status_label.pack(anchor=tk.W, pady=2)
        
        # Output
        out_frame = ttk.LabelFrame(scrollable, text="5. Output Directory", padding=10)
        out_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(out_frame, text="Choose Folder", command=self.browse_output).pack(fill=tk.X)
        self.output_label = tk.Label(out_frame, text="Default: Current Directory", wraplength=300, bg=self.bg, fg=self.fg)
        self.output_label.pack(fill=tk.X, pady=2)
        
        ttk.Button(scrollable, text="🚀 START EMBEDDING", command=self.start_embedding, style="Accent.TButton").pack(fill=tk.X, pady=(10,20))
        
        # Results right panel
        res_frame = ttk.LabelFrame(right_panel, text="Embedding Results", padding=10)
        res_frame.pack(fill=tk.BOTH, expand=True)
        self.results_text = scrolledtext.ScrolledText(res_frame, height=25, font=("Courier",10),
                bg='#1a1a1a', fg='#00ff00', state='disabled')
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.progress = ttk.Progressbar(res_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10,0))
        
    # ---------- Extract tab ----------
    def create_extract_tab(self):
        extract_frame = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(extract_frame, text="📥 Extract Secret")
        left_panel = tk.Frame(extract_frame, bg=self.bg)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        right_panel = tk.Frame(extract_frame, bg=self.bg)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        scrollable = self.create_scrollable_panel(left_panel)
        
        # Image
        img_frame = ttk.LabelFrame(scrollable, text="1. Received Image", padding=10)
        img_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(img_frame, text="Browse Image", command=self.browse_image_extract).pack(fill=tk.X)
        self.extract_img_label = tk.Label(img_frame, text="No image", wraplength=300, bg=self.bg, fg=self.fg)
        self.extract_img_label.pack(fill=tk.X, pady=5)
        
        # Mapping
        map_frame = ttk.LabelFrame(scrollable, text="2. Mapping File (.pkl)", padding=10)
        map_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Button(map_frame, text="Browse Mapping", command=self.browse_mapping).pack(fill=tk.X)
        self.map_path_label = tk.Label(map_frame, text="No file", wraplength=300, bg=self.bg, fg=self.fg)
        self.map_path_label.pack(fill=tk.X, pady=5)
        
        # HMAC key
        key_frame = ttk.LabelFrame(scrollable, text="3. HMAC Key (same as embedding)", padding=10)
        key_frame.pack(fill=tk.X, pady=(0,10))
        tk.Label(key_frame, text="Key hex:", bg=self.bg, fg=self.fg).pack(anchor=tk.W)
        self.extract_key_entry = ttk.Entry(key_frame, width=50)
        self.extract_key_entry.pack(fill=tk.X, pady=2)
        btn_frame = tk.Frame(key_frame, bg=self.bg)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Load from File", command=self.load_key_extract).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Generate Random", command=self.generate_key_extract).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_key_extract).pack(side=tk.LEFT, padx=2)
        self.extract_key_status_label = tk.Label(key_frame, text="No key loaded", bg=self.bg, fg='lightgray')
        self.extract_key_status_label.pack(anchor=tk.W, pady=2)
        
        ttk.Button(scrollable, text="🔎 START EXTRACTION", command=self.start_extraction, style="Accent.TButton").pack(fill=tk.X, pady=(10,20))
        
        # Results right panel
        res_frame = ttk.LabelFrame(right_panel, text="Extraction Results", padding=10)
        res_frame.pack(fill=tk.BOTH, expand=True)
        secret_frame = tk.Frame(res_frame, bg='#1a1a1a')
        secret_frame.pack(fill=tk.X, pady=(0,10))
        tk.Label(secret_frame, text="RECOVERED SECRET:", font=("Arial",12,"bold"),
                bg='#1a1a1a', fg='#3498db').pack(anchor=tk.W, padx=5, pady=(5,0))
        self.secret_display = tk.Label(secret_frame, text="", font=("Courier",14,"bold"),
                bg='#1a1a1a', fg='#2ecc71', wraplength=500, justify=tk.LEFT)
        self.secret_display.pack(fill=tk.X, padx=10, pady=10)
        details_frame = ttk.LabelFrame(res_frame, text="Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        self.extract_details = scrolledtext.ScrolledText(details_frame, height=15, font=("Courier",9),
                bg='#1a1a1a', fg='#00ff00')
        self.extract_details.pack(fill=tk.BOTH, expand=True)
        
    def create_help_tab(self):
        help_frame = tk.Frame(self.notebook, bg=self.bg)
        self.notebook.add(help_frame, text="❓ Help")
        text = """
        DH + HMAC WORKFLOW

        1. Both parties perform DH key exchange (DH tab).
        2. This produces a shared 32‑byte HMAC key.
        3. Sender embeds secret – the mapping file is signed with HMAC.
        4. Receiver extracts – the mapping file signature is verified.
        5. If the mapping file is tampered with, extraction fails.

        The image itself is NEVER modified (true coverless).
        """
        tk.Label(help_frame, text=text, font=("Courier",11), bg=self.bg, fg=self.fg, justify=tk.LEFT).pack(padx=20,pady=20)
        
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        tools = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools)
        tools.add_command(label="Clear All", command=self.clear_all)
        
    # ---------- Helpers ----------
    def _generate_random_key(self, entry, status_label):
        key = secrets.token_bytes(32)
        entry.delete(0, tk.END)
        entry.insert(0, key.hex())
        status_label.config(text="Random key generated", fg='lightgreen')
        self.update_status("Random key generated")
        
    def generate_key_embed(self):
        self._generate_random_key(self.embed_key_entry, self.key_status_label)
    def generate_key_extract(self):
        self._generate_random_key(self.extract_key_entry, self.extract_key_status_label)
        
    def load_key_embed(self):
        fn = filedialog.askopenfilename(filetypes=[("All files","*.*")])
        if fn:
            with open(fn, 'rb') as f:
                key = f.read()
            self.embed_key_entry.delete(0, tk.END)
            self.embed_key_entry.insert(0, key.hex())
            self.key_status_label.config(text=f"Key loaded ({len(key)} bytes)", fg='lightgreen')
            self.update_status(f"Key loaded from {os.path.basename(fn)}")
    def load_key_extract(self):
        fn = filedialog.askopenfilename(filetypes=[("All files","*.*")])
        if fn:
            with open(fn, 'rb') as f:
                key = f.read()
            self.extract_key_entry.delete(0, tk.END)
            self.extract_key_entry.insert(0, key.hex())
            self.extract_key_status_label.config(text=f"Key loaded ({len(key)} bytes)", fg='lightgreen')
            self.update_status(f"Key loaded from {os.path.basename(fn)}")
            
    def clear_key_embed(self):
        self.embed_key_entry.delete(0, tk.END)
        self.key_status_label.config(text="No key", fg='lightgray')
    def clear_key_extract(self):
        self.extract_key_entry.delete(0, tk.END)
        self.extract_key_status_label.config(text="No key", fg='lightgray')
        
    def browse_image_embed(self):
        fn = filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png *.bmp *.tiff")])
        if fn:
            self.image_path.set(fn)
            self.img_path_label.config(text=fn)
            self.show_preview(fn)
            self.update_status(f"Image: {os.path.basename(fn)}")
    def browse_image_extract(self):
        fn = filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png *.bmp *.tiff")])
        if fn:
            self.image_path.set(fn)
            self.extract_img_label.config(text=fn)
            self.update_status(f"Image: {os.path.basename(fn)}")
    def browse_mapping(self):
        fn = filedialog.askopenfilename(filetypes=[("Pickle","*.pkl")])
        if fn:
            self.mapping_path.set(fn)
            self.map_path_label.config(text=fn)
            self.update_status(f"Mapping: {os.path.basename(fn)}")
    def browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)
            self.output_label.config(text=d)
    def show_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((300,200))
            photo = ImageTk.PhotoImage(img)
            self.img_preview.config(image=photo, text="")
            self.img_preview.image = photo
        except: pass
        
    def update_status(self, msg):
        self.status_var.set(f"Status: {msg}")
        self.root.update_idletasks()
        
    def clear_all(self):
        self.image_path.set("")
        self.mapping_path.set("")
        self.output_dir.set("")
        self.embed_key_entry.delete(0, tk.END)
        self.extract_key_entry.delete(0, tk.END)
        self.secret_textbox.delete(1.0, tk.END)
        self.secret_display.config(text="")
        self.extract_details.delete(1.0, tk.END)
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')
        self.key_status_label.config(text="No key", fg='lightgray')
        self.extract_key_status_label.config(text="No key", fg='lightgray')
        self.update_status("Cleared")
        
    # ---------- Embed ----------
    def start_embedding(self):
        img = self.image_path.get()
        secret = self.secret_textbox.get("1.0", tk.END).strip()
        out_dir = self.output_dir.get() or os.getcwd()
        if not img or not os.path.exists(img):
            messagebox.showerror("Error", "Select cover image")
            return
        if not secret:
            messagebox.showerror("Error", "Enter secret")
            return
        try:
            w_ll2 = self.ll2_weight.get()
            w_lh2 = self.lh2_weight.get()
            w_hl2 = self.hl2_weight.get()
            w_hh2 = self.hh2_weight.get()
            if abs(w_ll2 + w_lh2 + w_hl2 + w_hh2 - 1.0) > 0.001:
                messagebox.showerror("Error", "Weights must sum to 1.0")
                return
        except:
            messagebox.showerror("Error", "Invalid weight")
            return
        key_hex = self.embed_key_entry.get().strip()
        hmac_key = None
        if key_hex:
            try:
                hmac_key = bytes.fromhex(key_hex)
                if len(hmac_key) < 16:
                    messagebox.showerror("Error", "Key must be ≥16 bytes.")
                    return
            except:
                messagebox.showerror("Error", "Invalid hex key")
                return
        self.progress.start()
        self.update_status("Embedding...")
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "=== EMBEDDING STARTED ===\n\n")
        self.results_text.config(state='disabled')
        threading.Thread(target=self.run_embedding, args=(img, secret, out_dir, w_ll2, w_lh2, w_hl2, w_hh2, hmac_key), daemon=True).start()
        
    def run_embedding(self, img, secret, out_dir, w_ll2, w_lh2, w_hl2, w_hh2, hmac_key):
        try:
            viz = os.path.join(out_dir, "mapping_visualization.png")
            mapping_dict, _, _ = embed_secret_data(
                image_path=img,
                secret_text=secret,
                output_viz_path=viz,
                ll2_weight=w_ll2,
                lh2_weight=w_lh2,
                hl2_weight=w_hl2,
                hh2_weight=w_hh2,
                hmac_key=hmac_key
            )
            self.root.after(0, self.embedding_done, mapping_dict, out_dir, hmac_key is not None)
        except Exception as e:
            self.root.after(0, self.embedding_error, str(e))
            
    def embedding_done(self, mapping_dict, out_dir, key_used):
        self.progress.stop()
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        res = f"""
✅ EMBEDDING SUCCESSFUL

Secret: {mapping_dict['secret_text']}
Hash: {mapping_dict['secret_hash']}
Weights: LL2={mapping_dict['split_weights']['LL2']:.0%}, LH2={mapping_dict['split_weights']['LH2']:.0%}, HL2={mapping_dict['split_weights']['HL2']:.0%}, HH2={mapping_dict['split_weights']['HH2']:.0%}

Files saved in: {out_dir}
- mapping_{mapping_dict['feature_hash']}.pkl
- mapping_visualization.png
"""
        if key_used:
            res += f"- mapping_{mapping_dict['feature_hash']}.sig (HMAC signature)\n"
        else:
            res += "- No signature created (HMAC key not used)\n"
        res += "\nSend the ORIGINAL image and the mapping file to the receiver."
        if key_used:
            res += "\nAlso send the .sig file. The receiver must have the same HMAC key."
        self.results_text.insert(tk.END, res)
        self.results_text.config(state='disabled')
        self.update_status("Embedding complete")
        messagebox.showinfo("Success", "Embedding complete. Check the results panel.")
        
    def embedding_error(self, err):
        self.progress.stop()
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, f"\n❌ ERROR: {err}\n")
        self.results_text.config(state='disabled')
        self.update_status(f"Embedding failed: {err}")
        messagebox.showerror("Error", f"Embedding failed:\n{err}")
        
    # ---------- Extract ----------
    def start_extraction(self):
        img = self.image_path.get()
        mapf = self.mapping_path.get()
        if not img or not os.path.exists(img):
            messagebox.showerror("Error", "Select received image")
            return
        if not mapf or not os.path.exists(mapf):
            messagebox.showerror("Error", "Select mapping file")
            return
        key_hex = self.extract_key_entry.get().strip()
        hmac_key = None
        if key_hex:
            try:
                hmac_key = bytes.fromhex(key_hex)
                if len(hmac_key) < 16:
                    messagebox.showerror("Error", "Key must be ≥16 bytes.")
                    return
            except:
                messagebox.showerror("Error", "Invalid hex key")
                return
        self.secret_display.config(text="")
        self.extract_details.delete(1.0, tk.END)
        self.update_status("Extracting...")
        try:
            secret, _, confidence, hash_ok = extract_secret_data(img, mapf, hmac_key)
            self.show_extraction_results(secret, confidence, hash_ok, hmac_key is not None)
        except Exception as e:
            self.extraction_error(str(e))
            
    def show_extraction_results(self, secret, confidence, hash_ok, key_used):
        self.secret_display.config(text=secret)
        hash_str = "✅ Verified" if hash_ok else "❌ Mismatch"
        details = f"""
=== EXTRACTION RESULTS ===
Recovered secret: {secret}
Confidence: {confidence:.2f}%
Secret hash: {hash_str}
"""
        if key_used:
            details += "HMAC verification: ✅ Mapping file is authentic\n"
        else:
            details += "HMAC verification: ⚠️ Not performed (no key)\n"
        self.extract_details.delete(1.0, tk.END)
        self.extract_details.insert(tk.END, details)
        self.update_status(f"Extraction complete, confidence {confidence:.1f}%")
        if confidence > 80 and hash_ok:
            messagebox.showinfo("Success", "Secret extracted and verified!")
        else:
            messagebox.showwarning("Warning", "Extraction completed with issues. Check details.")
            
    def extraction_error(self, err):
        self.extract_details.delete(1.0, tk.END)
        self.extract_details.insert(tk.END, f"❌ ERROR:\n{err}")
        self.update_status(f"Extraction failed: {err}")
        messagebox.showerror("Error", f"Extraction failed:\n{err}")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = CoverlessSteganoApp(root)
    app.run()
