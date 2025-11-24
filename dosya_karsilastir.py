import re

def parse_srt(file_path):
    """
    Bir SRT dosyasını okur ve yalnızca konuşma metinlerini birleştirerek döndürür.
    Zaman damgaları, sıra numaraları ve boş satırlar atlanır.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Zaman damgalarını, satır numaralarını ve HTML etiketlerini temizle
            lines = content.splitlines()
            text_lines = [line for line in lines if not re.match(r'^\d+$', line.strip()) and '-->' not in line and line.strip()]
            return ' '.join(text_lines)
    except FileNotFoundError:
        return f"Hata: '{file_path}' dosyası bulunamadı."
    except Exception as e:
        return f"Dosya okunurken bir hata oluştu: {e}"

def levenshtein_distance(s1, s2):
    """
    İki metin arasındaki Levenshtein mesafesini hesaplar.
    Bu, bir metni diğerine dönüştürmek için gereken minimum tek karakterli
    düzenleme (ekleme, silme veya değiştirme) sayısıdır.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def compare_files_percentage(file1_path, file2_path):
    """
    İki dosyanın metin içeriğini karşılaştırır ve aralarındaki
    farklılık ve benzerlik yüzdesini döndürür.
    """
    text1 = parse_srt(file1_path)
    text2 = parse_srt(file2_path)

    if "Hata:" in text1 or "Hata:" in text2:
        print(text1)
        print(text2)
        return

    distance = levenshtein_distance(text1, text2)
    max_len = max(len(text1), len(text2))
    
    if max_len == 0:
        print("Dosyalar boş veya metin içeriği bulunamadı.")
        return

    similarity = (1 - (distance / max_len)) * 100
    difference = 100 - similarity

    print(f"'{file1_path}' ve '{file2_path}' dosyaları karşılaştırılıyor...")
    print("-" * 50)
    print(f"Benzerlik Oranı: %{similarity:.2f}")
    print(f"Farklılık Oranı: %{difference:.2f}")
    print("-" * 50)


if __name__ == '__main__':
    # --- DEĞİŞTİRİLECEK ALAN ---
    # Karşılaştırmak istediğiniz dosyaların adlarını buraya yazın.
    # Dosyaların bu betikle aynı klasörde olduğundan emin olun.
    file1 = "/Volumes/Hi_WD/eminrem 2/P7-Satbayev University_KZ/Module 2_Sem 4_Promising methods of underground leaching of minerals. Underground Mining. Trends of underground mining_V/Module 2_Sem 4.srt"
    file2 = "/Volumes/Hi_WD/eminrem 2/P7-Satbayev University_KZ/Module 2_Sem 4_Promising methods of underground leaching of minerals. Underground Mining. Trends of underground mining_V/Complete 2nd lecture.srt"
    # --------------------------
    
    compare_files_percentage(file1, file2)
