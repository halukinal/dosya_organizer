import pandas as pd
from pathlib import Path
from tqdm import tqdm
import google.generativeai as genai
import os
import time

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================
RAPOR_ADI = "AI_Ozetli_Disk_Envanteri.xlsx"

class AIEnvanterAnalizcisi:
    def __init__(self, excel_path, output_folder, api_key):
        self.excel_path = Path(excel_path)
        self.output_folder = Path(output_folder)
        
        # 1. Önce parametre olarak gelen anahtarı dene
        self.api_key = api_key
        
        # 2. Eğer parametre boşsa, yerel dosyadan ("google_api_key.txt") okumayı dene
        if not self.api_key:
            self.api_key = self._load_key_from_file()
            
        self.setup_ai()

    def _load_key_from_file(self):
        """Yerel dosyadan API anahtarını okur."""
        try:
            key_file = Path("google_api_key.txt")
            if key_file.exists():
                print("🔑 API Anahtarı 'google_api_key.txt' dosyasından alındı.")
                return key_file.read_text("utf-8").strip()
        except Exception:
            pass
        return None

    def setup_ai(self):
        """Google Gemini API bağlantısını kurar."""
        if not self.api_key:
            raise ValueError("API Anahtarı bulunamadı! Lütfen arayüzden girin veya 'google_api_key.txt' dosyası oluşturun.")
        
        genai.configure(api_key=self.api_key)
        # Hızlı ve ekonomik model: Flash
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_summary(self, row):
        """
        Satırdaki verileri kullanarak Gemini ile kısa bir özet metni oluşturur.
        """
        try:
            urun = str(row.get('Orijinal_Ad', '')).strip()
            ebat = str(row.get('Ebat', '')).strip()
            yuzey = str(row.get('Yuzey', '')).strip()
            sayi = str(row.get('Gorsel_Sayisi', '0')).strip()
            
            prompt = (
                f"Ürün: {urun}, Ebat: {ebat}, Yüzey: {yuzey}, Görsel Sayısı: {sayi}. "
                "Bu ürün bilgilerini kullanarak, bir katalogda kullanılabilecek, "
                "ilgi çekici ve öz ama profesyonel, tek cümlelik kısa bir Türkçe tanıtım/özet yazısı yaz. "
                "Örneğin: '60x120 ebatlarında, mat yüzeyli şık Abaco Bambu serisi, 12 görsel ile stoklarda.'"
            )
            
            # API çağrısı (Hız sınırı hatası almamak için kısa bekleme eklenebilir)
            response = self.model.generate_content(prompt)
            time.sleep(1) # Rate limit önlemi
            return response.text.strip()
        except Exception as e:
            return f"AI Özet Hatası: {str(e)[:50]}"

    def baslat(self):
        print(f"📊 Excel Verisi Analiz Ediliyor: {self.excel_path.name}")

        if not self.excel_path.exists():
            print("❌ Excel dosyası bulunamadı!")
            return

        try:
            # Excel dosyasını oku
            df = pd.read_excel(self.excel_path)
            
            print(f"Toplam {len(df)} kayıt işleniyor. AI özetleri oluşturuluyor...")
            print("Not: Bu işlem API hızına bağlı olarak zaman alabilir.")

            # Özet sütunu ekle - Progress bar ile
            tqdm.pandas(desc="AI Özetliyor")
            df['AI_Tanitim_Ozeti'] = df.progress_apply(self.generate_summary, axis=1)

            # Raporu kaydet
            output_path = self.output_folder / RAPOR_ADI
            df.to_excel(output_path, index=False)
            
            print(f"\n✅ AI ÖZETLİ RAPOR HAZIRLANDI: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"❌ İşlem sırasında hata oluştu: {e}")
            return None