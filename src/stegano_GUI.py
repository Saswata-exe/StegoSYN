"""
Coverless Steganography GUI Application
Main file with GUI interface for DWT-based feature mapping steganography
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# Import your existing modules
try:
    from embed import embed_secret_data
    from extract import extract_secret_data
except ImportError:
    print("Warning: embed.py and extract.py not found in current directory")
    print("Please ensure both files are in the same directory as this GUI")
    sys.exit(1)

class CoverlessSteganoApp:
    """Main GUI Application for Coverless Steganography"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Coverless Steganography System")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')
        
        # Variables
        self.image_path = tk.StringVar()
        self.secret_text = tk.StringVar()
        self.mapping_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Current images for display
        self.cover_image = None
        self.dwt_image = None
        
        # Setup GUI
        self.setup_style()
        self.create_widgets()
        self.setup_menu()
        
    def setup_style(self):
        """Configure GUI style"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Color scheme
        self.bg_color = '#2c3e50'
        self.fg_color = '#ecf0f1'
        self.primary_color = '#3498db'
        self.success_color = '#2ecc71'
        self.warning_color = '#e74c3c'
        self.accent_color = '#9b59b6'
        
    def create_widgets(self):
        """Create main GUI widgets"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(main_container, bg=self.bg_color)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="🕵️ Coverless Steganography System",
            font=("Arial", 24, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="DWT-Based Feature Mapping | Zero Image Modification",
            font=("Arial", 12),
            bg=self.bg_color,
            fg=self.fg_color
        )
        subtitle_label.pack()
        
        # Tab Notebook
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_embed_tab()
        self.create_extract_tab()
        self.create_visualize_tab()
        self.create_help_tab()
        
        # Status bar
        status_frame = tk.Frame(main_container, bg=self.bg_color, height=30)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Arial", 10),
            bg='#34495e',
            fg=self.fg_color,
            anchor=tk.W,
            padx=10
        )
        status_label.pack(fill=tk.X)
        
    def create_embed_tab(self):
        """Create embedding tab"""
        embed_frame = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(embed_frame, text="🔒 Embed Secret")
        
        # Left panel - Input controls
        left_panel = tk.Frame(embed_frame, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Section 1: Image Selection
        img_frame = ttk.LabelFrame(left_panel, text="1. Select Cover Image", padding=10)
        img_frame.pack(fill=tk.X, pady=(0, 10))
        
        img_select_btn = ttk.Button(
            img_frame,
            text="Browse Image",
            command=self.browse_image,
            style="Accent.TButton"
        )
        img_select_btn.pack(fill=tk.X)
        
        self.img_path_label = tk.Label(
            img_frame,
            text="No image selected",
            wraplength=300,
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.img_path_label.pack(fill=tk.X, pady=(5, 0))
        
        # Image preview
        self.img_preview_label = tk.Label(
            img_frame,
            text="Image Preview",
            bg='#34495e',
            width=40,
            height=10
        )
        self.img_preview_label.pack(pady=5)
        
        # Section 2: Secret Message
        secret_frame = ttk.LabelFrame(left_panel, text="2. Enter Secret Message", padding=10)
        secret_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        secret_label = tk.Label(
            secret_frame,
            text="Enter your secret message:",
            bg=self.bg_color,
            fg=self.fg_color
        )
        secret_label.pack(anchor=tk.W)
        
        self.secret_textbox = scrolledtext.ScrolledText(
            secret_frame,
            height=8,
            width=40,
            font=("Courier", 10),
            bg='#34495e',
            fg='white',
            insertbackground='white'
        )
        self.secret_textbox.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Section 3: Embed Options
        options_frame = ttk.LabelFrame(left_panel, text="3. Embedding Options", padding=10)
        options_frame.pack(fill=tk.X)
        
        # Output location
        output_label = tk.Label(
            options_frame,
            text="Output Directory:",
            bg=self.bg_color,
            fg=self.fg_color
        )
        output_label.pack(anchor=tk.W)
        
        output_btn = ttk.Button(
            options_frame,
            text="Choose Output Folder",
            command=self.browse_output,
            width=20
        )
        output_btn.pack(pady=(5, 0))
        
        self.output_label = tk.Label(
            options_frame,
            text="Default: Current Directory",
            wraplength=300,
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.output_label.pack(fill=tk.X, pady=(5, 0))
        
        # Section 4: Embed Button
        embed_btn = ttk.Button(
            left_panel,
            text="🚀 START EMBEDDING",
            command=self.start_embedding,
            style="Success.TButton"
        )
        embed_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Right panel - Results display
        right_panel = tk.Frame(embed_frame, bg=self.bg_color)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Results frame
        results_frame = ttk.LabelFrame(right_panel, text="Embedding Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            height=25,
            font=("Courier", 10),
            bg='#1a1a1a',
            fg='#00ff00',
            state='disabled'
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            results_frame,
            mode='indeterminate'
        )
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
    def create_extract_tab(self):
        """Create extraction tab"""
        extract_frame = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(extract_frame, text="🔍 Extract Secret")
        
        # Left panel - Input controls
        left_panel = tk.Frame(extract_frame, bg=self.bg_color)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Section 1: Received Image
        img_frame = ttk.LabelFrame(left_panel, text="1. Select Received Image", padding=10)
        img_frame.pack(fill=tk.X, pady=(0, 10))
        
        img_select_btn = ttk.Button(
            img_frame,
            text="Browse Image",
            command=lambda: self.browse_image(extract=True),
            style="Accent.TButton"
        )
        img_select_btn.pack(fill=tk.X)
        
        self.extract_img_label = tk.Label(
            img_frame,
            text="No image selected",
            wraplength=300,
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.extract_img_label.pack(fill=tk.X, pady=(5, 0))
        
        # Section 2: Mapping File
        map_frame = ttk.LabelFrame(left_panel, text="2. Select Mapping File (.pkl)", padding=10)
        map_frame.pack(fill=tk.X, pady=(0, 10))
        
        map_select_btn = ttk.Button(
            map_frame,
            text="Browse Mapping File",
            command=self.browse_mapping,
            style="Accent.TButton"
        )
        map_select_btn.pack(fill=tk.X)
        
        self.map_path_label = tk.Label(
            map_frame,
            text="No mapping file selected",
            wraplength=300,
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.map_path_label.pack(fill=tk.X, pady=(5, 0))
        
        # Section 3: Extract Button
        extract_btn = ttk.Button(
            left_panel,
            text="🔎 START EXTRACTION",
            command=self.start_extraction,
            style="Success.TButton"
        )
        extract_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Right panel - Results display
        right_panel = tk.Frame(extract_frame, bg=self.bg_color)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Results frame
        results_frame = ttk.LabelFrame(right_panel, text="Extraction Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Secret display frame
        secret_frame = tk.Frame(results_frame, bg='#1a1a1a')
        secret_frame.pack(fill=tk.X, pady=(0, 10))
        
        secret_title = tk.Label(
            secret_frame,
            text="RECOVERED SECRET:",
            font=("Arial", 12, "bold"),
            bg='#1a1a1a',
            fg='#3498db'
        )
        secret_title.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.secret_display = tk.Label(
            secret_frame,
            text="",
            font=("Courier", 14, "bold"),
            bg='#1a1a1a',
            fg='#2ecc71',
            wraplength=500,
            justify=tk.LEFT
        )
        self.secret_display.pack(fill=tk.X, padx=10, pady=10)
        
        # Details frame
        details_frame = ttk.LabelFrame(results_frame, text="Extraction Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        self.extract_details = scrolledtext.ScrolledText(
            details_frame,
            height=15,
            font=("Courier", 9),
            bg='#1a1a1a',
            fg='#00ff00'
        )
        self.extract_details.pack(fill=tk.BOTH, expand=True)
        
    def create_visualize_tab(self):
        """Create visualization tab"""
        visualize_frame = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(visualize_frame, text="📊 Visualization")
        
        # Visualization controls
        control_frame = tk.Frame(visualize_frame, bg=self.bg_color)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        load_viz_btn = ttk.Button(
            control_frame,
            text="Load Visualization Image",
            command=self.load_visualization,
            style="Accent.TButton"
        )
        load_viz_btn.pack(side=tk.LEFT, padx=5)
        
        self.viz_path_label = tk.Label(
            control_frame,
            text="No visualization loaded",
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.viz_path_label.pack(side=tk.LEFT, padx=10)
        
        # Image display area
        self.viz_canvas_frame = tk.Frame(visualize_frame, bg='#34495e')
        self.viz_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add placeholder
        placeholder = tk.Label(
            self.viz_canvas_frame,
            text="Visualization will appear here\n\n"
                 "After embedding, a visualization image is created\n"
                 "showing the DWT decomposition and feature mapping",
            font=("Arial", 12),
            bg='#34495e',
            fg=self.fg_color
        )
        placeholder.pack(expand=True)
        
    def create_help_tab(self):
        """Create help/info tab"""
        help_frame = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(help_frame, text="❓ Help & Info")
        
        # Create notebook for help sections
        help_notebook = ttk.Notebook(help_frame)
        help_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # About section
        about_frame = tk.Frame(help_notebook, bg=self.bg_color)
        help_notebook.add(about_frame, text="About")
        
        about_text = """
        COVERLESS STEGANOGRAPHY SYSTEM
        
        Version: 1.0
        Developed for: Academic Project
        Technology: Python, OpenCV, PyWavelets
        
        📌 KEY FEATURES:
        • Zero modification to cover image
        • DWT-based robust feature extraction
        • Statistical feature mapping
        • Dual-channel transmission security
        • High resistance to steganalysis
        
        🔒 HOW IT WORKS:
        1. Sender extracts features from image using DWT
        2. Creates mapping between features and secret
        3. Sends original image + mapping file separately
        4. Receiver extracts same features
        5. Matches features to recover secret
        
        ⚠️ IMPORTANT:
        • Original image is NEVER modified
        • No data embedded in pixels
        • No statistical traces left
        """
        
        about_label = tk.Label(
            about_frame,
            text=about_text,
            font=("Courier", 10),
            bg=self.bg_color,
            fg=self.fg_color,
            justify=tk.LEFT
        )
        about_label.pack(anchor=tk.W, padx=20, pady=20)
        
        # Instructions section
        instr_frame = tk.Frame(help_notebook, bg=self.bg_color)
        help_notebook.add(instr_frame, text="Instructions")
        
        instr_text = """
        🚀 EMBEDDING PROCESS:
        
        1. Go to 'Embed Secret' tab
        2. Select a cover image (JPG/PNG)
        3. Enter your secret message
        4. Click 'START EMBEDDING'
        5. System will:
           - Extract DWT features
           - Create mapping file (.pkl)
           - Generate visualization
        6. Send both files to receiver:
           - Original image (unchanged)
           - Mapping file (.pkl)
        
        🔍 EXTRACTION PROCESS:
        
        1. Go to 'Extract Secret' tab
        2. Select received image
        3. Select mapping file (.pkl)
        4. Click 'START EXTRACTION'
        5. System will:
           - Extract same DWT features
           - Compare with mapping
           - Recover secret message
           - Show match confidence
        
        📊 VISUALIZATION:
        
        • Shows DWT decomposition
        • Displays extracted features
        • Illustrates mapping process
        • Available after embedding
        
        ⚙️ TECHNICAL DETAILS:
        
        • Wavelet: Haar (2-level)
        • Features: Mean, Variance, Energy, Entropy
        • Region: LL2 (most stable)
        • Match Score: 0-100% confidence
        """
        
        instr_label = tk.Label(
            instr_frame,
            text=instr_text,
            font=("Courier", 10),
            bg=self.bg_color,
            fg=self.fg_color,
            justify=tk.LEFT
        )
        instr_label.pack(anchor=tk.W, padx=20, pady=20)
        
    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Clear All", command=self.clear_all)
        tools_menu.add_command(label="Test Embedding", command=self.test_embedding)
        tools_menu.add_command(label="Test Extraction", command=self.test_extraction)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_guide)
        help_menu.add_command(label="About", command=self.show_about)
        
    # ========== GUI FUNCTIONS ==========
    
    def browse_image(self, extract=False):
        """Browse for image file"""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=filetypes
        )
        
        if filename:
            if extract:
                self.extract_img_label.config(text=filename)
                self.image_path.set(filename)
            else:
                self.img_path_label.config(text=filename)
                self.image_path.set(filename)
                self.show_image_preview(filename)
                
            self.update_status(f"Selected image: {os.path.basename(filename)}")
            
    def browse_mapping(self):
        """Browse for mapping file"""
        filename = filedialog.askopenfilename(
            title="Select Mapping File",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        
        if filename:
            self.map_path_label.config(text=filename)
            self.mapping_path.set(filename)
            self.update_status(f"Selected mapping file: {os.path.basename(filename)}")
            
    def browse_output(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        
        if directory:
            self.output_label.config(text=directory)
            self.output_path.set(directory)
            self.update_status(f"Output directory: {directory}")
            
    def show_image_preview(self, image_path):
        """Display image preview"""
        try:
            img = Image.open(image_path)
            # Resize for preview
            img.thumbnail((300, 200))
            photo = ImageTk.PhotoImage(img)
            
            self.img_preview_label.config(image=photo, text="")
            self.img_preview_label.image = photo
            self.cover_image = img
        except Exception as e:
            self.img_preview_label.config(text=f"Preview error: {str(e)}")
            
    def load_visualization(self):
        """Load and display visualization image"""
        filename = filedialog.askopenfilename(
            title="Select Visualization Image",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if filename:
            self.viz_path_label.config(text=os.path.basename(filename))
            
            # Clear previous content
            for widget in self.viz_canvas_frame.winfo_children():
                widget.destroy()
                
            # Load and display image
            try:
                img = Image.open(filename)
                
                # Calculate display size
                canvas_width = self.viz_canvas_frame.winfo_width()
                canvas_height = self.viz_canvas_frame.winfo_height()
                
                if canvas_width < 100 or canvas_height < 100:
                    # Default size if not yet rendered
                    img.thumbnail((800, 600))
                else:
                    img.thumbnail((canvas_width - 20, canvas_height - 20))
                
                photo = ImageTk.PhotoImage(img)
                
                img_label = tk.Label(
                    self.viz_canvas_frame,
                    image=photo,
                    bg='#34495e'
                )
                img_label.image = photo
                img_label.pack(pady=10)
                
                self.update_status(f"Loaded visualization: {os.path.basename(filename)}")
            except Exception as e:
                error_label = tk.Label(
                    self.viz_canvas_frame,
                    text=f"Error loading image: {str(e)}",
                    fg=self.warning_color,
                    bg='#34495e'
                )
                error_label.pack(expand=True)
                
    def start_embedding(self):
        """Start embedding process in separate thread"""
        # Get inputs
        image_path = self.image_path.get()
        secret_text = self.secret_textbox.get("1.0", tk.END).strip()
        
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", "Please select a valid image file")
            return
            
        if not secret_text:
            messagebox.showerror("Error", "Please enter a secret message")
            return
            
        # Get output directory
        output_dir = self.output_path.get()
        if not output_dir:
            output_dir = os.path.dirname(image_path)
            
        # Disable button and start progress
        self.progress.start()
        self.update_status("Embedding in progress...")
        
        # Clear results
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "=== EMBEDDING PROCESS STARTED ===\n\n")
        self.results_text.config(state='disabled')
        
        # Run in thread to avoid GUI freeze
        thread = threading.Thread(
            target=self.run_embedding,
            args=(image_path, secret_text, output_dir)
        )
        thread.daemon = True
        thread.start()
        
    def run_embedding(self, image_path, secret_text, output_dir):
        """Run embedding process"""
        try:
            # Run embedding
            output_viz = os.path.join(output_dir, "mapping_visualization.png")
            
            mapping_dict, features, original_image = embed_secret_data(
                image_path=image_path,
                secret_text=secret_text,
                output_viz_path=output_viz
            )
            
            # Update GUI with results
            self.root.after(0, self.show_embedding_results, mapping_dict, output_viz)
            
        except Exception as e:
            self.root.after(0, self.embedding_error, str(e))
            
    def show_embedding_results(self, mapping_dict, viz_path):
        """Show embedding results in GUI"""
        self.progress.stop()
        
        # Update results text
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        
        results = f"""
=== EMBEDDING COMPLETE ===

✅ SUCCESS: Secret message embedded successfully

📄 DETAILS:
• Cover Image: {os.path.basename(mapping_dict['image_path'])}
• Secret Length: {len(mapping_dict['secret_text'])} characters
• Selected Region: {mapping_dict['selected_region']}
• Feature Hash: {mapping_dict['feature_hash']}
• Mapping File: mapping_{mapping_dict['feature_hash']}.pkl

🔧 FEATURES EXTRACTED (LL2):
• Mean: {mapping_dict['features']['mean']:.6f}
• Variance: {mapping_dict['features']['variance']:.8f}
• Energy: {mapping_dict['features']['energy']:.4f}
• Entropy: {mapping_dict['features']['entropy']:.4f}

📁 OUTPUT FILES:
1. Original Image: {mapping_dict['image_path']}
   (Unchanged - send this to receiver)

2. Mapping File: mapping_{mapping_dict['feature_hash']}.pkl
   (Contains secret mapping - send securely)

3. Visualization: {viz_path}
   (For reference - shows DWT decomposition)

🚀 NEXT STEPS:
1. Send the original image to receiver
2. Send the mapping file securely
3. Receiver uses both files to extract secret

=== END OF EMBEDDING ===
        """
        
        self.results_text.insert(tk.END, results)
        self.results_text.config(state='disabled')
        
        # Update status
        self.update_status("Embedding completed successfully")
        
        # Show success message
        messagebox.showinfo("Success", "Secret embedded successfully!\n\n"
                            "Check the 'Embedding Results' section for details.")
                            
    def embedding_error(self, error_msg):
        """Handle embedding error"""
        self.progress.stop()
        
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, f"\n❌ ERROR: {error_msg}\n")
        self.results_text.config(state='disabled')
        
        self.update_status(f"Embedding failed: {error_msg}")
        messagebox.showerror("Embedding Error", f"Error during embedding:\n\n{error_msg}")
        
    def start_extraction(self):
        """Start extraction process"""
        image_path = self.image_path.get()
        mapping_path = self.mapping_path.get()
        
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", "Please select a valid image file")
            return
            
        if not mapping_path or not os.path.exists(mapping_path):
            messagebox.showerror("Error", "Please select a valid mapping file")
            return
            
        # Clear previous results
        self.secret_display.config(text="")
        self.extract_details.delete(1.0, tk.END)
        
        # Update status
        self.update_status("Extraction in progress...")
        
        # Run extraction
        try:
            secret, features, score = extract_secret_data(image_path, mapping_path)
            
            # Update GUI
            self.show_extraction_results(secret, score)
            
        except Exception as e:
            self.extraction_error(str(e))
            
    def show_extraction_results(self, secret, score):
        """Show extraction results in GUI"""
        # Update secret display
        self.secret_display.config(text=secret)
        
        # Update details
        details = f"""
=== EXTRACTION RESULTS ===

📨 RECOVERED SECRET:
{secret}

📊 MATCH CONFIDENCE:
• Score: {score:.2f}%
• Confidence: {'HIGH' if score > 80 else 'MEDIUM' if score > 60 else 'LOW'}
• Status: {'✅ SUCCESS' if score > 60 else '⚠️ PARTIAL SUCCESS'}

🔍 INTERPRETATION:
• >95%: Excellent match (identical image)
• 80-95%: Good match (minor processing)
• 60-80%: Fair match (noticeable changes)
• <60%: Poor match (possible wrong image)

💡 RECOMMENDATIONS:
{'- Image appears identical to original' if score > 95 else 
 '- Image has minor modifications' if score > 80 else 
 '- Image may have been processed' if score > 60 else 
 '- Check if correct image/mapping pair'}

=== EXTRACTION COMPLETE ===
        """
        
        self.extract_details.delete(1.0, tk.END)
        self.extract_details.insert(tk.END, details)
        
        self.update_status(f"Extraction completed with {score:.2f}% match")
        
        # Show message
        if score > 80:
            messagebox.showinfo("Extraction Success", 
                              f"Secret extracted successfully!\n\n"
                              f"Match confidence: {score:.2f}%")
        else:
            messagebox.showwarning("Low Confidence", 
                                 f"Secret extracted with low confidence\n\n"
                                 f"Match score: {score:.2f}%\n"
                                 f"Image may have been modified.")
                                 
    def extraction_error(self, error_msg):
        """Handle extraction error"""
        self.extract_details.delete(1.0, tk.END)
        self.extract_details.insert(tk.END, f"❌ EXTRACTION ERROR:\n{error_msg}")
        
        self.update_status(f"Extraction failed: {error_msg}")
        messagebox.showerror("Extraction Error", f"Error during extraction:\n\n{error_msg}")
        
    def clear_all(self):
        """Clear all inputs and results"""
        # Clear embedding tab
        self.img_path_label.config(text="No image selected")
        self.secret_textbox.delete(1.0, tk.END)
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')
        
        # Clear extraction tab
        self.extract_img_label.config(text="No image selected")
        self.map_path_label.config(text="No mapping file selected")
        self.secret_display.config(text="")
        self.extract_details.delete(1.0, tk.END)
        
        # Clear visualization
        self.viz_path_label.config(text="No visualization loaded")
        for widget in self.viz_canvas_frame.winfo_children():
            widget.destroy()
            
        # Reset variables
        self.image_path.set("")
        self.mapping_path.set("")
        self.output_path.set("")
        
        self.update_status("All inputs cleared")
        
    def test_embedding(self):
        """Run test embedding with sample data"""
        # Create test image if doesn't exist
        test_image = "test_image.jpg"
        if not os.path.exists(test_image):
            self.create_test_image()
            
        # Set test values
        self.img_path_label.config(text=test_image)
        self.image_path.set(test_image)
        self.secret_textbox.delete(1.0, tk.END)
        self.secret_textbox.insert(tk.END, "This is a test secret message for demonstration.")
        
        self.update_status("Test mode activated")
        messagebox.showinfo("Test Mode", 
                          "Test values loaded.\n\n"
                          "Click 'START EMBEDDING' to run test.")
                          
    def test_extraction(self):
        """Run test extraction"""
        messagebox.showinfo("Test Extraction", 
                          "For testing extraction:\n\n"
                          "1. First run a test embedding\n"
                          "2. Use the generated mapping file\n"
                          "3. Select the same image for extraction")
                          
    def create_test_image(self):
        """Create a test image for demonstration"""
        import numpy as np
        from PIL import Image
        
        # Create a simple gradient image
        width, height = 400, 300
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (x + y) / (width + height))
                image[y, x] = [r, g, b]
                
        img = Image.fromarray(image)
        img.save("test_image.jpg")
        
        self.update_status("Created test image: test_image.jpg")
        
    def show_guide(self):
        """Show user guide"""
        guide_text = """
        USER GUIDE - COVERLESS STEGANOGRAPHY
        
        1. EMBEDDING:
           • Select an image (JPG/PNG)
           • Enter secret message
           • Click START EMBEDDING
           • Send original image + .pkl file
        
        2. EXTRACTION:
           • Select received image
           • Select .pkl mapping file
           • Click START EXTRACTION
           • View recovered secret
        
        3. KEY POINTS:
           • Original image NEVER modified
           • Mapping file contains secret
           • Send files separately for security
           • Match score indicates confidence
        
        4. TROUBLESHOOTING:
           • Low match score: Wrong image or mapping
           • Extraction error: Check file paths
           • No preview: Image may be corrupted
        """
        
        messagebox.showinfo("User Guide", guide_text)
        
    def show_about(self):
        """Show about dialog"""
        about_text = """
        COVERLESS STEGANOGRAPHY SYSTEM
        
        Version 1.0
        Academic Project
        
        Features:
        • Zero image modification
        • DWT-based feature extraction
        • Statistical feature mapping
        • Dual-channel security
        • GUI interface
        
        Technologies:
        • Python 3.x
        • OpenCV for image processing
        • PyWavelets for DWT
        • Tkinter for GUI
        
        Developed for secure communication
        without altering cover media.
        """
        
        messagebox.showinfo("About", about_text)
        
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(f"Status: {message}")
        self.root.update_idletasks()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = CoverlessSteganoApp(root)
    app.run()