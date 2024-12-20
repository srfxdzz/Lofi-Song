from googleapiclient.discovery import build
YOUTUBE_API_KEY = 'AIzaSyBp_u_E0-xaDwSNJk4saicZD32OiscgQFY'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

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
    with open(file_name, "+a") as configfile:
        for playlist_id, video_links in data.items():
            configfile.write(f"[{playlist_id}]\n")
            for link in video_links:
                configfile.write(f"{link}\n")

# Playlist IDs to fetch videos from
playlist_ids = ["PL9bw4S5ePsEFSSvWQ2ukqHoxC4YvN4gsJ", "PLizEqzsgQvPp8kTHGV9o6bjkz6t0TJtjm"]

# Collect video links for all playlists
playlist_data = {}
for playlist_id in playlist_ids:
    playlist_data[playlist_id] = get_playlist_videos(playlist_id)

# Save the playlist data to a .config file
config_file_name = "playlists2.config"
save_to_config_file(config_file_name, playlist_data)

print(f"Data saved to {config_file_name}")
