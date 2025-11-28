import pandas as pd
import shutil
import os
import re
from pathlib import Path
from tqdm import tqdm

# =============================================================================
# ⚙️ AYARLAR VE SABİTLER
# =============================================================================

# Girdiler
ENVANTER_DOSYASI = Path("/Users/halukinal/dosya_organizer/Guncel_Disk_Envanteri.xlsx")  # Bizim oluşturduğumuz envanter
URUN_GAMI_DOSYASI = Path("/Volumes/KIOXIA/Güral Seramik/Katalog/25.11.27 Ürün Gamı.xlsx")   # Müşteriden gelen talep listesi

# Çıktılar
HEDEF_KLASOR = Path("/Volumes/KIOXIA/Güral Seramik/Katalog/Bayi_Paketi_2025_v2") # Bayilere gidecek klasör
RAPOR_DOSYASI = "/Volumes/KIOXIA/Güral Seramik/Katalog/Bayi_Paketi_Raporu_v2.xlsx"

# Güvenlik Modu (True = Kopyalamaz, sadece raporlar)
DRY_RUN = False 

# Yüzey Haritası (Kısaltmalar)
SURFACE_MAP = {
    "FULL LAPPATO": "FLP", "LAPPATO": "FLP", "FLP": "FLP",
    "SEMI LAPPATO": "SLP", "SLP": "SLP", "SEMILAPPATO": "SLP",
    "SUGAR": "SGR", "SGR": "SGR", 
    "RECTIFIED": "REC", "REC": "REC", "REKTI": "REC",
    "MAT": "MAT", 
    "PARLAK": "PARLAK", "PRK": "PARLAK",
    "ANTISLIP": "ANTISLIP", "SOFT ANTISLIP": "ANTISLIP", "ASL": "ANTISLIP",
    "DEKOR": "DEKOR", "DEKAFON": "DEKOR"
}

# =============================================================================
# 🛠 YARDIMCI SINIFLAR
# =============================================================================

