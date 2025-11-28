import pandas as pd
import re
import os
from pathlib import Path
from collections import Counter
import difflib

# =============================================================================
# ⚙️ KONFİGÜRASYON
# =============================================================================
class KatalogConfig:
    ROOT_DIR = Path("/Volumes/KIOXIA/YENI_KATALOG")
    
    # Kısaltma ve Temizleme Haritası
    # ÖNEMLİ: Uzun kelimeler ÜSTTE olmalı ki "Semi Lappato"yu "Lappato" sanmasın.
    SURFACE_MAP = {
        "FULL LAPPATO": "FLP", "LAPPATO": "FLP", "FLP": "FLP",
        "SEMI LAPPATO": "SLP", "SLP": "SLP", "SEMILAPPATO": "SLP",
        "SUGAR": "SGR", "SGR": "SGR", 
        "RECTIFIED": "REC", "REC": "REC", "REKTI": "REC",
        "MAT": "MAT", 
        "PARLAK": "PARLAK", "PRK": "PARLAK",  # PRK eklendi
        "ANTISLIP": "ANTISLIP", "SOFT ANTISLIP": "ANTISLIP", "ASL": "ANTISLIP", # ASL eklendi
        "DEKOR": "DEKOR", "DEKAFON": "DEKOR",
        "R9": "", "R10": "", "R11": "" # Teknik kodları temizle
    }
    
    EXCEL_FILES = [
        {
            "path": Path("/Users/halukinal/dosya_organizer/tk Katalog Çalışması 09.10.25.xlsx"),
            "header_row": 2,          
            "col_urun": "Ürün",
            "col_ebat": "Ebat",
            "col_yuzey": "Yüzey Karakteri",
            "name": "Katalog_Calismasi"
        },
        {
            "path": Path("/Users/halukinal/dosya_organizer/25.06.03 Ürün Listesi.xlsx"),
            "header_row": 1,          
            "col_urun": "Ürün Adı -2",
            "col_ebat": "Ebat",
            "col_yuzey": "Yüzey Karakteri", 
            "name": "Urun_Listesi"
        }
    ]

