import os
import pandas as pd
import json
from pathlib import Path

# --- AYARLAR (Burayı Kendi Yollarına Göre Düzenle) ---
ANALIZ_AYARLARI = {
    "katalog_klasoru": "/Volumes/KIOXIA/YENI_KATALOG",  # Taranacak ana klasör
    "excel_dosyalari": [
        "/Users/halukinal/dosya_organizer/tk Katalog Çalışması 09.10.25.xlsx",
        "/Users/halukinal/dosya_organizer/25.06.03 Ürün Listesi.xlsx"
    ]
}
# ----------------------------------------------------

def klasor_yapisini_ozetle(start_path, max_depth=3):
    """Klasör hiyerarşisinin bir özetini çıkarır."""
    start_path = Path(start_path)
    if not start_path.exists():
        return f"HATA: Klasör bulunamadı: {start_path}"

    yapi_ozeti = {"root": str(start_path), "tree": {}}

    print(f"Klasör taranıyor: {start_path}...")

    # Sadece ilk seviye klasörleri (Ebatlar) alalım
    ebat_klasorleri = [p for p in start_path.iterdir() if p.is_dir()]
    
    # Çok fazla klasör varsa sadece ilk 3 tanesini örnekle
    ornek_ebatlar = ebat_klasorleri[:3] 
    
    for ebat in ornek_ebatlar:
        ebat_dict = {}
        # Yüzeyler (Mat, Parlak vb.)
        yuzey_klasorleri = [p for p in ebat.iterdir() if p.is_dir()]
        ornek_yuzeyler = yuzey_klasorleri[:2] # Her ebat için 2 yüzey örnekle

        for yuzey in ornek_yuzeyler:
            # Ürünler
            urun_klasorleri = [p for p in yuzey.iterdir() if p.is_dir()]
            ornek_urunler = urun_klasorleri[:3] # Her yüzey için 3 ürün örnekle
            
            urun_listesi = []
            for urun in ornek_urunler:
                # Klasör içindeki dosya tiplerini say
                dosyalar = [f.suffix for f in urun.iterdir() if f.is_file()]
                urun_listesi.append({
                    "ad": urun.name,
                    "icerik_ornekleri": list(set(dosyalar)) # örn: ['.jpg', '.json']
                })
            
            ebat_dict[yuzey.name] = {
                "ornek_urunler": urun_listesi,
                "toplam_urun_sayisi": len(urun_klasorleri)
            }
        
        yapi_ozeti["tree"][ebat.name] = ebat_dict

    return yapi_ozeti

def excel_yapisini_analiz_et(dosya_yollari):
    """Excel dosyalarının sütunlarını ve örnek verilerini çeker."""
    excel_analizi = {}
    
    for yol in dosya_yollari:
        path = Path(yol)
        print(f"Excel okunuyor: {path.name}...")
        
        if not path.exists():
            excel_analizi[path.name] = "HATA: Dosya bulunamadı."
            continue
            
        try:
            # Genelde başlıklar 1. veya 2. satırda olur, garanti olsun diye hepsini okuyup
            # kullanıcıya sütunları göstereceğiz.
            # İlk 5 satırı okuyalım (Header tespiti için)
            df = pd.read_excel(path, nrows=5, header=None) 
            
            # Veriyi JSON formatına çevir (tarihleri string yap)
            data_json = json.loads(df.to_json(orient='split', date_format='iso'))
            
            excel_analizi[path.name] = {
                "ham_ilk_5_satir": data_json['data']
            }
        except Exception as e:
            excel_analizi[path.name] = f"HATA: {str(e)}"
            
    return excel_analizi

def main():
    rapor = {
        "klasor_yapisi": klasor_yapisini_ozetle(ANALIZ_AYARLARI["katalog_klasoru"]),
        "excel_yapilari": excel_yapisini_analiz_et(ANALIZ_AYARLARI["excel_dosyalari"])
    }
    
    # Raporu kaydet
    cikis_dosyasi = "yapi_analiz_raporu.json"
    with open(cikis_dosyasi, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=4)
        
    print("-" * 50)
    print(f"ANALİZ TAMAMLANDI! '{cikis_dosyasi}' oluşturuldu.")
    print("Lütfen bu dosyanın içeriğini kopyalayıp chat'e yapıştır.")
    print("-" * 50)

    # İstersen direkt konsola da basalım ki kopyalaması kolay olsun
    print(json.dumps(rapor, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    main()