class VeriIsleyici:
    @staticmethod
    def standardize_surface(text):
        """Yüzey ismini standart kısaltmaya çevirir (örn: Full Lappato -> FLP)"""
        if not isinstance(text, str): return "DIGER"
        text = text.upper().strip()
        
        # En uzun ifadeyi önce kontrol et (Semi Lappato vs Lappato karışmasın diye)
        sorted_keys = sorted(SURFACE_MAP.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            if key == text or (f" {key} " in f" {text} ") or text.endswith(f" {key}"):
                return SURFACE_MAP[key]
        
        # Eğer haritada yoksa, sadece harfleri bırak
        return re.sub(r'[^A-Z]', '', text)

    @staticmethod
    def clean_product_name(text):
        """Ürün adından gereksiz teknik terimleri ve ebatları temizler"""
        if not isinstance(text, str): return ""
        text = text.upper()
        
        # Ebatları sil (60X120 vb.)
        text = re.sub(r'\d+\s*[X]\s*\d+', '', text)
        
        # Yüzey isimlerini sil
        sorted_keys = sorted(SURFACE_MAP.keys(), key=len, reverse=True)
        for word in sorted_keys:
            text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
            
        # Sadece harf ve rakam kalsın
        text = re.sub(r'[^A-Z0-9]', '', text)
        return text

    @staticmethod
    def create_key(urun_adi, ebat, yuzey):
        """Benzersiz Eşleştirme Anahtarı Oluşturur"""
        try:
            clean_name = VeriIsleyici.clean_product_name(str(urun_adi))
            
            # Ebat Temizliği (60 x 120 -> 60X120)
            clean_ebat = str(ebat).upper().replace(" ", "").replace("x", "X")
            
            # Yüzey Standardizasyonu
            clean_yuzey = VeriIsleyici.standardize_surface(str(yuzey))
            
            return f"{clean_name}_{clean_ebat}_{clean_yuzey}"
        except:
            return None

class BayiPaketiOlusturucu:
    def __init__(self):
        self.envanter_df = pd.DataFrame()
        self.talep_df = pd.DataFrame()
        
    def verileri_yukle(self):
        print("📊 Veriler yükleniyor...")
        
        # 1. Envanteri Oku
        try:
            self.envanter_df = pd.read_excel(ENVANTER_DOSYASI)
            print(f"✅ Envanter yüklendi: {len(self.envanter_df)} adet mevcut ürün.")
        except Exception as e:
            print(f"❌ Envanter dosyası okunamadı: {e}")
            return False

        # 2. Ürün Gamını Oku
        try:
            # Header genelde 2. satırdadır (index 1), dosya yapısına göre
            self.talep_df = pd.read_excel(URUN_GAMI_DOSYASI, header=1) 
            print(f"✅ Ürün Gamı yüklendi: {len(self.talep_df)} adet talep.")
        except Exception as e:
            print(f"❌ Ürün Gamı dosyası okunamadı: {e}")
            return False
            
        return True

    def eslestir_ve_islem_yap(self):
        print("\n🧠 Eşleştirme ve Hazırlık Başlıyor...")
        
        # Envanter KEY'lerini hızlı erişim için sözlüğe çevir
        # Key: URUN_KEY -> Value: Dosya Yolu
        envanter_map = dict(zip(self.envanter_df['KEY'], self.envanter_df['Yol']))
        
        rapor_verisi = []
        kopyalanacaklar = []

        # Ürün Gamı listesini tek tek gez
        for index, row in tqdm(self.talep_df.iterrows(), total=len(self.talep_df), desc="Analiz"):
            
            # Excel'den verileri al
            raw_urun = row.get('Ürün') # "Ürün" kolonu genelde en temiz isimdir
            if pd.isna(raw_urun): 
                raw_urun = row.get('Stok Adi') # Yedek olarak Stok Adı
            
            raw_ebat = row.get('Ebat')
            raw_yuzey = row.get('Yüzey Karakteri')
            
            if pd.isna(raw_urun) or pd.isna(raw_ebat): continue

            # Talep için KEY oluştur
            talep_key = VeriIsleyici.create_key(raw_urun, raw_ebat, raw_yuzey)
            
            durum = "BULUNAMADI"
            kaynak_yol = None
            
            # Eşleşme Kontrolü
            if talep_key in envanter_map:
                durum = "HAZIR"
                kaynak_yol = envanter_map[talep_key]
                kopyalanacaklar.append({
                    'kaynak': kaynak_yol,
                    'hedef_isim': f"{raw_ebat}_{raw_urun}_{raw_yuzey}".replace("/", "-"), # Klasör adı
                    'key': talep_key
                })
            else:
                # Fuzzy (Benzer) Arama Yapılabilir mi?
                # Şimdilik kesin eşleşme yapıyoruz, risk almamak için.
                durum = "EKSİK / EŞLEŞMEDİ"

            rapor_verisi.append({
                "Talep_Ürün": raw_urun,
                "Talep_Ebat": raw_ebat,
                "Talep_Yüzey": raw_yuzey,
                "Oluşturulan_KEY": talep_key,
                "Durum": durum,
                "Bulunan_Yol": kaynak_yol
            })

        # --- RAPORLAMA ---
        df_rapor = pd.DataFrame(rapor_verisi)
        df_rapor.to_excel(RAPOR_DOSYASI, index=False)
        print(f"\n📄 Rapor oluşturuldu: {RAPOR_DOSYASI}")
        print(f"   -> Toplam Talep: {len(df_rapor)}")
        print(f"   -> Hazır Ürün  : {len(df_rapor[df_rapor['Durum'] == 'HAZIR'])}")
        print(f"   -> Eksik Ürün  : {len(df_rapor[df_rapor['Durum'] != 'HAZIR'])}")

        # --- KOPYALAMA İŞLEMİ ---
        self.kopyalama_baslat(kopyalanacaklar)

    def kopyalama_baslat(self, liste):
        if not liste:
            print("⚠️ Kopyalanacak ürün bulunamadı.")
            return

        print(f"\n🚀 {len(liste)} adet ürün bayiler için hazırlanıyor...")
        print(f"📂 Hedef: {HEDEF_KLASOR}")
        
        if DRY_RUN:
            print("\n⚠️ [GÜVENLİ MOD] DRY_RUN = True. Kopyalama yapılmayacak, sadece simülasyon.")
        else:
            if not HEDEF_KLASOR.exists():
                HEDEF_KLASOR.mkdir(parents=True)

        basarili = 0
        hatali = 0
        
        for item in tqdm(liste, desc="Kopyalanıyor"):
            kaynak = Path(item['kaynak'])
            
            # Hedef Klasör Yapısı: /Bayi_Paketi/URUN_ADI_EBAT_YUZEY
            # Bayilerin kolay anlaması için düz bir isim kullanıyoruz
            yeni_klasor_adi = item['hedef_isim']
            # Geçersiz karakterleri temizle
            yeni_klasor_adi = "".join([c for c in yeni_klasor_adi if c.isalnum() or c in (' ', '_', '-', '.')]).strip()
            
            hedef = HEDEF_KLASOR / yeni_klasor_adi
            
            if DRY_RUN:
                continue
            
            try:
                if not hedef.exists():
                    hedef.mkdir(parents=True)
                
                # Klasör içindeki görselleri kopyala
                for dosya in kaynak.iterdir():
                    if dosya.is_file() and dosya.suffix.lower() in ['.jpg', '.jpeg']:
                        shutil.copy2(dosya, hedef / dosya.name)
                
                basarili += 1
            except Exception as e:
                print(f"❌ Kopyalama hatası ({yeni_klasor_adi}): {e}")
                hatali += 1

        if not DRY_RUN:
            print(f"\n🏁 İşlem Tamamlandı. {basarili} ürün kopyalandı, {hatali} hata.")
        else:
            print("\n💡 Simülasyon bitti. Gerçek işlem için 'DRY_RUN = False' yapın.")

if __name__ == "__main__":
    app = BayiPaketiOlusturucu()
    if app.verileri_yukle():
        app.eslestir_ve_islem_yap()