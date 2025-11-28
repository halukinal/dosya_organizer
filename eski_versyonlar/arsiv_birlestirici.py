import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm  # İlerleme çubuğu için (yoksa: pip install tqdm)

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================
ANALIZ_DOSYASI = "Stok_Analiz_V4_Final.xlsx"
HEDEF_ANA_KLASOR = Path("/Volumes/KIOXIA/Yeni_Ürün_v2")

# GÜVENLİK MODU (True = Sadece simülasyon yapar, kopyalamaz. False = Gerçek işlem)
DRY_RUN = True  # <-- ÖNCE TRUE İLE ÇALIŞTIRIP KONTROL ET, SONRA FALSE YAP

class ArsivBirlestirici:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)
        
    def en_iyi_klasoru_sec(self, paths):
        """
        Aynı ürüne ait birden fazla klasör varsa, 
        içinde en çok JPG dosyası olanı seçer.
        """
        best_path = None
        max_files = -1
        
        for path_str in paths:
            p = Path(path_str)
            if not p.exists(): continue
            
            # Klasördeki jpg sayısını bul
            # (Büyük/küçük harf duyarlı olmadan)
            count = 0
            try:
                count = len([f for f in p.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg']])
            except Exception:
                continue
                
            if count > max_files:
                max_files = count
                best_path = p
                
        return best_path, max_files

    def baslat(self):
        print(f"📊 Analiz dosyası okunuyor: {self.excel_path}...")
        try:
            df = pd.read_excel(self.excel_path, sheet_name="Disk_Envanter")
        except Exception as e:
            print(f"❌ Hata: Excel dosyası okunamadı. {e}")
            return

        if 'KEY' not in df.columns or 'Yol' not in df.columns:
            print("❌ Hata: Excel dosyasında 'KEY' veya 'Yol' sütunları eksik.")
            return

        # 1. Gruplama (Key'e göre)
        print("🔄 Mükerrer kayıtlar analiz ediliyor...")
        gruplar = df.groupby('KEY')['Yol'].apply(list).to_dict()
        
        total_urun = len(gruplar)
        print(f"✅ Toplam {total_urun} benzersiz ürün tespit edildi.")
        print(f"📂 Hedef Klasör: {HEDEF_ANA_KLASOR}")
        
        if DRY_RUN:
            print("\n⚠️  MOD: DRY RUN (SİMÜLASYON) - Dosya kopyalanmayacak, sadece listelenecek.\n")
        else:
            print("\n🚀 MOD: GERÇEK İŞLEM - Dosyalar kopyalanmaya başlıyor...\n")
            if not HEDEF_ANA_KLASOR.exists():
                HEDEF_ANA_KLASOR.mkdir(parents=True)

        # İstatistikler
        kopyalanan = 0
        atlanan = 0
        hatali = 0

        # 2. İşlem Döngüsü
        # tqdm ile ilerleme çubuğu gösterelim
        for key, paths in tqdm(gruplar.items(), desc="Ürünler İşleniyor", unit="ürün"):
            
            # En dolu klasörü seç
            kaynak_yol, dosya_sayisi = self.en_iyi_klasoru_sec(paths)
            
            if not kaynak_yol:
                hatali += 1
                continue

            # Hedef yolu oluştur: Yeni_Ürün_v2 / Ebat / Yüzey / ÜrünAdı
            # Kaynak yolun son 3 parçasını alıyoruz (Ebat/Yuzey/Ad)
            # Örn: .../60x120/Mat/Abaco -> parts[-3:]
            try:
                parts = kaynak_yol.parts
                # Güvenli yol inşası: Klasör yapısının standart olduğunu varsayıyoruz
                # /Volumes/KIOXIA/YENI_KATALOG/60X120/Mat/UrunAdi
                relative_structure = Path(*parts[-3:]) 
                hedef_yol = HEDEF_ANA_KLASOR / relative_structure
            except Exception:
                # Yol yapısı beklenmedikse düz kopyala
                hedef_yol = HEDEF_ANA_KLASOR / "Diger" / kaynak_yol.name

            # Bilgilendirme (Duplicate durumu varsa yazdır)
            if len(paths) > 1 and DRY_RUN:
                print(f"⚡️ ÇİFT KAYIT ÇÖZÜLDÜ: {key}")
                print(f"   Seçilen ({dosya_sayisi} dosya): {kaynak_yol}")
                print(f"   Elenenler: {[p for p in paths if p != str(kaynak_yol)]}")

            # Kopyalama İşlemi
            if not DRY_RUN:
                try:
                    if hedef_yol.exists():
                        # Eğer hedefte zaten varsa atla (veya üzerine yazma stratejisi belirle)
                        atlanan += 1
                    else:
                        shutil.copytree(kaynak_yol, hedef_yol)
                        kopyalanan += 1
                except Exception as e:
                    print(f"❌ Kopyalama hatası ({key}): {e}")
                    hatali += 1
            else:
                kopyalanan += 1

        # Sonuç Raporu
        print("\n" + "="*40)
        print("🏁 İŞLEM TAMAMLANDI")
        print("="*40)
        print(f"Toplam Benzersiz Ürün : {total_urun}")
        print(f"İşlenen (Kopyalanan)  : {kopyalanan}")
        print(f"Atlanan (Zaten Var)   : {atlanan}")
        print(f"Hatalı / Bulunamayan  : {hatali}")
        
        if DRY_RUN:
            print("\n💡 İpucu: Sonuçlar doğru görünüyorsa kodun başındaki 'DRY_RUN = False' yapıp tekrar çalıştır.")

if __name__ == "__main__":
    app = ArsivBirlestirici(ANALIZ_DOSYASI)
    app.baslat()