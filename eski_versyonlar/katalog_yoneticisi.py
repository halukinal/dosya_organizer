import pandas as pd
import re
import os
from pathlib import Path
from collections import Counter

# =============================================================================
# ⚙️ KONFİGÜRASYON (AYARLAR)
# =============================================================================
class KatalogConfig:
    ROOT_DIR = Path("/Volumes/KIOXIA/YENI_KATALOG")
    
    # Kısaltma Haritası (Standartlaştırma için)
    SURFACE_MAP = {
        "FULL LAPPATO": "FLP", "LAPPATO": "FLP", "FLP": "FLP",
        "SEMI LAPPATO": "SLP", "SLP": "SLP",
        "SUGAR": "SGR", "SGR": "SGR", 
        "RECTIFIED": "REC", "REC": "REC", "REKTI": "REC",
        "MAT": "MAT", 
        "PARLAK": "PARLAK", 
        "ANTISLIP": "ANTISLIP", "SOFT ANTISLIP": "ANTISLIP",
        "DEKOR": "DEKOR"
    }
    
    # Excel Dosyaları
    EXCEL_FILES = [
        {
            "path": Path("/Users/halukinal/dosya_organizer/tk   09.10.25.xlsx"),
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
# 🧠 VERİ NORMALİZASYON MOTORU
# =============================================================================
class DataNormalizer:
    
    @staticmethod
    def standardize_size(text):
        """Boyutları standartlaştırır (Örn: '60 x 120' -> '60X120')"""
        if not isinstance(text, (str, int, float)): return ""
        text = str(text).upper().strip()
        text = re.sub(r'\s*X\s*', 'X', text)
        return text

    @staticmethod
    def standardize_surface(text):
        """Yüzey tiplerini kısaltmalara çevirir"""
        if not isinstance(text, str): return "DIGER"
        text = text.upper().strip()
        for key, code in KatalogConfig.SURFACE_MAP.items():
            if key == text or (f" {key} " in f" {text} "):
                return code
        return re.sub(r'[^A-Z]', '', text)

    @staticmethod
    def clean_product_name(text):
        """İsimden boyut ve yüzey bilgilerini temizler"""
        if not isinstance(text, str): return ""
        text = text.upper()
        text = re.sub(r'\d+\s*X\s*\d+', '', text)
        remove_list = list(KatalogConfig.SURFACE_MAP.keys()) + list(KatalogConfig.SURFACE_MAP.values())
        for word in remove_list:
            text = re.sub(r'\b' + word + r'\b', '', text)
        text = re.sub(r'[^A-Z0-9]', '', text)
        return text

    @staticmethod
    def create_composite_key(name, size, surface):
        """BENZERSİZ KİMLİK: ISIM_BOYUT_YUZEY"""
        clean_name = DataNormalizer.clean_product_name(name)
        std_size = DataNormalizer.standardize_size(size)
        std_surf = DataNormalizer.standardize_surface(surface)
        if not clean_name: return None
        return f"{clean_name}_{std_size}_{std_surf}"

# =============================================================================
# 📂 DOSYA SİSTEMİ TARAYICISI
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
                                "Ebat": raw_size,
                                "Yuzey": raw_surface,
                                "Gorsel_Sayisi": jpg_count,
                                "KEY": unique_key,
                                "Yol": str(urun_dir)
                            })
        
        print(f"✅ Disk taraması bitti. {len(bulunanlar)} adet ürün tespit edildi.")
        return pd.DataFrame(bulunanlar)

# =============================================================================
# 📊 EXCEL OKUYUCU
# =============================================================================
class ExcelOkuyucu:
    @staticmethod
    def oku(config):
        print(f"📊 Excel okunuyor: {config['name']}...")
        try:
            df = pd.read_excel(config['path'], header=config['header_row'])
            clean_data = []
            cols_check = [config['col_urun'], config['col_ebat'], config['col_yuzey']]
            
            if not all(col in df.columns for col in cols_check):
                print(f"⚠️ HATA: Kolonlar eksik! {cols_check}")
                return pd.DataFrame()
            
            for index, row in df.iterrows():
                raw_name = str(row[config['col_urun']])
                raw_size = str(row[config['col_ebat']])
                raw_surf = str(row[config['col_yuzey']])
                
                if pd.isna(row[config['col_urun']]): continue
                
                unique_key = DataNormalizer.create_composite_key(raw_name, raw_size, raw_surf)
                
                if unique_key:
                    clean_data.append({
                        "Kaynak": config['name'],
                        "Excel_Satir_No": index + config['header_row'] + 2, # Gerçek Excel satır numarası
                        "Orijinal_Ad": raw_name,
                        "Ebat": raw_size,
                        "Yuzey": raw_surf,
                        "KEY": unique_key
                    })
            
            return pd.DataFrame(clean_data)
        except Exception as e:
            print(f"❌ Hata: {e}")
            return pd.DataFrame()

