import pandas as pd
from pathlib import Path

# --- AYARLAR ---
GIRIS_DOSYASI = "Kapsamli_Stok_Analizi_V3.xlsx"
CIKIS_DOSYASI = "Final_Aksiyon_Plani.xlsx"

def kesisim_analizi_yap():
    print(f"🔍 '{GIRIS_DOSYASI}' dosyası analiz ediliyor...")
    
    try:
        # 1. Excel'den İlgili Sayfaları Oku
        # Not: Sayfa isimleri V3 kodundaki kısaltmalara göre belirlendi.
        # Eğer sayfa ismini değiştirdiysen burayı güncellemelisin.
        try:
            df_katalog_eksik = pd.read_excel(GIRIS_DOSYASI, sheet_name="Katalog_Ca_EKSIKLER")
            df_liste_eksik = pd.read_excel(GIRIS_DOSYASI, sheet_name="Urun_Liste_EKSIKLER")
        except ValueError as e:
            print(f"❌ HATA: Sayfa isimleri bulunamadı. Lütfen Excel dosyasındaki sekme adlarını kontrol et.")
            print(f"Detay: {e}")
            return

        if df_katalog_eksik.empty and df_liste_eksik.empty:
            print("✅ Her iki listede de eksik yok! Harika.")
            return

        # 2. Anahtarları (KEY) Kümeye Çevir
        # Set (Küme) yapısı matematikteki kesişim işlemleri için en hızlı yoldur.
        keys_katalog = set(df_katalog_eksik['KEY'])
        keys_liste = set(df_liste_eksik['KEY'])

        # --- A) KESİŞİM (ORTAK EKSİKLER) ---
        # Her iki tarafta da görseli olmayanlar (EN KRİTİK LİSTE)
        ortak_keys = keys_katalog.intersection(keys_liste)
        
        # --- B) SADECE KATALOGDA EKSİK OLANLAR ---
        sadece_katalog_keys = keys_katalog - keys_liste
        
        # --- C) SADECE ÜRÜN LİSTESİNDE EKSİK OLANLAR ---
        sadece_liste_keys = keys_liste - keys_katalog

        print(f"\n📊 ANALİZ SONUCU:")
        print(f"   🔴 ACİL (İki listede de yok): {len(ortak_keys)} Ürün")
        print(f"   🟠 Katalog Hatası Olabilir  : {len(sadece_katalog_keys)} Ürün")
        print(f"   🟡 Liste Hatası Olabilir    : {len(sadece_liste_keys)} Ürün")

        # 3. Raporu Oluştur (Detaylı Verilerle)
        # Sadece KEY değil, ürünün orijinal adını da görmek istersin, o yüzden merge yapıyoruz.
        
        # Ortak Eksikler Detayı
        df_ortak = df_katalog_eksik[df_katalog_eksik['KEY'].isin(ortak_keys)].copy()
        df_ortak['Durum'] = "ACİL - İki Listede de Eksik"
        
        # Sadece Katalog Detayı
        df_sadece_katalog = df_katalog_eksik[df_katalog_eksik['KEY'].isin(sadece_katalog_keys)].copy()
        df_sadece_katalog['Durum'] = "Katalogda Var, Listede Yok (Görsel Eksik)"
        
        # Sadece Liste Detayı
        df_sadece_liste = df_liste_eksik[df_liste_eksik['KEY'].isin(sadece_liste_keys)].copy()
        df_sadece_liste['Durum'] = "Listede Var, Katalogda Yok (Görsel Eksik)"

        # 4. Kaydet
        with pd.ExcelWriter(CIKIS_DOSYASI, engine='openpyxl') as writer:
            if not df_ortak.empty:
                df_ortak.to_excel(writer, sheet_name='1-ACIL_CEKIM_LISTESI', index=False)
            
            if not df_sadece_katalog.empty:
                df_sadece_katalog.to_excel(writer, sheet_name='2-Sadece_Katalog_Eksik', index=False)
                
            if not df_sadece_liste.empty:
                df_sadece_liste.to_excel(writer, sheet_name='3-Sadece_Liste_Eksik', index=False)
                
        print(f"\n✅ ÇAPRAZ KONTROL RAPORU OLUŞTURULDU: {CIKIS_DOSYASI}")
        print("   -> '1-ACIL_CEKIM_LISTESI' sekmesindeki ürünler prodüksiyon için önceliklidir.")

    except FileNotFoundError:
        print(f"❌ HATA: '{GIRIS_DOSYASI}' dosyası aynı klasörde bulunamadı.")
    except Exception as e:
        print(f"❌ Beklenmeyen bir hata oluştu: {e}")

if __name__ == "__main__":
    kesisim_analizi_yap()