import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================

# Taranacak Hedef Klasör 
# (Bunu arayüzden gönderdiğinizde otomatik güncellenir, burası varsayılandır)
HEDEF_KLASOR = Path("/Volumes/KIOXIA/Yeni_Ürün_v2")

# Çıktı Excel Dosyasının Adı
RAPOR_ADI = "Guncel_Disk_Envanteri.xlsx"

# =============================================================================
# 🛠 YARDIMCI SINIFLAR
# =============================================================================

class EnvanterTarayici:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        
    def smart_parse_path(self, path_obj):
        """
        Klasör yolundan bilgileri çıkarır.
        Beklenen Yapı: .../EBAT/URUN_ADI/YUZEY
        """
        try:
            parts = path_obj.parts
            
            # En az 3 seviye derinlikte olmalı (Ebat/Ürün/Yüzey)
            if len(parts) < 3:
                return None, None, None
            
            yuzey = parts[-1]      # En son klasör (örn: MAT)
            urun_adi = parts[-2]   # Bir üstü (örn: ABACO BAMBU)
            ebat = parts[-3]       # İki üstü (örn: 60X120)
            
            return urun_adi, ebat, yuzey
        except Exception:
            return None, None, None

    def create_key(self, urun, ebat, yuzey):
        """Benzersiz Anahtar (KEY) oluşturur: URUN_EBAT_YUZEY"""
        try:
            u = str(urun).upper().replace(" ", "")
            e = str(ebat).upper().replace(" ", "")
            y = str(yuzey).upper().replace(" ", "")
            return f"{u}_{e}_{y}"
        except:
            return "UNKNOWN_KEY"

    def calculate_folder_stats(self, files_in_folder):
        """
        Klasördeki dosyaların toplam boyutunu ve görsel sayısını hesaplar.
        Geriye (Görsel Sayısı, Toplam MB, Ortalama MB) döner.
        """
        try:
            total_bytes = 0
            image_count = 0
            
            for f in files_in_folder:
                # Sadece görsel dosyalarının boyutunu topla
                if f.suffix.lower() in ['.jpg', '.jpeg']:
                    total_bytes += f.stat().st_size
                    image_count += 1
            
            # Byte -> Megabyte dönüşümü (2 ondalık basamak)
            total_mb = round(total_bytes / (1024 * 1024), 2)
            
            # Ortalama Boyut Hesabı (Sıfıra bölünme hatasını önle)
            avg_mb = 0.0
            if image_count > 0:
                avg_mb = round(total_mb / image_count, 2)
                
            return image_count, total_mb, avg_mb
            
        except Exception:
            return 0, 0.0, 0.0

    def tara_ve_raporla(self):
        print(f"📂 Klasör taranıyor: {self.root_path}...")
        
        if not self.root_path.exists():
            print(f"❌ HATA: '{self.root_path}' klasörü bulunamadı!")
            return

        envanter_verisi = []
        
        # Tüm klasör ağacını gez
        tum_klasorler = list(os.walk(self.root_path))
        
        print(f"🧠 Toplam {len(tum_klasorler)} alt klasör analiz ediliyor...")

        for root, dirs, files in tqdm(tum_klasorler, desc="Envanter Çıkarılıyor"):
            path_obj = Path(root)
            
            # Pathlib nesnelerine dönüştür
            path_files = [path_obj / f for f in files]
            
            # İstatistikleri Hesapla (Sayi, Toplam Boyut, Ortalama Boyut)
            gorsel_sayisi, toplam_boyut_mb, ortalama_mb = self.calculate_folder_stats(path_files)
            
            # Eğer klasörde görsel varsa listeye ekle
            if gorsel_sayisi > 0:
                # Yol bilgisinden ürün detaylarını ayrıştır
                urun_adi, ebat, yuzey = self.smart_parse_path(path_obj)
                
                # Eğer yapı beklediğimiz gibi değilse "Düzensiz" olarak kaydet
                if not urun_adi: 
                    urun_adi = path_obj.name
                    ebat = "BİLİNMİYOR"
                    yuzey = "BİLİNMİYOR"

                # Key oluştur
                key = self.create_key(urun_adi, ebat, yuzey)

                # Listeye ekle
                envanter_verisi.append({
                    "Kaynak": "Fiziksel_Disk",
                    "Orijinal_Ad": urun_adi,
                    "Ebat": ebat,
                    "Yuzey": yuzey,
                    "KEY": key,
                    "Gorsel_Sayisi": gorsel_sayisi,
                    "Toplam_Boyut_MB": toplam_boyut_mb,
                    "Ortalama_Gorsel_MB": ortalama_mb,  # YENİ SÜTUN
                    "Yol": str(path_obj)
                })

        # --- RAPOR OLUŞTURMA ---
        if not envanter_verisi:
            print("⚠️ HİÇBİR ÜRÜN BULUNAMADI! Klasör boş olabilir mi?")
            return

        df = pd.DataFrame(envanter_verisi)
        
        # Sütun Sıralaması
        sutun_sirasi = ["Kaynak", "Orijinal_Ad", "Ebat", "Yuzey", "KEY", "Gorsel_Sayisi", "Toplam_Boyut_MB", "Ortalama_Gorsel_MB", "Yol"]
        
        # Mevcut sütunları koruyarak sırala
        mevcut_sutunlar = [col for col in sutun_sirasi if col in df.columns]
        df = df[mevcut_sutunlar]

        print(f"\n✅ Tarama Tamamlandı. Toplam {len(df)} ürün bulundu.")
        print(f"💾 Excel kaydediliyor: {RAPOR_ADI}")
        
        try:
            df.to_excel(RAPOR_ADI, index=False)
            print("🎉 İŞLEM BAŞARILI!")
        except Exception as e:
            print(f"❌ Excel kaydetme hatası: {e}")
            print("Dosya açık olabilir, kapatıp tekrar deneyin.")

# =============================================================================
# 🚀 ÇALIŞTIRMA
# =============================================================================
if __name__ == "__main__":
    tarayici = EnvanterTarayici(HEDEF_KLASOR)
    tarayici.tara_ve_raporla()