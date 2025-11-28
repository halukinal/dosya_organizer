import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import threading
from pathlib import Path
import io

# --- MODÜLLERİ İÇE AKTAR ---
# Eğer dosyalar aynı klasördeyse bunları import edebiliriz.
# Hata almamak için try-except bloğu kullanıyoruz.
try:
    import disk_envanter_guncelleyici
    import main_optimizer
    import bayi_paketi_hazirlayici
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    MISSING_MODULE = str(e)

class TextRedirector(io.StringIO):
    """Konsol çıktılarını (print) arayüzdeki Text kutusuna yönlendirir."""
    def __init__(self, widget):
        self.widget = widget
        
    def write(self, str):
        self.widget.after(0, self._append_text, str)
        
    def _append_text(self, str):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')
        
    def flush(self):
        pass

class MedyaYonetimApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medya Asistanı Pro - Haluk İnal")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # Stil Ayarları
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#333")

        if not MODULES_AVAILABLE:
            messagebox.showerror("Eksik Dosyalar", f"Gerekli modüller bulunamadı:\n{MISSING_MODULE}\n\nLütfen diğer python dosyalarının (disk_envanter_guncelleyici.py vb.) bu dosya ile aynı klasörde olduğundan emin olun.")

        self.create_widgets()

    def create_widgets(self):
        # --- BAŞLIK ---
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(header_frame, text="MEDYA ENVANTER & STOK YÖNETİMİ", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header_frame, text="v1.0", style="TLabel").pack(side=tk.RIGHT, anchor="s")

        # --- SEKMELER (TABS) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=20, pady=5)

        # Sekme 1: Envanter Güncelleme
        self.tab_envanter = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_envanter, text=" 📂 Disk Envanteri ")
        self.setup_envanter_tab()

        # Sekme 2: Optimizasyon
        self.tab_optimize = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optimize, text=" 🚀 Stok Optimizasyonu ")
        self.setup_optimize_tab()

        # Sekme 3: Bayi Paketi
        self.tab_bayi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bayi, text=" 📦 Bayi Paketi Hazırla ")
        self.setup_bayi_tab()

        # --- KONSOL LOG ALANI ---
        log_frame = ttk.LabelFrame(self.root, text="İşlem Logları", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled', font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Print çıktılarını yönlendir
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)

    # =========================================================================
    # SEKME 1: ENVANTER GÜNCELLEME
    # =========================================================================
    def setup_envanter_tab(self):
        frame = ttk.Frame(self.tab_envanter, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Bu modül, seçilen klasörü tarar ve 'Guncel_Disk_Envanteri.xlsx' dosyasını oluşturur.", wraplength=800).pack(anchor="w", pady=(0, 20))

        # Klasör Seçimi
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(select_frame, text="Taranacak Ana Klasör:").pack(anchor="w")
        self.path_envanter = tk.StringVar(value="/Volumes/KIOXIA/Yeni_Ürün_v2")
        entry = ttk.Entry(select_frame, textvariable=self.path_envanter)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(select_frame, text="Klasör Seç", command=lambda: self.select_folder(self.path_envanter)).pack(side=tk.RIGHT)

        # Başlat Butonu
        btn_start = ttk.Button(frame, text="▶ TARAMAYI BAŞLAT", command=self.run_envanter)
        btn_start.pack(pady=20, ipadx=20, ipady=5)

    def run_envanter(self):
        target_path = self.path_envanter.get()
        if not target_path: return
        
        def task():
            print(f"\n--- ENVANTER GÜNCELLEME BAŞLATILIYOR ---\nHedef: {target_path}")
            # Modül değişkenini güncelle ve çalıştır
            try:
                disk_envanter_guncelleyici.HEDEF_KLASOR = Path(target_path)
                app = disk_envanter_guncelleyici.EnvanterTarayici(target_path)
                app.tara_ve_raporla()
            except Exception as e:
                print(f"HATA: {e}")

        threading.Thread(target=task, daemon=True).start()

    # =========================================================================
    # SEKME 2: STOK OPTİMİZASYONU
    # =========================================================================
    def setup_optimize_tab(self):
        frame = ttk.Frame(self.tab_optimize, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Mükerrer dosyaları temizler, 4MB altına sıkıştırır ve düzenli klasör yapısına taşır.", wraplength=800).pack(anchor="w", pady=(0, 20))

        # Analiz Dosyası Seçimi
        f1 = ttk.Frame(frame); f1.pack(fill=tk.X, pady=5)
        ttk.Label(f1, text="Analiz Excel Dosyası (Stok_Analiz_V4...):").pack(anchor="w")
        self.path_opt_excel = tk.StringVar(value="Stok_Analiz_V4_Final.xlsx")
        ttk.Entry(f1, textvariable=self.path_opt_excel).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(f1, text="Dosya Seç", command=lambda: self.select_file(self.path_opt_excel)).pack(side=tk.RIGHT)

        # Hedef Klasör
        f2 = ttk.Frame(frame); f2.pack(fill=tk.X, pady=5)
        ttk.Label(f2, text="Hedef Klasör (Nereye Oluşturulsun?):").pack(anchor="w")
        self.path_opt_target = tk.StringVar(value="/Volumes/KIOXIA/Yeni_Ürün_v2")
        ttk.Entry(f2, textvariable=self.path_opt_target).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(f2, text="Klasör Seç", command=lambda: self.select_folder(self.path_opt_target)).pack(side=tk.RIGHT)

        # Ayarlar
        self.opt_dry_run = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Simülasyon Modu (DRY_RUN) - İşaretliyse dosya kopyalamaz, sadece dener.", variable=self.opt_dry_run).pack(anchor="w", pady=10)

        # Başlat
        ttk.Button(frame, text="▶ OPTİMİZASYONU BAŞLAT", command=self.run_optimize).pack(pady=20, ipadx=20, ipady=5)

    def run_optimize(self):
        excel = self.path_opt_excel.get()
        target = self.path_opt_target.get()
        is_dry = self.opt_dry_run.get()
        
        def task():
            print(f"\n--- OPTİMİZASYON BAŞLATILIYOR ---\nExcel: {excel}\nHedef: {target}\nMod: {'Simülasyon' if is_dry else 'Gerçek İşlem'}")
            try:
                # Modül ayarlarını güncelle
                main_optimizer.ANALIZ_DOSYASI = excel
                main_optimizer.HEDEF_ANA_KLASOR = Path(target)
                main_optimizer.DRY_RUN = is_dry
                
                app = main_optimizer.StokOptimizeEdici(excel)
                app.baslat()
            except Exception as e:
                print(f"HATA: {e}")

        threading.Thread(target=task, daemon=True).start()

    # =========================================================================
    # SEKME 3: BAYİ PAKETİ HAZIRLA
    # =========================================================================
    def setup_bayi_tab(self):
        frame = ttk.Frame(self.tab_bayi, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Müşterinin ürün gamı listesine göre bayilere özel klasör hazırlar.", wraplength=800).pack(anchor="w", pady=(0, 20))

        # Envanter Dosyası
        f1 = ttk.Frame(frame); f1.pack(fill=tk.X, pady=5)
        ttk.Label(f1, text="Güncel Envanter Dosyası (Guncel_Disk_Envanteri.xlsx):").pack(anchor="w")
        self.path_bayi_env = tk.StringVar(value="Guncel_Disk_Envanteri.xlsx")
        ttk.Entry(f1, textvariable=self.path_bayi_env).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(f1, text="Dosya Seç", command=lambda: self.select_file(self.path_bayi_env)).pack(side=tk.RIGHT)

        # Ürün Gamı Dosyası
        f2 = ttk.Frame(frame); f2.pack(fill=tk.X, pady=5)
        ttk.Label(f2, text="Müşteri Talep Listesi (Ürün Gamı.xlsx):").pack(anchor="w")
        self.path_bayi_talep = tk.StringVar(value="25.11.27 Ürün Gamı.xlsx")
        ttk.Entry(f2, textvariable=self.path_bayi_talep).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(f2, text="Dosya Seç", command=lambda: self.select_file(self.path_bayi_talep)).pack(side=tk.RIGHT)

        # Hedef Klasör
        f3 = ttk.Frame(frame); f3.pack(fill=tk.X, pady=5)
        ttk.Label(f3, text="Paket Nereye Kaydedilsin?:").pack(anchor="w")
        self.path_bayi_target = tk.StringVar(value="/Volumes/KIOXIA/Bayi_Paketi_2025")
        ttk.Entry(f3, textvariable=self.path_bayi_target).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(f3, text="Klasör Seç", command=lambda: self.select_folder(self.path_bayi_target)).pack(side=tk.RIGHT)

        # Ayarlar
        self.bayi_dry_run = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Simülasyon Modu (DRY_RUN)", variable=self.bayi_dry_run).pack(anchor="w", pady=10)

        # Başlat
        ttk.Button(frame, text="▶ PAKETİ HAZIRLA", command=self.run_bayi).pack(pady=20, ipadx=20, ipady=5)

    def run_bayi(self):
        env = self.path_bayi_env.get()
        talep = self.path_bayi_talep.get()
        target = self.path_bayi_target.get()
        is_dry = self.bayi_dry_run.get()

        def task():
            print(f"\n--- BAYİ PAKETİ HAZIRLANIYOR ---\nEnvanter: {env}\nTalep: {talep}\nMod: {'Simülasyon' if is_dry else 'Gerçek İşlem'}")
            try:
                # Modül ayarlarını güncelle
                bayi_paketi_hazirlayici.ENVANTER_DOSYASI = Path(env)
                bayi_paketi_hazirlayici.URUN_GAMI_DOSYASI = Path(talep)
                bayi_paketi_hazirlayici.HEDEF_KLASOR = Path(target)
                bayi_paketi_hazirlayici.DRY_RUN = is_dry
                
                app = bayi_paketi_hazirlayici.BayiPaketiOlusturucu()
                if app.verileri_yukle():
                    app.eslestir_ve_islem_yap()
            except Exception as e:
                print(f"HATA: {e}")

        threading.Thread(target=task, daemon=True).start()

    # =========================================================================
    # YARDIMCILAR
    # =========================================================================
    def select_folder(self, string_var):
        folder = filedialog.askdirectory()
        if folder:
            string_var.set(folder)

    def select_file(self, string_var):
        file = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx;*.xls")])
        if file:
            string_var.set(file)

if __name__ == "__main__":
    root = tk.Tk()
    app = MedyaYonetimApp(root)
    root.mainloop()