import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================
ANALIZ_DOSYASI = "Stok_Analiz_V5_Final.xlsx"
HEDEF_ANA_KLASOR = Path("/Volumes/KIOXIA/Yeni_Ürün_v3")

# GÜVENLİK MODU (True = Simülasyon, False = Kopyalar)
DRY_RUN = False 

class StokYenidenYapilandirici:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)
        
    def smart_parse_key(self, key_str):
        """
        KEY'i parçalar: 'URUNADI_EBAT_YUZEY'
        Geriye (UrunAdi, Ebat, Yuzey) döner.
        """
        if not isinstance(key_str, str): return None, None, None
        
        parts = key_str.rsplit('_', 2) # Sondan 2 kez böl (Yüzey ve Ebat için)
        
        if len(parts) == 3:
            urun_adi, ebat, yuzey = parts[0], parts[1], parts[2]
            return urun_adi, ebat, yuzey
        return None, None, None

    def normalize_product_name(self, name):
        """
        'BAMBU ABACO' ile 'ABACO BAMBU'yu aynı yapmak için
        kelimeleri alfabetik sıraya dizer.
        """
        if not name: return "BILINMEYEN_URUN"
        
        # Kelimeleri ayır, sırala ve tekrar birleştir
        # Örn: "ZEUS DARK GREY" -> "DARK GREY ZEUS" (Standart bir imza oluşturur)
        words = name.split()
        sorted_name = " ".join(sorted(words))
        return sorted_name

    def baslat(self):
        print(f"📊 Analiz dosyası okunuyor: {self.excel_path.name}...")
        try:
            df = pd.read_excel(self.excel_path, sheet_name="Disk_Envanter")
        except Exception as e:
            print(f"❌ Hata: Excel dosyası okunamadı. {e}")
            return

        # --- 1. ADIM: GRUPLAMA VE SEÇME ---
        print("🧠 Veriler analiz ediliyor ve en iyi kaynaklar seçiliyor...")
        
        # Yapılacak İşler Listesi: Key = (HedefYol), Value = KaynakYol
        transfer_listesi = {} 
        
        # İstatistikler
        toplam_satir = len(df)
        islenen_kaynak = 0
        
        for _, row in tqdm(df.iterrows(), total=toplam_satir, desc="Analiz"):
            key = row['KEY']
            kaynak_yol = Path(row['Yol'])
            
            if not kaynak_yol.exists(): continue
            
            # KEY'i parçala
            ham_isim, ebat, yuzey = self.smart_parse_key(key)
            if not ham_isim: continue
            
            # İsim Normalizasyonu (Kelime sırasını düzelt)
            temiz_isim = self.normalize_product_name(ham_isim)
            
            # Hedef Klasör Yapısı: Ebat / Ürün Adı / Yüzey
            # Örn: 60X120 / ABACOBAMBU / MAT
            hedef_klasor_imzasi = (ebat, temiz_isim, yuzey)
            
            # Dosya Sayısını Hesapla (Kalite Kontrol)
            try:
                jpg_sayisi = len([f for f in kaynak_yol.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg']])
            except:
                jpg_sayisi = 0
                
            if jpg_sayisi == 0: continue

            # MANTIK: Eğer bu hedef klasör için daha önce bir aday belirlediysek,
            # ve şimdiki adayın dosya sayısı daha fazlaysa, yenisini seç.
            if hedef_klasor_imzasi in transfer_listesi:
                mevcut_en_iyi = transfer_listesi[hedef_klasor_imzasi]
                if jpg_sayisi > mevcut_en_iyi['count']:
                    transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}
            else:
                transfer_listesi[hedef_klasor_imzasi] = {'path': kaynak_yol, 'count': jpg_sayisi}

        # --- 2. ADIM: KOPYALAMA ---
        print(f"\n🚀 {len(transfer_listesi)} adet benzersiz ürün/yüzey kombinasyonu taşınacak.")
        print(f"📂 Hedef: {HEDEF_ANA_KLASOR}")
        
        if DRY_RUN:
            print("\n⚠️  MOD: DRY RUN (SİMÜLASYON) - İşlemler sadece listelenir.\n")
        else:
            if not HEDEF_ANA_KLASOR.exists():
                HEDEF_ANA_KLASOR.mkdir(parents=True)
        
        basarili = 0
        hatali = 0
        
        for (ebat, urun, yuzey), veri in tqdm(transfer_listesi.items(), desc="Taşınıyor"):
            kaynak = veri['path']
            
            # Hedef Yolu İnşa Et
            hedef_dizin = HEDEF_ANA_KLASOR / ebat / urun / yuzey
            
            if DRY_RUN:
                # Simülasyon çıktısı
                # print(f"Plan: {kaynak.name} -> {ebat}/{urun}/{yuzey}") 
                # Çok fazla log olmaması için sadece progress bar ilerliyor
                pass
            else:
                try:
                    if not hedef_dizin.exists():
                        hedef_dizin.mkdir(parents=True)
                    
                    # Dosyaları Kopyala (Klasörü değil, içeriğini)
                    for dosya in kaynak.iterdir():
                        if dosya.is_file() and dosya.suffix.lower() in ['.jpg', '.jpeg']:
                            shutil.copy2(dosya, hedef_dizin / dosya.name)
                    
                    basarili += 1
                except Exception as e:
                    print(f"❌ Hata ({urun}): {e}")
                    hatali += 1
                    
        print("\n" + "="*40)
        print("🏁 İŞLEM TAMAMLANDI")
        print("="*40)
        print(f"Oluşturulan Klasör Sayısı: {basarili}")
        print(f"Hatalı İşlem: {hatali}")
        
        if DRY_RUN:
            print("\n💡 SİMÜLASYON BAŞARILI GÖRÜNÜYORSA:")
            print("Kodun başındaki 'DRY_RUN = True' satırını 'False' yapıp tekrar çalıştır.")

if __name__ == "__main__":
    app = StokYenidenYapilandirici(ANALIZ_DOSYASI)
    app.baslat()