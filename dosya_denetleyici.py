import pandas as pd
import re
from pathlib import Path
import time
import sys

# --- AYARLAR ---

# 1. Taranacak organize klasör
KAYNAK_DIZIN = Path("/Volumes/KIOXIA/YENI_KATALOG")

# 2. Hangi uzantılara bakılacak?
ARANACAK_UZANTILAR = ('.jpg', '.jpeg')

# 3. Analiz edilecek Excel listelerinin konfigürasyonları
# Buraya birden fazla Excel dosyası tanımı eklenebilir.
EXCEL_LISTELERI_CONFIG = [
    {
        "path": Path("/Users/halukinal/Pythone Proje/dosya_organizer/tk Katalog Çalışması 09.10.25.xlsx"),
        "header_index": 2,  # Excel'de 3. satır
        "urun_kolonu": "Ürün",
        "ebat_kolonu": "Ebat"
    },
    {
        "path": Path("/Users/halukinal/Pythone Proje/dosya_organizer/25.06.03 Ürün Listesi.xlsx"),
        "header_index": 1,  # Excel'de 2. satır
        "urun_kolonu": "Ürün Adı -2",
        "ebat_kolonu": "Ebat"
    }
]


# --- HELPER FONKSİYON ---

def normalize_str(s: str) -> str:
    """Stringleri karşılaştırma için (büyük harf, boşluksuz) normalize eder."""
    if not isinstance(s, str):
        return ""
    return re.sub(r'[\W_]+', '', s).upper()

# --- ÇEKİRDEK FONKSİYONLAR ---

def dosya_sistemini_tara() -> list:
    """
    YENI_KATALOG klasör yapısını tarar (Ebat/Yuzey/UrunAdi)
    ve ürün bilgilerini listeler.
    """
    print(f"'{KAYNAK_DIZIN}' yeni yapısı taranıyor...")
    scanned_products = []
    
    # Ebat klasörlerini bul (ilk seviye, örn: '60X120')
    for ebat_dir in KAYNAK_DIZIN.glob('*'):
        if not ebat_dir.is_dir():
            continue
        
        # Yüzey klasörlerini bul (ikinci seviye, örn: 'Mat')
        for yuzey_dir in ebat_dir.glob('*'):
            if not yuzey_dir.is_dir():
                continue
                
            # Ürün klasörlerini bul (üçüncü seviye, örn: 'Volcano...')
            for urun_dir in yuzey_dir.glob('*'):
                if not urun_dir.is_dir() or urun_dir.name == 'kopya':
                    continue
                
                # Dosya sayısını hesapla (sadece görseller)
                file_count = 0
                for ext in ARANACAK_UZANTILAR:
                    file_count += len(list(urun_dir.glob(f'*{ext}')))
                    file_count += len(list(urun_dir.glob(f'*{ext.upper()}')))

                scanned_products.append({
                    "ebat_str": ebat_dir.name,
                    "yuzey_str": yuzey_dir.name,
                    "urun_adi_str": urun_dir.name,
                    "file_count": file_count
                })

    if not scanned_products:
        print("HATA: Kaynak dizinde (YENI_KATALOG) beklenen yapıda klasör bulunamadı.")
        return []
        
    print(f"{len(scanned_products)} adet organize ürün klasörü bulundu.")
    return scanned_products


