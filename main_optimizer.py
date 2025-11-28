import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile

# =============================================================================
# ⚙️ AYARLAR VE KONFİGÜRASYON
# =============================================================================

# Okunacak Envanter Dosyası
ANALIZ_DOSYASI = "Guncel_Disk_Envanteri.xlsx"

# Yeni dosyaların oluşturulacağı hedef klasör
HEDEF_ANA_KLASOR = Path("/Volumes/KIOXIA/Optimize_Edilmis_Urunler_V7")

# GÜVENLİK MODU 
# True  -> Sadece simülasyon yapar, dosya kopyalamaz/oluşturmaz.
# False -> Gerçek işlem yapar.
DRY_RUN = False 

# 📉 OPTİMİZASYON AYARLARI
HEDEF_MAX_BOYUT_MB = 4.0      # Hedef: Dosya boyutu 4MB altı olsun
STANDART_KISA_KENAR = 1000    # Hedef: Kısa kenar maksimum 1000px olsun
MIN_KALITE = 60               # Kalite en fazla %60'a düşsün
BASLANGIC_KALITE = 95         # Başlangıç kalitesi
KALITE_AZALTMA_ADIMI = 5      # Döngüde kalite düşürme adımı

# 🔧 PIL AYARLARI
Image.MAX_IMAGE_PIXELS = None       
ImageFile.LOAD_TRUNCATED_IMAGES = True 

class StokOptimizeEdici:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)

    def get_file_size_mb(self, path):
        """Dosya boyutunu MB cinsinden hesaplar."""
        return os.path.getsize(path) / (1024 * 1024)

    def optimize_image(self, source_path, target_path):
        """
        Görseli okur, RENK FORMATINA DOKUNMADAN (CMYK/RGB korunur),
        ICC Renk Profilini KORUR (Renk kaymasını önler),
        kısa kenarı 1000px'e indirir ve 4MB altına sıkıştırır.
        """
        try:
            file_size_mb = self.get_file_size_mb(source_path)
            
            with Image.open(source_path) as img:
                # --- ADIM 0: ICC Profilini Yakala (Renk Doğruluğu İçin) ---
                icc_profile = img.info.get('icc_profile')
                
                # Orijinal boyutları al
                width, height = img.size
                kisa_kenar = min(width, height)
                
                # --- ADIM 1: Renk Dönüşümü İPTAL ---
                # Kullanıcı isteği üzerine CMYK -> RGB dönüşümü kaldırıldı.
                
                # --- ADIM 2: Karar Mekanizması ---
                # Eğer kısa kenar 1000px altındaysa VE dosya boyutu 4MB altındaysa
                # hiç dokunma, direkt kopyala (Kalite kaybı 0 olsun)
                resize_needed = kisa_kenar > STANDART_KISA_KENAR
                
                if not resize_needed and file_size_mb < HEDEF_MAX_BOYUT_MB:
                    shutil.copy2(source_path, target_path)
                    return True

                # --- ADIM 3: İşleme ---
                
                # A) Resize (Sadece gerekliyse)
                if resize_needed:
                    ratio = STANDART_KISA_KENAR / kisa_kenar
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    # LANCZOS: En iyi küçültme filtresi
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # B) Sıkıştırma Döngüsü
                current_quality = BASLANGIC_KALITE
                saved_successfully = False

                while current_quality >= MIN_KALITE:
                    try:
                        # Formatı koruyarak kaydet.
                        # ÖNEMLİ: icc_profile parametresi ile renk haritasını geri yüklüyoruz.
                        save_kwargs = {
                            "quality": current_quality,
                            "optimize": True
                        }
                        
                        if icc_profile:
                            save_kwargs["icc_profile"] = icc_profile

                        img.save(target_path, "JPEG", **save_kwargs)
                        
                        # Boyut kontrolü
                        if self.get_file_size_mb(target_path) < HEDEF_MAX_BOYUT_MB:
                            saved_successfully = True
                            break # Hedefe ulaşıldı
                        
                        current_quality -= KALITE_AZALTMA_ADIMI
                    except OSError:
                        # CMYK JPEG yazma hatası vb. olursa
                        raise Exception("Format Yazma Hatası")

                # Eğer kalite düşmesine rağmen kaydedilemediyse (çok nadir)
                if not saved_successfully:
                     shutil.copy2(source_path, target_path)

                return True

        except Exception as e:
            # Herhangi bir hata durumunda orijinali kopyala
            try:
                shutil.copy2(source_path, target_path)
                return True
            except:
                return False

    def baslat(self):
        print(f"📊 Envanter dosyası okunuyor: {self.excel_path.name}")
        try:
            df = pd.read_excel(self.excel_path)
        except Exception as e:
            print(f"❌ Hata: Excel dosyası okunamadı. {e}")
            return

        # Gerekli sütunları kontrol et
        required_cols = ['Yol', 'Ebat', 'Orijinal_Ad', 'Yuzey']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ Hata: Excel dosyasında şu sütunlar eksik: {required_cols}")
            print("Lütfen 'Guncel_Disk_Envanteri.xlsx' dosyasını kullandığınızdan emin olun.")
            return

        print(f"\n🚀 Toplam {len(df)} klasör satırı işlenecek.")
        print(f"🎯 Hedef: Kısa Kenar Max {STANDART_KISA_KENAR}px | Boyut Max {HEDEF_MAX_BOYUT_MB}MB")
        print(f"🎨 Renk Profili: KORUNACAK (ICC Profile Copy)")
        print(f"📂 Çıktı Dizini: {HEDEF_ANA_KLASOR}")
        
        if DRY_RUN:
            print("\n⚠️  [SİMÜLASYON MODU] Dosyalar kopyalanmayacak/oluşturulmayacak.")
            print("    Gerçek işlem için kodun başındaki 'DRY_RUN = False' yapın.\n")
        else:
            if not HEDEF_ANA_KLASOR.exists():
                HEDEF_ANA_KLASOR.mkdir(parents=True)

        basarili_sayisi = 0
        hatali_sayisi = 0
        
        # Excel'deki her satırı gez
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Optimizasyon"):
            kaynak_klasor = Path(row['Yol'])
            
            try:
                ebat = str(row['Ebat']).strip()
                urun = str(row['Orijinal_Ad']).strip()
                yuzey = str(row['Yuzey']).strip()
                hedef_dizin = HEDEF_ANA_KLASOR / ebat / urun / yuzey
            except:
                continue 
            
            if not kaynak_klasor.exists():
                continue

            if DRY_RUN:
                continue 
            
            try:
                if not hedef_dizin.exists():
                    hedef_dizin.mkdir(parents=True)
                
                for dosya in kaynak_klasor.iterdir():
                    if dosya.is_file() and dosya.suffix.lower() in ['.jpg', '.jpeg']:
                        hedef_dosya = hedef_dizin / dosya.name
                        self.optimize_image(dosya, hedef_dosya)
                
                basarili_sayisi += 1
            except Exception as e:
                hatali_sayisi += 1

        print("\n" + "="*50)
        print("🏁 İŞLEM TAMAMLANDI")
        print("="*50)
        print(f"✅ Başarıyla İşlenen Klasör: {basarili_sayisi}")
        
        if DRY_RUN:
            print("\n💡 SİMÜLASYON TAMAMLANDI. Gerçek işlem için 'DRY_RUN = False' yapın.")

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ HATA: Pillow eksik. 'pip install Pillow' çalıştırın.")
        exit()
        
    app = StokOptimizeEdici(ANALIZ_DOSYASI)
    app.baslat()