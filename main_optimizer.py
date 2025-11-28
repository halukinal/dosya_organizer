import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm
from PIL import Image  # pip install Pillow

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================
ANALIZ_DOSYASI = "Stok_Analiz_V4_Final.xlsx"
HEDEF_ANA_KLASOR = Path("/Volumes/KIOXIA/Yeni_Ürün_v3")

# GÜVENLİK MODU (True = Simülasyon, False = Gerçek İşlem)
DRY_RUN = False 

# 📉 HEDEF ODAKLI SIKIŞTIRMA AYARLARI
HEDEF_MAX_BOYUT_MB = 4.0      # Hedef dosya boyutu (MB)
STANDART_KISA_KENAR = 1000    # Eğer boyut düşürülecekse kısa kenar bu olacak
MIN_KALITE = 60               # Kaliteyi en fazla %60'a kadar düşür
BASLANGIC_KALITE = 95         # İlk deneme kalitesi
KALITE_AZALTMA_ADIMI = 5      # Her denemede %5 düşür

class StokOptimizeEdici:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)
        
    def smart_parse_key(self, key_str):
        """KEY'i parçalar: 'URUNADI_EBAT_YUZEY' -> (UrunAdi, Ebat, Yuzey)"""
        if not isinstance(key_str, str): return None, None, None
        parts = key_str.rsplit('_', 2) 
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        return None, None, None

    def normalize_product_name(self, name):
        """'BAMBU ABACO' -> 'ABACO BAMBU' (Alfabetik sıralama)"""
        if not name: return "BILINMEYEN_URUN"
        words = name.split()
        return " ".join(sorted(words))

    def get_file_size_mb(self, path):
        """Dosya boyutunu MB cinsinden döndürür."""
        return os.path.getsize(path) / (1024 * 1024)

    def optimize_image(self, source_path, target_path):
        """
        Senin algoritmana göre görseli işler:
        1. 4MB altındaysa ve kısa kenar < 1000px ise -> Kopyala
        2. Değilse -> Kısa kenarı 1000px yap.
        3. Boyut hala > 4MB ise -> Kaliteyi düşürerek döngüye gir.
        """
        try:
            # Önce dosya boyutunu kontrol et
            file_size_mb = self.get_file_size_mb(source_path)
            
            with Image.open(source_path) as img:
                # Orijinal boyutlar
                width, height = img.size
                kisa_kenar = min(width, height)
                
                # RGB Dönüşümü (PNG/RGBA sorununu önler)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # --- SENARYO 1: HİÇ DOKUNMA ---
                # Dosya 4MB'dan küçük VE kısa kenarı 1000px'den küçükse
                if file_size_mb < HEDEF_MAX_BOYUT_MB and kisa_kenar <= STANDART_KISA_KENAR:
                    shutil.copy2(source_path, target_path)
                    return True

                # --- SENARYO 2: BOYUTLANDIRMA VE SIKIŞTIRMA ---
                
                # A) Yeniden Boyutlandırma (Resize)
                # Kısa kenar 1000px'den büyükse, 1000px'e indir
                if kisa_kenar > STANDART_KISA_KENAR:
                    ratio = STANDART_KISA_KENAR / kisa_kenar
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # B) Döngüsel Sıkıştırma (Iterative Compression)
                # Hedef boyuta ulaşana kadar kaliteyi düşür
                current_quality = BASLANGIC_KALITE
                
                while current_quality >= MIN_KALITE:
                    # Bellekte kaydetmeyi dene (Diske yazmadan boyut ölçmek için buffer kullanılabilir ama
                    # en garantisi geçici dosyaya yazıp bakmaktır, basitlik için direkt hedefe yazıp kontrol ediyoruz)
                    
                    img.save(target_path, "JPEG", quality=current_quality, optimize=True)
                    
                    new_size_mb = self.get_file_size_mb(target_path)
                    
                    if new_size_mb < HEDEF_MAX_BOYUT_MB:
                        # Başarılı! 4MB altına indi.
                        return True
                    
                    # Başarısız, kaliteyi düşür ve tekrar dene
                    current_quality -= KALITE_AZALTMA_ADIMI
                
                # Döngü bitti, min kaliteye (%60) rağmen 4MB altına düşmediyse
                # Yapacak bir şey yok, son haliyle (%60) kalsın.
                return True

        except Exception as e:
            print(f"⚠️ Görsel hatası ({source_path.name}): {e}")
            # Hata durumunda orijinali kopyala (Veri kaybı olmasın)
            try:
                shutil.copy2(source_path, target_path)
                return True
            except:
                return False

    def baslat(self):
        print(f"📊 Analiz dosyası okunuyor: {self.excel_path.name}...")
        try:
            df = pd.read_excel(self.excel_path, sheet_name="Disk_Envanter")
        except Exception as e:
            print(f"❌ Hata: Excel dosyası okunamadı. {e}")
            return

        # --- ADIM 1: GRUPLAMA (En iyi görseli seçme) ---
        print("🧠 Veriler analiz ediliyor...")
        transfer_listesi = {} 
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Analiz"):
            key = row['KEY']
            kaynak_yol = Path(row['Yol'])
            
            if not kaynak_yol.exists(): continue
            
            ham_isim, ebat, yuzey = self.smart_parse_key(key)
            if not ham_isim: continue
            
            temiz_isim = self.normalize_product_name(ham_isim)
            hedef_klasor_imzasi = (ebat, temiz_isim, yuzey)
            
            # Kalite kontrol (JPG var mı?)
            try:
                jpg_sayisi = len([f for f in kaynak_yol.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg']])
            except:
                jpg_sayisi = 0
            if jpg_sayisi == 0: continue

            # En dolu klasörü seç
            if hedef_klasor_imzasi in transfer_listesi:
                if jpg_sayisi > transfer_listesi[hedef_klasor_imzasi]['count']:
                    transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}
            else:
                transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}

        # --- ADIM 2: OPTİMİZASYON VE KOPYALAMA ---
        print(f"\n🚀 {len(transfer_listesi)} ürün işlenecek.")
        print(f"🎯 Hedef: Max {HEDEF_MAX_BOYUT_MB}MB | Kısa Kenar: {STANDART_KISA_KENAR}px")
        print(f"📂 Çıktı Yeri: {HEDEF_ANA_KLASOR}")

        if DRY_RUN:
            print("\n⚠️  MOD: DRY RUN (SİMÜLASYON) - İşlem yapılmayacak.\n")
        else:
            if not HEDEF_ANA_KLASOR.exists():
                HEDEF_ANA_KLASOR.mkdir(parents=True)

        basarili = 0
        hatali = 0
        
        for (ebat, urun, yuzey), veri in tqdm(transfer_listesi.items(), desc="Optimizasyon"):
            kaynak = veri['path']
            # Yeni Yapı: Ebat / Ürün Adı / Yüzey
            hedef_dizin = HEDEF_ANA_KLASOR / ebat / urun / yuzey
            
            if DRY_RUN:
                continue
            else:
                try:
                    if not hedef_dizin.exists():
                        hedef_dizin.mkdir(parents=True)
                    
                    for dosya in kaynak.iterdir():
                        if dosya.is_file() and dosya.suffix.lower() in ['.jpg', '.jpeg']:
                            hedef_dosya = hedef_dizin / dosya.name
                            
                            # --> SİHİR BURADA ÇAĞRILIYOR <--
                            self.optimize_image(dosya, hedef_dosya)
                    
                    basarili += 1
                except Exception as e:
                    print(f"❌ Hata ({urun}): {e}")
                    hatali += 1

        print("\n" + "="*40)
        print("🏁 İŞLEM TAMAMLANDI")
        print(f"Klasör: {basarili} | Hatalı: {hatali}")
        
        if DRY_RUN:
            print("\n💡 Test başarılıysa: 'DRY_RUN = False' yapıp çalıştır.")

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ HATA: Pillow eksik. 'pip install Pillow' çalıştır.")
        exit()
        
    app = StokOptimizeEdici(ANALIZ_DOSYASI)
    app.baslat()