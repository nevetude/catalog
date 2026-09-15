import gzip
import os
from datetime import datetime, timezone, timedelta
import requests
import urllib3

# Отключаем предупреждения о проверке SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_tmdb_export():
    # Проверяем даты: сначала сегодня, потом вчера, потом позавчера
    for days_ago in range(0, 3):
        date_obj = datetime.now(timezone.utc) - timedelta(days=days_ago)
        date_str = date_obj.strftime("%m_%d_%Y")
        
        url = f"https://files.tmdb.org/p/exports/movie_ids_{date_str}.json.gz"
        output_filename = f"tmdb_movies_{date_str}.ndjson"
        
        print(f"Пробуем скачать файл за {date_str}...")
        
        response = requests.get(url, stream=True, verify=False)
        
        if response.status_code == 200:
            # Проверяем, что нам вернули архив, а не HTML/XML ошибку
            content_type = response.headers.get('Content-Type', '')
            if 'html' in content_type or 'xml' in content_type:
                print(f"Файл за {date_str} на сервере ещё не готов или уже удалён (ошибка Access Denied).")
                continue
                
            print(f"Успешно! Файл найден. Начинаем запись в NDJSON...")
            try:
                with open(output_filename, "w", encoding="utf-8") as out_file:
                    with gzip.GzipFile(fileobj=response.raw) as f:
                        for line in f:
                            out_file.write(line.decode("utf-8"))
                print(f"Готово! Все фильмы сохранены в файл: {os.path.abspath(output_filename)}")
                return # Выходим из функции, так как файл успешно скачан
            except Exception as e:
                print(f"Ошибка при распаковке архива: {e}")
                if os.path.exists(output_filename):
                    os.remove(output_filename)
        else:
            print(f"Сервер вернул статус код: {response.status_code}")
            
    print("К сожалению, не удалось найти доступный файл за последние 3 дня.")

if __name__ == "__main__":
    download_tmdb_export()