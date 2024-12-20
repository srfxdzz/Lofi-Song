from flask import Flask, request, render_template, redirect, url_for
from googleapiclient.discovery import build
import os

app = Flask(__name__)

YOUTUBE_API_KEY = 'AIzaSyBp_u_E0-xaDwSNJk4saicZD32OiscgQFY'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
CONFIG_FILE_NAME = "playlists.config"

def get_playlist_videos(playlist_id):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

    video_links = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            video_id = item['snippet']['resourceId']['videoId']
            video_links.append(f"https://www.youtube.com/watch?v={video_id}")

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return video_links

def save_to_config_file(file_name, data):
    with open(file_name, "w") as configfile:
        for playlist_id, video_links in data.items():
            configfile.write(f"[{playlist_id}]\n")
            for link in video_links:
                configfile.write(f"{link}\n")

def load_config_file(file_name):
    if not os.path.exists(file_name):
        return {}

    data = {}
    with open(file_name, "r") as configfile:
        lines = configfile.readlines()
        current_playlist = None
        for line in lines:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_playlist = line[1:-1]
                data[current_playlist] = []
            elif current_playlist and line:
                data[current_playlist].append(line)
    return data


