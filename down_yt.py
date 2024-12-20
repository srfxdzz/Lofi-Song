import yt_dlp
import uuid
import random

def download_youtube_audio(youtube_link):
    uu = str(uuid.uuid4())
    if isDownlaodable(youtube_link):
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'outtmpl': 'uploaded_files/' + uu + '.%(ext)s', "quiet":True, "noplaylist":True}) as ydl:
                info_dict = ydl.extract_info(youtube_link, download=True)
                audio_file = ydl.prepare_filename(info_dict)
                song_name = info_dict['title']
            return uu , song_name
        except Exception as e:
            return None
        


def isDownlaodable(youtube_link):
    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', "quiet":True, "noplaylist":True}) as ydl:
            dur = None
            info_dict = ydl.extract_info(youtube_link, download=False)
            for i in info_dict['formats']:
                if "duration" in i['fragments'][0].keys():
                    dur = i['fragments'][0]["duration"]
                    break

    except Exception as e:
        return False
    if dur <= 600:
        return True
    else:
        return False





songs = open("playlists2.config","r").readlines()


def get_random_song():
    while True:
        song_url = random.choice(songs)
        os = download_youtube_audio(song_url)

        if os == None:
            pass
        else:
            return os


        