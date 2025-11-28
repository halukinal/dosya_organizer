import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import threading
from pathlib import Path
import io
import webbrowser
import os
import A_B_kiyasla

# --- MODÜLLERİ GÜVENLİ İÇE AKTARMA ---
MODULE_STATUS = {}

def safe_import(module_name, key):
    try:
        mod = __import__(module_name)
        MODULE_STATUS[key] = True
        return mod
    except ImportError:
        MODULE_STATUS[key] = False
        return None

disk_envanter_guncelleyici = safe_import('disk_envanter_guncelleyici', 'envanter')
main_optimizer = safe_import('main_optimizer', 'optimizer')
bayi_paketi_hazirlayici = safe_import('bayi_paketi_hazirlayici', 'bayi')
ai_envanter_analizcisi = safe_import('ai_envanter_analizcisi', 'ai') 
kiyasla = safe_import('A_B_kiyasla', 'kiyasla')

class TextRedirector(io.StringIO):
    """Konsol çıktılarını arayüze yönlendirir."""
    def __init__(self, widget):
        self.widget = widget
        
    def write(self, str):
        self.widget.after(0, self._append_text, str)
        
    def _append_text(self, str):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')
        
    def flush(self): pass

class MedyaYonetimApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medya Asistanı Pro v4.1 (Llama AI) - Haluk İnal")
        self.root.geometry("1150x850")
        
        # Tema ve Renkler
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        bg_color = "#f0f2f5"
        self.root.configure(bg=bg_color)
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, font=("Segoe UI", 10), foreground="#333")
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#2c3e50")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("Success.TLabel", font=("Segoe UI", 10, "bold"), foreground="#27ae60", background=bg_color)
        self.style.configure("Warning.TLabel", font=("Segoe UI", 10, "bold"), foreground="#c0392b", background=bg_color)
        
        self.create_widgets()
        self.check_modules()

    def check_modules(self):
        missing = [k for k, v in MODULE_STATUS.items() if not v]
        if missing:
            msg = "Eksik Modüller:\n" + "\n".join([f"- {m}.py" for m in missing])
            messagebox.showwarning("Eksik Dosya", msg)

    def create_widgets(self):
        # BAŞLIK
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=30, pady=20)
        ttk.Label(header, text="MEDYA ENVANTER & STOK YÖNETİMİ", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="v4.1 Final", font=("Segoe UI", 10, "italic")).pack(side=tk.RIGHT, anchor="s")

        # --- Eksik Ürün Analiz Butonu ---
        self.btn_kiyasla = tk.Button(
            self.main_frame, 
            text="Eksik Ürünleri Analiz Et (A/B)", 
            bg="#FF9800", fg="white", # Turuncu renk, dikkat çeksin
            font=("Arial", 11, "bold"),
            command=self.eksik_urun_analizi_yap
        )
        self.btn_kiyasla.pack(pady=10, fill="x") # Mevcut layout'una göre grid veya pack kullan
        
        # SEKMELER
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=20, pady=5)

        # Sekme 1: Envanter
        self.tab_envanter = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_envanter, text=" 📂 Disk Envanteri ")
        self.setup_envanter_tab()

        # Sekme 2: Optimizasyon
        self.tab_optimize = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optimize, text=" 🚀 Stok Optimizasyonu ")
        self.setup_optimize_tab()

        # Sekme 3: Bayi Paketi
        self.tab_bayi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bayi, text=" 📦 Bayi Paketi ")
        self.setup_bayi_tab()
        
        # Sekme 4: AI Özet Rapor
        self.tab_ai = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ai, text=" 🤖 AI Özet Rapor (Llama) ")
        self.setup_ai_tab()

        # LOG EKRANI
        log_frame = ttk.LabelFrame(self.root, text="Sistem Logları", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled', bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)

    # --- SEKME 1: ENVANTER ---
    def setup_envanter_tab(self):
        frame = ttk.Frame(self.tab_envanter, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Diskteki karmaşık klasör yapısını tarar, görselleri sayar, boyutlarını ölçer ve Excel raporu oluşturur.").pack(anchor="w", pady=(0,20))
        
        f = ttk.Frame(frame); f.pack(fill=tk.X)
        ttk.Label(f, text="Taranacak Ana Klasör:").pack(anchor="w")
        
        self.path_env = tk.StringVar(value="/Volumes/KIOXIA/Yeni_Ürün_v2")
        ttk.Entry(f, textvariable=self.path_env).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
        ttk.Button(f, text="Klasör Seç", command=lambda: self.select_folder(self.path_env)).pack(side=tk.RIGHT)
        
        ttk.Button(frame, text="▶ TARAMAYI BAŞLAT", command=self.run_envanter).pack(pady=30)

    def run_envanter(self):
        if not MODULE_STATUS['envanter']: return
        path = self.path_env.get()
        def task():
            try:
                # Modüldeki hedefi güncelle
                disk_envanter_guncelleyici.HEDEF_KLASOR = Path(path)
                disk_envanter_guncelleyici.EnvanterTarayici(path).tara_ve_raporla()
            except Exception as e: print(f"HATA: {e}")
        threading.Thread(target=task, daemon=True).start()

    # --- SEKME 2: OPTİMİZASYON ---
    def setup_optimize_tab(self):
        frame = ttk.Frame(self.tab_optimize, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Mükerrerleri siler, 4MB altına sıkıştırır, ICC profillerini koruyarak CMYK->RGB dönüşümü yapar.").pack(anchor="w", pady=(0,20))
        
        # Excel
        f1 = ttk.Frame(frame); f1.pack(fill=tk.X, pady=5)
        ttk.Label(f1, text="Analiz Excel (Guncel_Disk_Envanteri):").pack(side=tk.LEFT)
        self.path_opt_exc = tk.StringVar(value="Guncel_Disk_Envanteri.xlsx")
        ttk.Entry(f1, textvariable=self.path_opt_exc).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f1, text="Seç", command=lambda: self.select_file(self.path_opt_exc)).pack(side=tk.RIGHT)
        
        # Hedef
        f2 = ttk.Frame(frame); f2.pack(fill=tk.X, pady=5)
        ttk.Label(f2, text="Hedef Klasör (Çıktı Yeri):").pack(side=tk.LEFT)
        self.path_opt_trg = tk.StringVar(value="/Volumes/KIOXIA/Optimize_Edilmis_Urunler_V7")
        ttk.Entry(f2, textvariable=self.path_opt_trg).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f2, text="Seç", command=lambda: self.select_folder(self.path_opt_trg)).pack(side=tk.RIGHT)
        
        # Ayarlar
        self.opt_dry = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Simülasyon Modu (İşaretliyse dosya oluşturmaz, sadece raporlar)", variable=self.opt_dry).pack(anchor="w", pady=15)
        
        ttk.Button(frame, text="▶ OPTİMİZASYONU BAŞLAT", command=self.run_optimize).pack(pady=10)

    def run_optimize(self):
        if not MODULE_STATUS['optimizer']: return
        exc = self.path_opt_exc.get(); trg = self.path_opt_trg.get(); dry = self.opt_dry.get()
        def task():
            try:
                # Modül değişkenlerini GUI'den gelenlerle güncelle
                main_optimizer.ANALIZ_DOSYASI = exc
                main_optimizer.HEDEF_ANA_KLASOR = Path(trg)
                main_optimizer.DRY_RUN = dry
                
                # Motoru başlat
                main_optimizer.StokOptimizeEdici(exc).baslat()
            except Exception as e: print(f"HATA: {e}")
        threading.Thread(target=task, daemon=True).start()

    # --- SEKME 3: BAYİ ---
    def setup_bayi_tab(self):
        frame = ttk.Frame(self.tab_bayi, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Müşteri talep listesine göre bayiye özel 'Hazır Paket' klasörü oluşturur.").pack(anchor="w", pady=(0,20))
        
        # Envanter Dosyası
        f1 = ttk.Frame(frame); f1.pack(fill=tk.X, pady=5)
        ttk.Label(f1, text="Güncel Envanter:").pack(side=tk.LEFT)
        self.path_bayi_env = tk.StringVar(value="Guncel_Disk_Envanteri.xlsx")
        ttk.Entry(f1, textvariable=self.path_bayi_env).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f1, text="Seç", command=lambda: self.select_file(self.path_bayi_env)).pack(side=tk.RIGHT)

        # Talep Dosyası
        f2 = ttk.Frame(frame); f2.pack(fill=tk.X, pady=5)
        ttk.Label(f2, text="Talep Listesi (Ürün Gamı):").pack(side=tk.LEFT)
        self.path_bayi_talep = tk.StringVar(value="25.11.27 Ürün Gamı.xlsx")
        ttk.Entry(f2, textvariable=self.path_bayi_talep).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f2, text="Seç", command=lambda: self.select_file(self.path_bayi_talep)).pack(side=tk.RIGHT)
        
        # Hedef
        f3 = ttk.Frame(frame); f3.pack(fill=tk.X, pady=5)
        ttk.Label(f3, text="Paket Nereye Kaydedilsin?:").pack(side=tk.LEFT)
        self.path_bayi_target = tk.StringVar(value="/Volumes/KIOXIA/Bayi_Paketi_2025")
        ttk.Entry(f3, textvariable=self.path_bayi_target).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f3, text="Seç", command=lambda: self.select_folder(self.path_bayi_target)).pack(side=tk.RIGHT)

        ttk.Button(frame, text="▶ PAKETİ HAZIRLA", command=self.run_bayi).pack(pady=20)

    def run_bayi(self):
        if not MODULE_STATUS['bayi']: return
        env = self.path_bayi_env.get(); talep = self.path_bayi_talep.get(); trg = self.path_bayi_target.get()
        def task():
            try:
                bayi_paketi_hazirlayici.ENVANTER_DOSYASI = Path(env)
                bayi_paketi_hazirlayici.URUN_GAMI_DOSYASI = Path(talep)
                bayi_paketi_hazirlayici.HEDEF_KLASOR = Path(trg)
                bayi_paketi_hazirlayici.DRY_RUN = False # Direkt işlem
                
                app = bayi_paketi_hazirlayici.BayiPaketiOlusturucu()
                if app.verileri_yukle(): app.eslestir_ve_islem_yap()
            except Exception as e: print(f"HATA: {e}")
        threading.Thread(target=task, daemon=True).start()

    # --- SEKME 4: AI ÖZET RAPOR (OLLAMA ENTEGRASYONU) ---
    def setup_ai_tab(self):
        frame = ttk.Frame(self.tab_ai, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        info = ttk.Label(frame, text="Bilgisayarınızdaki Yerel AI (Ollama - Llama 3.2 Vision) kullanılarak Excel verileri analiz edilir. İnternet gerektirmez.", wraplength=900)
        info.pack(anchor="w", pady=(0,20))

        # Durum Bilgisi
        status_frame = ttk.LabelFrame(frame, text="AI Motoru Durumu", padding=10)
        status_frame.pack(fill=tk.X, pady=10)
        
        # Basit bir kontrol (Ollama çalışıyor mu?)
        try:
            import ollama
            ttk.Label(status_frame, text="✅ Ollama Kütüphanesi Yüklü", foreground="green").pack(anchor="w")
        except ImportError:
            ttk.Label(status_frame, text="⚠️ 'ollama' kütüphanesi eksik! (pip install ollama)", foreground="red").pack(anchor="w")

        # Excel
        f = ttk.Frame(frame); f.pack(fill=tk.X)
        ttk.Label(f, text="Excel Dosyası:").pack(side=tk.LEFT)
        self.path_ai_excel = tk.StringVar(value="Guncel_Disk_Envanteri.xlsx")
        ttk.Entry(f, textvariable=self.path_ai_excel).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f, text="Seç", command=lambda: self.select_file(self.path_ai_excel)).pack(side=tk.RIGHT)

        ttk.Button(frame, text="✨ LLAMA İLE ÖZETLE", command=self.run_ai_ozet).pack(pady=20)

    def run_ai_ozet(self):
        if not MODULE_STATUS['ai']: return
        
        excel = self.path_ai_excel.get()
        out = os.path.dirname(excel) if excel else "."
        
        def task():
            try:
                # Key parametresi artık gereksiz ama uyumluluk için None gönderiyoruz
                ai_envanter_analizcisi.AIEnvanterAnalizcisi(excel, out, None).baslat()
            except Exception as e: print(f"HATA: {e}")
        threading.Thread(target=task, daemon=True).start()


    # --- SEKME 3: BAYİ ---
    def setup_bayi_tab(self):
        frame = ttk.Frame(self.tab_bayi, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Bu özellik müşteri talep listesine göre bayiye özel klasör hazırlar.").pack(anchor="w")
        
        # Envanter Dosyası
        f1 = ttk.Frame(frame); f1.pack(fill=tk.X, pady=5)
        ttk.Label(f1, text="Güncel Envanter:").pack(side=tk.LEFT)
        self.path_bayi_env = tk.StringVar(value="Guncel_Disk_Envanteri.xlsx")
        ttk.Entry(f1, textvariable=self.path_bayi_env).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f1, text="Seç", command=lambda: self.select_file(self.path_bayi_env)).pack(side=tk.RIGHT)

        # Talep Dosyası
        f2 = ttk.Frame(frame); f2.pack(fill=tk.X, pady=5)
        ttk.Label(f2, text="Ürün Gamı Listesi:").pack(side=tk.LEFT)
        self.path_bayi_talep = tk.StringVar(value="25.11.27 Ürün Gamı.xlsx")
        ttk.Entry(f2, textvariable=self.path_bayi_talep).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(f2, text="Seç", command=lambda: self.select_file(self.path_bayi_talep)).pack(side=tk.RIGHT)
        
        # --- YENİ EKLENEN BUTON ---
        # self.main_frame yerine 'frame' kullanıyoruz.
        ttk.Button(
            frame, 
            text="🔍 EKSİK ÜRÜN ANALİZİ (A/B Kıyasla)", 
            command=self.eksik_urun_analizi_yap
        ).pack(pady=(20, 5)) # Biraz boşluk bırak
        
        ttk.Button(frame, text="▶ PAKETİ HAZIRLA", command=self.run_bayi).pack(pady=5)

    # YARDIMCILAR
    def select_folder(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)
        
    def select_file(self, var):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx;*.xls")])
        if f: var.set(f)

    def eksik_urun_analizi_yap(self):
            # Dosya yollarını Bayi sekmesindeki giriş kutularından alıyoruz
            dosya_a = self.path_bayi_talep.get() # Ürün Gamı
            dosya_b = self.path_bayi_env.get()   # Disk Envanteri
            
            self.log_ekle(f"Analiz Başlatılıyor...\nA: {dosya_a}\nB: {dosya_b}")
            
            # İşlemi çalıştır
            try:
                sonuc_mesaji = A_B_Kiyasla.karsilastirma_baslat(dosya_a, dosya_b)
                self.log_ekle(sonuc_mesaji)
                messagebox.showinfo("Analiz Sonucu", sonuc_mesaji)
            except Exception as e:
                err = f"Analiz Hatası: {str(e)}"
                self.log_ekle(err)
                messagebox.showerror("Hata", err)

if __name__ == "__main__":
    root = tk.Tk()
    app = MedyaYonetimApp(root)
    root.mainloop()