def excel_listesini_oku(config: dict) -> list:
    """
    Verilen konfigürasyona göre bir Excel dosyasını okur
    ve gerekli ürün anahtarlarını listeler.
    """
    dosya_yolu = config["path"]
    header_index = config["header_index"]
    urun_kolonu = config["urun_kolonu"]
    ebat_kolonu = config["ebat_kolonu"]
    
    print(f"\n'{dosya_yolu.name}' listesi okunuyor...")
    
    if not dosya_yolu.exists():
        print(f"HATA: {dosya_yolu} dosyası bulunamadı. Bu liste atlanacak.")
        return []
        
    try:
        if dosya_yolu.suffix == '.xlsx':
            df = pd.read_excel(dosya_yolu, header=header_index)
        else:
            print(f"HATA: Desteklenmeyen dosya formatı: {dosya_yolu.suffix}")
            return []
            
    except ImportError:
        print("HATA: .xlsx dosyasını okumak için 'openpyxl' kütüphanesi gerekli.")
        print("Lütfen 'pip install openpyxl' komutu ile kurun.")
        return []
    except Exception as e:
        print(f"HATA: {dosya_yolu} okunurken hata: {e}")
        return []

    gerekli_kolonlar = [urun_kolonu, ebat_kolonu]
    if not all(col in df.columns for col in gerekli_kolonlar):
        print(f"HATA: '{dosya_yolu.name}' dosyasında şu kolonlar bulunamadı: {gerekli_kolonlar}")
        print(f"Mevcut kolonlar: {list(df.columns)}")
        return []

    urun_listesi = []
    for _, row in df.iterrows():
        urun_adi = row[urun_kolonu]
        ebat = row[ebat_kolonu]

        if pd.isna(urun_adi) or pd.isna(ebat):
            continue

        urun_key = normalize_str(str(urun_adi))
        ebat_key = normalize_str(str(ebat))
        
        if not urun_key or not ebat_key:
            continue
            
        orijinal_isim = f"{row[urun_kolonu]} ({row[ebat_kolonu]})"
        
        urun_listesi.append({
            "urun_key": urun_key,
            "ebat_key": ebat_key,
            "orijinal_isim": orijinal_isim,
            "kaynak": dosya_yolu.name  # Raporlama için kaynak dosya adını ekle
        })

    print(f"'{dosya_yolu.name}' listesinden {len(urun_listesi)} ürün okundu.")
    return urun_listesi


def excel_raporu_olustur(rapor_verileri: list):
    """Analiz sonucunu bir Excel dosyası olarak kaydeder."""
    if not rapor_verileri:
        print("Rapor verisi bulunamadı, Excel dosyası oluşturulmadı.")
        return

    print("\nExcel raporu oluşturuluyor...")
    RAPOR_DOSYASI = Path("Eksik_Urun_Raporu.xlsx")
    
    try:
        df = pd.DataFrame(rapor_verileri)
        
        # Veriyi Kaynak, Durum ve Ürün'e göre sırala
        df_sirali = df.sort_values(by=['Kaynak', 'Durum', 'Ürün'])
        
        # Sütun sırasını belirle (Kaynak en başta olsun)
        df_sirali = df_sirali[['Kaynak', 'Ürün', 'Durum', 'Detay']]
        
        df_sirali.to_excel(RAPOR_DOSYASI, index=False, sheet_name='Urun_Durum_Raporu')
        
        print(f"--- BAŞARILI ---")
        print(f"Rapor başarıyla '{RAPOR_DOSYASI.resolve()}' konumuna kaydedildi.")
    
    except ImportError:
        print("HATA: Excel (.xlsx) raporu yazmak için 'openpyxl' kütüphanesi gerekli.")
    except Exception as e:
        print(f"HATA: Excel raporu kaydedilirken bir sorun oluştu: {e}")