# =============================================================================
# 🧠 GELİŞMİŞ NORMALİZASYON MOTORU
# =============================================================================
class DataNormalizer:
    
    @staticmethod
    def standardize_size(text):
        """Boyutları standartlaştırır (Örn: '59x119' -> '60X120' toleransı eklenebilir)"""
        if not isinstance(text, (str, int, float)): return ""
        text = str(text).upper().strip()
        text = re.sub(r'\s*X\s*', 'X', text)
        
        # Toleranslı Ebat Düzeltmeleri (İsteğe bağlı)
        if text == "59X119": return "60X120"
        
        return text

    @staticmethod
    def standardize_surface(text):
        """Yüzey tiplerini akıllıca kısaltır"""
        if not isinstance(text, str): return "DIGER"
        text = text.upper().strip()
        
        # Kelime uzunluğuna göre sırala (En uzun ifade önce kontrol edilir)
        # Bu sayede "Semi Lappato", "Lappato"dan önce yakalanır.
        sorted_keys = sorted(KatalogConfig.SURFACE_MAP.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            # Tam kelime eşleşmesi veya içinde geçme durumu
            if key == text or (f" {key} " in f" {text} ") or (text.endswith(f" {key}")):
                return KatalogConfig.SURFACE_MAP[key]
                
        # Hiçbiri değilse temizle ve döndür
        return re.sub(r'[^A-Z]', '', text)

    @staticmethod
    def clean_product_name(text):
        """
        Ürün isminden PRK, ASL, R11 gibi teknik terimleri temizler.
        'Black Sea PRK' -> 'BLACKSEA'
        """
        if not isinstance(text, str): return ""
        text = text.upper()
        
        # 1. Boyutları sil
        text = re.sub(r'\d+\s*X\s*\d+', '', text)
        
        # 2. Yüzey haritasındaki TÜM anahtarları isimden sil
        sorted_keys = sorted(KatalogConfig.SURFACE_MAP.keys(), key=len, reverse=True)
        for word in sorted_keys:
            if word == "": continue # Boş stringleri atla
            # Kelime sınırı (\b) ile sil
            text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
            
        # 3. Kalan harf ve rakamları birleştir
        text = re.sub(r'[^A-Z0-9]', '', text)
        return text

    @staticmethod
    def create_composite_key(name, size, surface):
        clean_name = DataNormalizer.clean_product_name(name)
        std_size = DataNormalizer.standardize_size(size)
        std_surf = DataNormalizer.standardize_surface(surface)
        if not clean_name: return None
        return f"{clean_name}_{std_size}_{std_surf}"

# =============================================================================
# 📂 TARAMA VE OKUMA
# =============================================================================
class DosyaSistemiTarayici:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        
    def tara(self):
        print(f"📂 Disk Taranıyor: {self.root_path}...")
        bulunanlar = []
        if not self.root_path.exists():
            print("❌ HATA: Katalog klasörü bulunamadı!")
            return pd.DataFrame()

        for ebat_dir in self.root_path.iterdir():
            if not ebat_dir.is_dir() or ebat_dir.name.startswith('.'): continue
            
            for yuzey_dir in ebat_dir.iterdir():
                if not yuzey_dir.is_dir() or yuzey_dir.name.startswith('.'): continue
                
                for urun_dir in yuzey_dir.iterdir():
                    if not urun_dir.is_dir() or urun_dir.name.startswith('.'): continue
                    
                    jpg_count = len(list(urun_dir.glob("*.[jJ][pP][gG]"))) + len(list(urun_dir.glob("*.[jJ][pP][eE][gG]")))
                    
                    if jpg_count > 0:
                        raw_name = urun_dir.name
                        raw_size = ebat_dir.name
                        raw_surface = yuzey_dir.name
                        unique_key = DataNormalizer.create_composite_key(raw_name, raw_size, raw_surface)
                        
                        if unique_key:
                            bulunanlar.append({
                                "Kaynak": "Fiziksel_Disk",
                                "Orijinal_Ad": raw_name,
                                "KEY": unique_key,
                                "Yol": str(urun_dir)
                            })
        return pd.DataFrame(bulunanlar)

class ExcelOkuyucu:
    @staticmethod
    def oku(config):
        print(f"📊 Excel okunuyor: {config['name']}...")
        try:
            df = pd.read_excel(config['path'], header=config['header_row'])
            clean_data = []
            
            for index, row in df.iterrows():
                raw_name = str(row[config['col_urun']])
                raw_size = str(row[config['col_ebat']])
                raw_surf = str(row[config['col_yuzey']])
                
                if pd.isna(row[config['col_urun']]): continue
                
                unique_key = DataNormalizer.create_composite_key(raw_name, raw_size, raw_surf)
                
                if unique_key:
                    clean_data.append({
                        "Kaynak": config['name'],
                        "Satir": index + config['header_row'] + 2,
                        "Orijinal_Ad": raw_name,
                        "KEY": unique_key
                    })
            return pd.DataFrame(clean_data)
        except Exception as e:
            print(f"❌ Hata: {e}")
            return pd.DataFrame()

# =============================================================================
# 🧠 AKILLI EŞLEŞTİRME VE RAPORLAMA
# =============================================================================
def yakin_eslesme_bul(hedef_key, aday_keys, cutoff=0.7):
    """
    Eğer tam eşleşme yoksa, benzer bir isim var mı diye bakar.
    Örn: 'BLACKSEAPRK' aranıyor, 'BLACKSEA' varsa önerir.
    """
    matches = difflib.get_close_matches(hedef_key, aday_keys, n=1, cutoff=cutoff)
    return matches[0] if matches else None

def analiz_yap(df_disk, df_excel, excel_name):
    print(f"\n🔍 {excel_name} analizi yapılıyor...")
    
    disk_keys = set(df_disk['KEY']) if not df_disk.empty else set()
    disk_keys_list = list(disk_keys) # Fuzzy search için liste lazım
    
    sonuclar = []
    
    # Her Excel satırını kontrol et
    for _, row in df_excel.iterrows():
        key = row['KEY']
        
        durum = ""
        disk_adet = 0
        onerilen_yol = ""
        
        # 1. Tam Eşleşme Kontrolü
        if key in disk_keys:
            disk_adet = len(df_disk[df_disk['KEY'] == key])
            durum = "TAM EŞLEŞME"
        else:
            # 2. Akıllı (Fuzzy) Eşleşme Kontrolü
            yakin_key = yakin_eslesme_bul(key, disk_keys_list)
            
            if yakin_key:
                # Bulunan yakın eşleşmenin detaylarını al
                disk_kayit = df_disk[df_disk['KEY'] == yakin_key].iloc[0]
                durum = f"OLASI EŞLEŞME (Bulunan: {disk_kayit['Orijinal_Ad']})"
                onerilen_yol = disk_kayit['Yol']
                disk_adet = 1
            else:
                durum = "EKSİK (Kesinlikle Yok)"
        
        sonuclar.append({
            "Excel_Satir": row['Satir'],
            "Urun_Adi": row['Orijinal_Ad'],
            "KEY_Excel": key,
            "Durum": durum,
            "Disk_Adet": disk_adet,
            "Disk_Yolu": onerilen_yol
        })
        
    return pd.DataFrame(sonuclar)

def main():
    # 1. Verileri Oku
    tarayici = DosyaSistemiTarayici(KatalogConfig.ROOT_DIR)
    df_disk = tarayici.tara()
    
    writer = pd.ExcelWriter("Stok_Analiz_V4_Final.xlsx", engine='openpyxl')
    
    if not df_disk.empty:
        df_disk.to_excel(writer, sheet_name='Disk_Envanter', index=False)
        
    # 2. Analizleri Çalıştır
    for conf in KatalogConfig.EXCEL_FILES:
        df_ex = ExcelOkuyucu.oku(conf)
        if df_ex.empty: continue
        
        df_sonuc = analiz_yap(df_disk, df_ex, conf['name'])
        
        # Raporları Böl
        # a) Eksikler
        df_eksik = df_sonuc[df_sonuc['Durum'].str.contains("EKSİK")]
        df_eksik.to_excel(writer, sheet_name=f"{conf['name'][:10]}_KESIN_YOK", index=False)
        
        # b) Olası Eşleşmeler (Senin 'Yanlış' dediklerini buraya yakalayacağız)
        df_olasi = df_sonuc[df_sonuc['Durum'].str.contains("OLASI")]
        df_olasi.to_excel(writer, sheet_name=f"{conf['name'][:10]}_KONTROL_ET", index=False)
        
        # c) Tam Liste
        df_sonuc.to_excel(writer, sheet_name=f"{conf['name'][:10]}_TUMU", index=False)
        
        print(f"✅ {conf['name']} için {len(df_eksik)} eksik, {len(df_olasi)} potansiyel eşleşme bulundu.")

    writer.close()
    print(f"\n🚀 İŞLEM TAMAMLANDI: Stok_Analiz_V4_Final.xlsx")

if __name__ == "__main__":
    main()