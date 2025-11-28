import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile

# =============================================================================
# ⚙️ AYARLAR VE KONFİGÜRASYON
# =============================================================================

# Analiz edilecek Excel dosyası (GÜNCELLENDİ)
# Artık en son oluşturulan güncel envanter raporunu baz alıyor
ANALIZ_DOSYASI = "Guncel_Disk_Envanteri.xlsx"

# İşlenmiş dosyaların kopyalanacağı yeni ana klasör
HEDEF_ANA_KLASOR = Path("/Volumes/KIOXIA/Yeni_Ürün_v4")

# GÜVENLİK MODU 
# True  -> Sadece simülasyon yapar, dosya kopyalamaz.
# False -> Gerçek işlem yapar.
DRY_RUN = False 

# 📉 GÖRSEL SIKIŞTIRMA VE OPTİMİZASYON AYARLARI
HEDEF_MAX_BOYUT_MB = 3.0      # Heddeflenen maksimum dosya boyutu
STANDART_KISA_KENAR = 1000    # Kural: Kısa kenar EN FAZLA bu kadar olabilir
MIN_KALITE = 60               # Kalite düşürme alt sınırı (%)
BASLANGIC_KALITE = 95         # İlk deneme kalitesi (%)
KALITE_AZALTMA_ADIMI = 5      # Her denemede kalite ne kadar düşsün?

# 🔧 PIL KÜTÜPHANESİ İNCE AYARLARI
Image.MAX_IMAGE_PIXELS = None       # Devasa pikselli görsellerde hata vermesin (DecompressionBombError önlemi)
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Yarım kalmış/bozuk görselleri okumaya çalışsın

