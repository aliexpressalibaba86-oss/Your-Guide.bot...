from moviepy.editor import VideoFileClip

def compress_and_save(input_path, output_path):
    # Загружаем видео
    clip = VideoFileClip(input_path)
    
    # Сжимаем:
    # 1. codec="libx264" — стандарт для web-видео
    # 2. audio_codec="aac" — стандарт для звука
    # 3. bitrate="800k" — это значение можно менять (чем меньше, тем меньше файл)
    clip.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac", 
        bitrate="800k",
        threads=2 # Ограничиваем количество потоков для экономии RAM
    )
    clip.close()
    
  
