import pandas as pd
from pathlib import Path
from tqdm import tqdm
import ollama
import time

# =============================================================================
# ⚙️ AYARLAR
# =============================================================================
RAPOR_ADI = "AI_Ozetli_Disk_Envanteri.xlsx"

# Bilgisayarında yüklü olan modelin tam adı (Terminal çıktısından aldık)
MODEL_NAME = "llama3.2-vision:latest" 

class AIEnvanterAnalizcisi:
    def __init__(self, excel_path, output_folder, api_key=None):
        # api_key parametresi artık kullanılmıyor ama uyumluluk için duruyor
        self.excel_path = Path(excel_path)
        self.output_folder = Path(output_folder)
        self.check_ollama()

    def check_ollama(self):
        """Ollama'nın çalışıp çalışmadığını kontrol eder."""
        try:
            # Basit bir test sorgusu gönder
            ollama.list()
            print(f"✅ Ollama bağlantısı başarılı. Model: {MODEL_NAME}")
        except Exception as e:
            print(f"⚠️ Ollama'ya bağlanılamadı: {e}")
            print("Lütfen Ollama uygulamasının açık olduğundan emin olun.")

    def generate_summary(self, row):
        """
        Yerel AI (Llama 3.2) kullanarak ürün özeti oluşturur.
        """
        try:
            urun = str(row.get('Orijinal_Ad', '')).strip()
            ebat = str(row.get('Ebat', '')).strip()
            yuzey = str(row.get('Yuzey', '')).strip()
            sayi = str(row.get('Gorsel_Sayisi', '0')).strip()
            
            # Prompt (İstem) - AI'ya ne yapması gerektiğini söylüyoruz
            prompt = (
                f"Ürün: {urun}, Ebat: {ebat}, Yüzey: {yuzey}, Görsel Sayısı: {sayi}. "
                "Bu bilgileri kullanarak bilgileri açıklayan kısa metin oluştur. "
            )
            
            # Ollama'ya sor
            response = ollama.chat(model=MODEL_NAME, messages=[
                {'role': 'user', 'content': prompt},
            ])
            
            # Cevabı al
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"AI Hatası: {str(e)[:50]}"

    def baslat(self):
        print(f"📊 Excel Verisi Analiz Ediliyor (Yerel AI - {MODEL_NAME}): {self.excel_path.name}")

        if not self.excel_path.exists():
            print("❌ Excel dosyası bulunamadı!")
            return

        try:
            # Excel dosyasını oku
            df = pd.read_excel(self.excel_path)
            
            print(f"Toplam {len(df)} kayıt işleniyor. Yerel AI çalışıyor...")
            print("Not: Bu işlem bilgisayarınızın hızına bağlıdır.")
            
            # İlerleme çubuğu ile işlem
            tqdm.pandas(desc="AI Düşünüyor")
            df['AI_Tanitim_Ozeti'] = df.progress_apply(self.generate_summary, axis=1)

            # Raporu kaydet
            output_path = self.output_folder / RAPOR_ADI
            df.to_excel(output_path, index=False)
            
            print(f"\n✅ YEREL AI ÖZETLİ RAPOR HAZIR: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"❌ İşlem sırasında hata oluştu: {e}")
            return None
    