class StokOptimizeEdici:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)
        
    def smart_parse_key(self, key_str):
        """
        KEY yapısını (URUNADI_EBAT_YUZEY) parçalar.
        Geriye (UrunAdi, Ebat, Yuzey) döner.
        """
        if not isinstance(key_str, str): return None, None, None
        
        # Sondan 2 alt çizgiye göre böl (Yüzey ve Ebat sondadır)
        parts = key_str.rsplit('_', 2) 
        
        if len(parts) == 3:
            urun_adi, ebat, yuzey = parts[0], parts[1], parts[2]
            return urun_adi, ebat, yuzey
        return None, None, None

    def normalize_product_name(self, name):
        """
        Ürün adındaki kelime sırası hatalarını giderir.
        Örn: 'BAMBU ABACO' -> 'ABACO BAMBU'
        """
        if not name: return "BILINMEYEN_URUN"
        words = name.split()
        return " ".join(sorted(words))

    def get_file_size_mb(self, path):
        """Dosya boyutunu MB cinsinden hesaplar."""
        return os.path.getsize(path) / (1024 * 1024)

    def optimize_image(self, source_path, target_path):
        """
        Görseli okur, CMYK ise RGB'ye çevirir.
        Kısa kenarı 1000px'den büyükse 1000px'e küçültür.
        Dosya boyutu 4MB altına inene kadar sıkıştırır.
        """
        try:
            file_size_mb = self.get_file_size_mb(source_path)
            
            with Image.open(source_path) as img:
                width, height = img.size
                kisa_kenar = min(width, height)
                
                # --- ADIM 1: Renk Formatı Dönüşümü (CMYK -> RGB) ---
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # --- ADIM 2: Karar Mekanizması ---
                
                # KURAL: Kısa kenar 1000px'den büyükse MUTLAKA küçültülecek.
                resize_needed = kisa_kenar > STANDART_KISA_KENAR
                
                # Eğer boyutlandırma gerekmiyorsa ve dosya boyutu zaten küçükse -> Direkt Kopyala
                if not resize_needed and file_size_mb < HEDEF_MAX_BOYUT_MB:
                    shutil.copy2(source_path, target_path)
                    return True

                # --- ADIM 3: İşleme Başla ---

                # A) Yeniden Boyutlandırma (Resize)
                # Sadece kısa kenar 1000px üzerindeyse çalışır
                if resize_needed:
                    ratio = STANDART_KISA_KENAR / kisa_kenar
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    
                    # LANCZOS filtresi, küçültme işleminde en iyi kaliteyi verir
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # B) Döngüsel Sıkıştırma (Iterative Compression)
                # Dosya boyutu 4MB altına inene kadar kaliteyi adım adım düşür
                current_quality = BASLANGIC_KALITE
                while current_quality >= MIN_KALITE:
                    img.save(target_path, "JPEG", quality=current_quality, optimize=True)
                    
                    # Kontrol et: İstenen boyuta indi mi?
                    if self.get_file_size_mb(target_path) < HEDEF_MAX_BOYUT_MB:
                        return True
                    
                    # İnmediyse kaliteyi biraz daha düşür ve tekrar dene
                    current_quality -= KALITE_AZALTMA_ADIMI
                
                # Eğer %60 kaliteye rağmen hala 4MB üstündeyse (çok nadir), son hali kalsın.
                return True

        except Exception as e:
            # Kritik Hata Yönetimi: Pillow işleyemezse orijinali kopyala
            print(f"⚠️ Görsel işlenemedi, orijinal kopyalanıyor ({source_path.name}): {e}")
            try:
                shutil.copy2(source_path, target_path)
                return True
            except:
                return False

    def baslat(self):
        print(f"📊 Analiz dosyası yükleniyor: {self.excel_path.name}")
        try:
            # Guncel_Disk_Envanteri.xlsx dosyasını oku (Sayfa adı genelde Sheet1 olur veya ilk sayfa okunur)
            df = pd.read_excel(self.excel_path)
        except Exception as e:
            print(f"❌ Hata: Excel dosyası okunamadı. Lütfen dosya yolunu kontrol et.\nDetay: {e}")
            return

        # --- AŞAMA 1: GRUPLAMA VE SEÇME ---
        print("🧠 Envanter analiz ediliyor ve en iyi kaynaklar seçiliyor...")
        
        # Hedef klasör başına en iyi kaynak görseli tutacak sözlük
        transfer_listesi = {} 
        
        # tqdm ile ilerleme çubuğu göstererek analizi yap
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Analiz"):
            key = row['KEY']
            kaynak_yol = Path(row['Yol'])
            
            # Kaynak klasör diskte gerçekten var mı?
            if not kaynak_yol.exists(): continue
            
            # Anahtarı parçala
            ham_isim, ebat, yuzey = self.smart_parse_key(key)
            if not ham_isim: continue
            
            # İsimdeki kelime sırasını düzelt (Arama kolaylığı için)
            temiz_isim = self.normalize_product_name(ham_isim)
            
            # Benzersiz Klasör İmzası (Tuple)
            hedef_klasor_imzasi = (ebat, temiz_isim, yuzey)
            
            # Klasör içindeki JPG sayısını kontrol et
            try:
                # Guncel_Disk_Envanteri dosyasında 'Gorsel_Sayisi' sütunu varsa direkt kullan
                if 'Gorsel_Sayisi' in row:
                    jpg_sayisi = int(row['Gorsel_Sayisi'])
                else:
                    jpg_sayisi = len([f for f in kaynak_yol.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg']])
            except:
                jpg_sayisi = 0
            
            if jpg_sayisi == 0: continue # Boş klasörleri atla

            # MANTIK: Aynı ürün için birden fazla klasör varsa, EN ÇOK görseli olanı seç.
            if hedef_klasor_imzasi in transfer_listesi:
                if jpg_sayisi > transfer_listesi[hedef_klasor_imzasi]['count']:
                    transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}
            else:
                transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}

        # --- AŞAMA 2: İŞLEME, OPTİMİZASYON VE KOPYALAMA ---
        print(f"\n🚀 {len(transfer_listesi)} adet benzersiz ürün işlenecek.")
        print(f"🎯 Hedef Standartlar: Max {HEDEF_MAX_BOYUT_MB}MB | Kısa Kenar: Max {STANDART_KISA_KENAR}px")
        print(f"📂 Çıktı Dizini: {HEDEF_ANA_KLASOR}")
        
        if DRY_RUN:
            print("\n⚠️  [GÜVENLİ MOD] DRY RUN AKTİF: Dosyalar kopyalanmayacak, sadece simülasyon yapılıyor.\n")
        else:
            # Hedef klasörü oluştur
            if not HEDEF_ANA_KLASOR.exists():
                HEDEF_ANA_KLASOR.mkdir(parents=True)

        basarili_sayisi = 0
        hatali_sayisi = 0
        
        for (ebat, urun, yuzey), veri in tqdm(transfer_listesi.items(), desc="Optimizasyon"):
            kaynak = veri['path']
            # Yeni Hiyerarşik Yapı: Ebat / Ürün Adı / Yüzey
            hedef_dizin = HEDEF_ANA_KLASOR / ebat / urun / yuzey
            
            if DRY_RUN:
                # Simülasyon modunda işlem yapma, döngüyü devam ettir
                continue
            else:
                try:
                    if not hedef_dizin.exists():
                        hedef_dizin.mkdir(parents=True)
                    
                    # Klasördeki her görseli işle
                    for dosya in kaynak.iterdir():
                        if dosya.is_file() and dosya.suffix.lower() in ['.jpg', '.jpeg']:
                            hedef_dosya = hedef_dizin / dosya.name
                            
                            # Optimizasyon fonksiyonunu çağır
                            self.optimize_image(dosya, hedef_dosya)
                    
                    basarili_sayisi += 1
                except Exception as e:
                    print(f"❌ Klasör işleme hatası ({urun}): {e}")
                    hatali_sayisi += 1

        # --- RAPORLAMA ---
        print("\n" + "="*50)
        print("🏁 İŞLEM TAMAMLANDI")
        print("="*50)
        print(f"✅ Başarıyla Oluşturulan Klasör: {basarili_sayisi}")
        print(f"❌ Hatalı / Atlanan Klasör    : {hatali_sayisi}")
        
        if DRY_RUN:
            print("\n💡 İPUCU: Simülasyon başarılı görünüyorsa, kodun başındaki")
            print("         'DRY_RUN = True' satırını 'False' yapıp tekrar çalıştırın.")

if __name__ == "__main__":
    # Pillow kütüphanesi kontrolü
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ HATA: 'Pillow' kütüphanesi eksik.")
        print("Lütfen terminalde şu komutu çalıştırın: pip install Pillow")
        exit()
        
    app = StokOptimizeEdici(ANALIZ_DOSYASI)
    app.baslat()