# =============================================================================
# 📑 GELİŞMİŞ RAPORLAMA (DUPLICATE CHECK)
# =============================================================================
def frekans_analizi_ve_rapor(df_disk, df_excel_list, excel_name):
    """
    Hem varlık yokluk kontrolü yapar hem de mükerrer kayıtları raporlar.
    """
    if df_excel_list.empty: return None, None

    # 1. Frekansları Say (Counter kullanımı)
    excel_counts = Counter(df_excel_list['KEY'])
    disk_counts = Counter(df_disk['KEY']) if not df_disk.empty else Counter()
    
    # 2. Tekrar Edenleri Bul (Excel'de 1'den fazla geçenler)
    tekrarlayan_keys = [k for k, v in excel_counts.items() if v > 1]
    df_tekrar = df_excel_list[df_excel_list['KEY'].isin(tekrarlayan_keys)].sort_values(by='KEY')
    
    # 3. Analiz Tablosu Oluştur
    analiz_sonuclari = []
    
    # Tüm benzersiz anahtarlar üzerinde dön
    all_keys = set(excel_counts.keys()) | set(disk_counts.keys())
    
    for key in all_keys:
        e_count = excel_counts.get(key, 0)
        d_count = disk_counts.get(key, 0)
        
        durum = ""
        if e_count > 0 and d_count == 0:
            durum = "EKSİK (Görsel Yok)"
        elif e_count > 0 and d_count > 0:
            if e_count == d_count:
                durum = "TAM EŞLEŞME (Adet Tutuyor)"
            elif e_count > d_count:
                durum = f"KISMI EŞLEŞME (Excel'de {e_count} satır, Diskte {d_count} klasör)"
            else:
                durum = f"FAZLA GÖRSEL (Excel'de {e_count}, Diskte {d_count})"
        elif e_count == 0 and d_count > 0:
            durum = "LİSTEDE YOK (Diskte Fazla)"
            
        # Orijinal isim örneğini al
        ornek_isim = ""
        if e_count > 0:
            ornek_isim = df_excel_list[df_excel_list['KEY'] == key].iloc[0]['Orijinal_Ad']
        elif d_count > 0:
            ornek_isim = df_disk[df_disk['KEY'] == key].iloc[0]['Orijinal_Ad']
            
        analiz_sonuclari.append({
            "KEY": key,
            "Urun_Adi": ornek_isim,
            "Excel_Adet": e_count,
            "Disk_Klasor_Adet": d_count,
            "Durum": durum
        })
        
    return pd.DataFrame(analiz_sonuclari), df_tekrar

def rapor_olustur():
    # 1. Verileri Topla
    tarayici = DosyaSistemiTarayici(KatalogConfig.ROOT_DIR)
    df_disk = tarayici.tara()
    
    writer = pd.ExcelWriter("Kapsamli_Stok_Analizi_V3.xlsx", engine='openpyxl')
    
    # Diskteki ham veriyi kaydet
    if not df_disk.empty:
        df_disk.to_excel(writer, sheet_name='Fiziksel_Arsiv_Ham', index=False)
    
    # 2. Excel Analizleri
    for conf in KatalogConfig.EXCEL_FILES:
        df_ex = ExcelOkuyucu.oku(conf)
        if df_ex.empty: continue
        
        # Frekans Analizi Yap
        df_analiz, df_tekrar = frekans_analizi_ve_rapor(df_disk, df_ex, conf['name'])
        
        # Raporları Yaz
        sheet_base = conf['name'][:10]
        
        # A) Genel Analiz (Adet Kontrollü)
        df_analiz.to_excel(writer, sheet_name=f"{sheet_base}_Analiz", index=False)
        
        # B) Sadece Eksikler (Filtrelenmiş)
        df_eksik = df_analiz[df_analiz['Durum'].str.contains("EKSİK")]
        df_eksik.to_excel(writer, sheet_name=f"{sheet_base}_EKSIKLER", index=False)
        
        # C) Tekrar Eden Kayıtlar (Duplicate Rows)
        if not df_tekrar.empty:
            df_tekrar.to_excel(writer, sheet_name=f"{sheet_base}_TEKRARLAR", index=False)
            print(f"⚠️  {conf['name']}: {len(df_tekrar)} adet mükerrer satır bulundu. 'TEKRARLAR' sayfasına bak.")
            
    writer.close()
    print(f"\n✅ RAPOR OLUŞTURULDU: Kapsamli_Stok_Analizi_V3.xlsx")

if __name__ == "__main__":
    rapor_olustur()