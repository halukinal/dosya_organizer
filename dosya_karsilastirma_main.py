import pandas as pd
import re
import os

# --- Fonksiyon: Normalleştirme Anahtarı ---
def normalize_key(text):
    """
    Karşılaştırma için metinleri temizler ve standart bir formata getirir.
    Örn: "Aleats 60X120 Mat Grey" -> "ALEATSGREY"
    """
    if not isinstance(text, str):
        return ""
    
    text = str(text).upper()
    text = re.sub(r'\d+X\d+', '', text) # Boyutları kaldır
    
    kaldirilacak_kelimeler = [
        'MAT', 'PARLAK', 'FLP', 'LAPPATO', 'SOFT', 'ANTISLIP', 'SAS',
        'FULL', 'DEKOR', 'HAT1', 'HAT'
    ]
    for kelime in kaldirilacak_kelimeler:
        text = re.sub(r'\b' + re.escape(kelime) + r'\b', '', text)
        
    text = re.sub(r'[^A-Z]', '', text) # Sadece harfler kalsın
    return text

# --- Fonksiyon: Katalog Tarama ---
def tara_ve_excel_olustur(root_path, output_excel_path):
    """
    Klasörleri tarar ve jpg dosyalarını listeler.
    """
    print(f"Tarama başlatıldı: {root_path}")
    bulunan_urunler = {}

    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if filename.lower().endswith(('.jpg', '.jpeg')):
                full_path = os.path.join(dirpath, filename)
                try:
                    relative_path = os.path.relpath(full_path, root_path)
                    parts = relative_path.split(os.path.sep)

                    if len(parts) >= 3:
                        ebat = parts[0]
                        yuzey = parts[1]
                        urun_klasoru_adi = parts[-2]
                        
                        if urun_klasoru_adi not in bulunan_urunler:
                            bulunan_urunler[urun_klasoru_adi] = {
                                "Bulunan Ebat": ebat,
                                "Bulunan Yüzey": yuzey,
                                "İlk Bulunan Dosya Yolu": full_path
                            }
                except ValueError:
                    pass
    
    if not bulunan_urunler:
        print("Klasörde uygun yapıda görsel bulunamadı.")
        return

    df = pd.DataFrame.from_dict(bulunan_urunler, orient='index')
    df = df.reset_index().rename(columns={'index': 'Bulunan Ürün Adı'})
    
    try:
        df.to_excel(output_excel_path, index=False)
        print(f"Tarama tamamlandı. {len(df)} adet benzersiz ürün bulundu.")
        print(f"Rapor oluşturuldu: {output_excel_path}")
    except Exception as e:
        print(f"Excel kaydetme hatası: {e}")