def analiz_et_ve_raporla(urun_listesi: list, taranan_urunler: list):
    """
    Excel listesini taranan klasörlerle karşılaştırır,
    konsola log basar ve rapor için veri döndürür.
    """
    print("\n--- Analiz ve Raporlama Başlatıldı ---")
    log_kayitlari = []
    rapor_verileri = []
    excel_urun_sayisi = len(urun_listesi)
    bulunan_urun_sayisi = 0
    
    # Taranan ürünleri normalize edip hızlı arama için bir yapıya sokalım
    # Key: ebat_key, Value: [ (norm_urun_adi, tam_yol, file_count), ... ]
    taranan_map = {}
    for urun in taranan_urunler:
        ebat_key = normalize_str(urun["ebat_str"])
        norm_urun_adi = normalize_str(urun["urun_adi_str"])
        
        # "Ebat/Yuzey/UrunAdi" şeklinde göreceli bir yol oluştur
        tam_yol = f"{urun['ebat_str']}/{urun['yuzey_str']}/{urun['urun_adi_str']}"
        
        if ebat_key not in taranan_map:
            taranan_map[ebat_key] = []
        
        taranan_map[ebat_key].append( (norm_urun_adi, tam_yol, urun["file_count"]) )
        

    # Excel listesindeki her ürünü kontrol et
    for urun_data in urun_listesi:
        urun_key = urun_data['urun_key']
        ebat_key = urun_data['ebat_key']
        orijinal_isim = urun_data['orijinal_isim']
        kaynak = urun_data['kaynak'] # Hangi Excel'den geldiği bilgisi
        
        found = False
        
        # Sadece ilgili ebattaki klasörlere bak
        potansiyel_klasorler = taranan_map.get(ebat_key, [])
        
        for norm_urun_adi, tam_yol, file_count in potansiyel_klasorler:
            
            if urun_key in norm_urun_adi:
                if file_count == 0:
                    log_str = f"[KLASÖR VAR - İÇİ BOŞ] {orijinal_isim} (Yol: .../{tam_yol})"
                    rapor_verileri.append({'Kaynak': kaynak, 'Ürün': orijinal_isim, 'Durum': 'KLASÖR BOŞ', 'Detay': f"(Yol: .../{tam_yol})"})
                else:
                    log_str = f"[BULUNDU] {orijinal_isim} -> {file_count} adet görsel. (Yol: .../{tam_yol})"
                    rapor_verileri.append({'Kaynak': kaynak, 'Ürün': orijinal_isim, 'Durum': 'BULUNDU', 'Detay': f"{file_count} adet görsel. (Yol: .../{tam_yol})"})
                
                log_kayitlari.append(log_str)
                bulunan_urun_sayisi += 1
                found = True
                break 

        if not found:
            log_str = f"[EKSİK]    {orijinal_isim} -> Organize klasör (YENI_KATALOG) içinde bulunamadı."
            log_kayitlari.append(log_str)
            rapor_verileri.append({'Kaynak': kaynak, 'Ürün': orijinal_isim, 'Durum': 'EKSİK', 'Detay': 'Organize klasör (YENI_KATALOG) içinde bulunamadı.'})

    # --- Raporlama (KONSOL) ---
    print("\n--- Konsol Logları ---")
    log_kayitlari.sort()
    for log in log_kayitlari:
        print(log)
    
    print("-" * 30)
    print("--- Analiz Özeti ---")
    print(f"Taranan Toplam Excel Ürünü: {excel_urun_sayisi}")
    print(f"Bulunan/Eşleşen Ürün Sayısı: {bulunan_urun_sayisi}")
    print(f"{excel_urun_sayisi - bulunan_urun_sayisi} adet ürün EKSİK veya (KLASÖRÜ BOŞ).")
    print("-" * 30)
    
    # --- Raporlama (EXCEL) ---
    excel_raporu_olustur(rapor_verileri)


# --- ANA ÇALIŞTIRMA ---

def main():
    """Script'in ana çalışma akışı."""
    start_time = time.time()
    
    # 1. Dosya sistemini BİR KEZ tara
    taranan_urunler = dosya_sistemini_tara()
    if not taranan_urunler:
        print("Dosya sistemi taraması başarısız oldu veya klasör boş. İşlem durduruldu.")
        sys.exit(1) # Programı hata koduyla sonlandır

    # 2. Tüm Excel listelerini tara ve tek bir listede birleştir
    tum_excel_urunleri = []
    for config in EXCEL_LISTELERI_CONFIG:
        urunler = excel_listesini_oku(config)
        if urunler:
            tum_excel_urunleri.extend(urunler)
            
    if not tum_excel_urunleri:
        print("Tüm Excel listeleri okunamadı veya listeler boş. İşlem durduruldu.")
        sys.exit(1)

    # 3. Toplu listeyi analiz et ve raporla
    analiz_et_ve_raporla(tum_excel_urunleri, taranan_urunler)

    # 4. Süre raporlaması
    end_time = time.time()
    print(f"\nİşlem {end_time - start_time:.2f} saniyede tamamlandı.")


if __name__ == "__main__":
    main()