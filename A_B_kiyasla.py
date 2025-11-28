import pandas as pd
import re
import os
import A_B_kiyasla

# --- AYARLAR VE FİLTRELER ---
SILINECEK_YUZEYLER = [
    "FULL LAPPATO", "SEMI LAPPATO", "SHINE EFFECT", 
    "FLP", "SLP", "R11", "R10", "PRK", "DEKAFON", "SGR", "SAS", "ASL", 
    "ANTISLIP", "ANTSLIP", "MAT", "PARLAK"
]

RENKLER = [
    "GREY", "GRAY", "BEIGE", "WHITE", "BLACK", "ANTHRACITE", "BROWN", 
    "GOLD", "SILVER", "BLUE", "IVORY", "VIZON", "CREAM", "OAK", "BONE", 
    "TAUPE", "MOKA", "NOCE", "SAND"
]

def metin_temizle_ve_normalize_et(ham_metin):
    if pd.isna(ham_metin):
        return ""
    
    # 1. Büyük Harfe Çevir
    metin = str(ham_metin).upper()
    metin = metin.replace("İ", "I").replace("ı", "I")
    
    # 2. Ebat Bilgisini Sil (Örn: 60X120)
    metin = re.sub(r'\b\d+\s*[X]\s*\d+\b', '', metin)
    
    # 3. Yüzey Karakterlerini Sil
    for yuzey in SILINECEK_YUZEYLER:
        metin = metin.replace(yuzey, "")
        
    # 4. Renk Ayrıştırma (Bitişik yazılan renkleri ayır)
    for renk in RENKLER:
        if renk in metin:
            pattern = f"(?<=[A-Z])({renk})"
            metin = re.sub(pattern, r' \1', metin)
    
    # 5. Temizlik
    metin = re.sub(r'\s+', ' ', metin).strip()
    return metin

def karsilastirma_baslat(dosya_a_yolu, dosya_b_yolu):
    """
    GUI tarafından çağrılacak ana fonksiyon.
    Sonuç mesajı döner.
    """
    try:
        # Dosyaları Oku
        df_urun_gami = pd.read_excel(dosya_a_yolu) # XLSX okuyacak şekilde ayarladım
        df_disk_envanteri = pd.read_excel(dosya_b_yolu)
        
        # Veri İşleme
        df_urun_gami['Normalize_Ad'] = df_urun_gami['Ürün'].apply(metin_temizle_ve_normalize_et)
        df_disk_envanteri['Normalize_Ad'] = df_disk_envanteri['Orijinal_Ad'].apply(metin_temizle_ve_normalize_et)
        
        aktif_urun_listesi = df_urun_gami[df_urun_gami['Normalize_Ad'] != ""]
        disk_listesi_set = set(df_disk_envanteri['Normalize_Ad'].tolist())
        
        # Karşılaştırma
        eksik_urunler = []
        for index, satir in aktif_urun_listesi.iterrows():
            normalize_isim = satir['Normalize_Ad']
            orijinal_isim = satir['Ürün']
            
            if normalize_isim not in disk_listesi_set:
                eksik_urunler.append({
                    "Sıra No": index + 1,
                    "Ürün Gamı Adı (A)": orijinal_isim,
                    "Aranan Normalize İsim": normalize_isim,
                    "Durum": "Diskte Yok"
                })
        
        # Raporlama
        rapor_adi = "Eksik_Urunler_Raporu.xlsx"
        if eksik_urunler:
            df_sonuc = pd.DataFrame(eksik_urunler)
            df_sonuc.to_excel(rapor_adi, index=False)
            return f"İşlem Başarılı!\nTopl. Ürün Gamı: {len(aktif_urun_listesi)}\nEksik Ürün Sayısı: {len(df_sonuc)}\nRapor '{rapor_adi}' olarak kaydedildi."
        else:
            return "Harika! Hiçbir eksik ürün bulunamadı. Tüm ürün gamı diskte mevcut."

    except Exception as e:
        return f"Hata oluştu: {str(e)}"

# Test için (Doğrudan çalıştırılırsa)
if __name__ == "__main__":
    # Test amaçlı dosya yolları
    print(karsilastirma_baslat("25.11.27 Ürün Gamı.xlsx", "Guncel_Disk_Envanteri.xlsx"))