# --- Ana İşlem Fonksiyonu ---
def ana_karsilastirma_islemi():
    
    # --- 1. AYARLAR ---
    
    # Taranacak klasör (Senin yolun)
    KATALOG_ANA_DIZINI = "/Volumes/KIOXIA/YENI_KATALOG" 
    
    # --- BURAYI DİKKATLİ KONTROL ET ---
    # Bilgisayarındaki dosya isimleri tam olarak böyle olmalı (.xlsx uzantılı):
    KATALOG_CALISMASI_DOSYASI = "/Users/halukinal/Pythone Proje/dosya_organizer/tk Katalog Çalışması 09.10.25.xlsx"
    URUN_LISTESI_DOSYASI = "/Users/halukinal/Pythone Proje/dosya_organizer/25.06.03 Ürün Listesi.xlsx"
    
    # Çıktı dosyaları
    BULUNAN_URUNLER_CIKTISI = "bulunan_urunler_v2.xlsx"
    FINAL_RAPOR_DOSYASI = "karsilastirma_raporu_v2.xlsx"

    # --- 2. ADIM: Tarama ---
    # Eğer zaten tarama yaptıysan ve bulunan_urunler.xlsx varsa tekrar tarama yapmayabilirsin
    # Ama emin olmak için her seferinde yapması iyidir.
    if os.path.isdir(KATALOG_ANA_DIZINI):
        tara_ve_excel_olustur(KATALOG_ANA_DIZINI, BULUNAN_URUNLER_CIKTISI)
    else:
        print(f"UYARI: {KATALOG_ANA_DIZINI} yolu bulunamadı. Tarama atlanıyor, varsa mevcut liste kullanılacak.")

    # --- 3. ADIM: Dosyaları Yükle (XLSX OKUMA) ---
    try:
        # 1. Taranan dosya
        if not os.path.exists(BULUNAN_URUNLER_CIKTISI):
            print("HATA: bulunan_urunler.xlsx dosyası yok. Tarama başarısız olmuş olabilir.")
            return
        df_dosya_sistemi = pd.read_excel(BULUNAN_URUNLER_CIKTISI)
        
        # 2. Katalog Çalışması (Excel Olarak Oku)
        # Başlıklar 3. satırda olduğu için header=2
        print(f"Okunuyor: {KATALOG_CALISMASI_DOSYASI}")
        df_katalog = pd.read_excel(KATALOG_CALISMASI_DOSYASI, header=2)
        
        # 3. Ürün Listesi (Excel Olarak Oku)
        # Başlıklar 2. satırda olduğu için header=1
        print(f"Okunuyor: {URUN_LISTESI_DOSYASI}")
        df_urun_listesi = pd.read_excel(URUN_LISTESI_DOSYASI, header=1)
        
    except FileNotFoundError as e:
        print(f"\n!!! HATA: Dosya bulunamadı: {e.filename}")
        print("Lütfen Excel dosyalarının isimlerini kontrol et ve kod ile aynı klasörde olduğundan emin ol.")
        print("İpucu: Dosya isimlerini basitçe 'katalog.xlsx' ve 'liste.xlsx' yapıp kodda da değiştirebilirsin.")
        return
    except Exception as e:
        print(f"Dosya okuma sırasında beklenmeyen hata: {e}")
        return

    # --- 4. ADIM: Eşleştirme Anahtarlarını Oluştur ---
    print("Veriler işleniyor ve karşılaştırılıyor...")
    
    df_dosya_sistemi['match_key'] = df_dosya_sistemi['Bulunan Ürün Adı'].apply(normalize_key)
    
    # Sütun kontrolü ve anahtar oluşturma
    if 'Stok Adi' in df_katalog.columns:
        df_katalog['match_key'] = df_katalog['Stok Adi'].apply(normalize_key)
    elif 'Ürün' in df_katalog.columns:
        df_katalog['match_key'] = df_katalog['Ürün'].apply(normalize_key)
    else:
        print("UYARI: Katalog dosyasında 'Stok Adi' veya 'Ürün' sütunu bulunamadı. Sütun adları:")
        print(df_katalog.columns)
        return

    if 'Ürün Adı -2' in df_urun_listesi.columns:
        df_urun_listesi['match_key'] = df_urun_listesi['Ürün Adı -2'].apply(normalize_key)
    else:
        print("UYARI: Ürün listesinde 'Ürün Adı -2' sütunu bulunamadı. Sütun adları:")
        print(df_urun_listesi.columns)
        return
    
    # Boşları temizle
    df_dosya_sistemi = df_dosya_sistemi[df_dosya_sistemi['match_key'] != ""]
    df_katalog = df_katalog[df_katalog['match_key'] != ""]
    df_urun_listesi = df_urun_listesi[df_urun_listesi['match_key'] != ""]

    # --- 5. ADIM: Karşılaştırma ---
    keys_dosya = set(df_dosya_sistemi['match_key'])
    keys_katalog = set(df_katalog['match_key'])
    keys_urun_listesi = set(df_urun_listesi['match_key'])

    # Raporları hazırla
    rapor1_df = df_dosya_sistemi[df_dosya_sistemi['match_key'].isin(keys_dosya - keys_katalog)] # Görsel Var, Katalog Yok
    rapor2_df = df_katalog[df_katalog['match_key'].isin(keys_katalog - keys_dosya)] # Katalog Var, Görsel Yok
    rapor3_df = df_dosya_sistemi[df_dosya_sistemi['match_key'].isin(keys_dosya - keys_urun_listesi)] # Görsel Var, Liste Yok
    rapor4_df = df_urun_listesi[df_urun_listesi['match_key'].isin(keys_urun_listesi - keys_dosya)] # Liste Var, Görsel Yok
    
    # Tam Eşleşme
    tam_eslesen_keys = keys_dosya.intersection(keys_katalog).intersection(keys_urun_listesi)
    rapor5_df = df_dosya_sistemi[df_dosya_sistemi['match_key'].isin(tam_eslesen_keys)]

    # --- 6. ADIM: Kaydetme ---
    try:
        with pd.ExcelWriter(FINAL_RAPOR_DOSYASI) as writer:
            rapor1_df.to_excel(writer, sheet_name='Gorsel_Var_Katalog_Yok', index=False)
            rapor2_df.to_excel(writer, sheet_name='Katalog_Var_Gorsel_Yok', index=False)
            rapor3_df.to_excel(writer, sheet_name='Gorsel_Var_UrunList_Yok', index=False)
            rapor4_df.to_excel(writer, sheet_name='UrunList_Var_Gorsel_Yok', index=False)
            rapor5_df.to_excel(writer, sheet_name='Tum_Listelerde_Eslesenler', index=False)
            
            # Ham veriler
            df_dosya_sistemi.to_excel(writer, sheet_name='Ham_Gorsel_Verisi', index=False)
            
        print(f"\n--- İŞLEM BAŞARILI ---")
        print(f"Rapor dosyası oluşturuldu: {FINAL_RAPOR_DOSYASI}")
        
    except Exception as e:
        print(f"Rapor kaydedilirken hata oluştu: {e}")
        print("Dosya açık olabilir, lütfen kapatıp tekrar deneyin.")

if __name__ == "__main__":
    ana_karsilastirma_islemi()