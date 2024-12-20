from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import subprocess
import threading
import os
import random
import requests
import time
from test_1 import *
from dotenv import load_dotenv
from music import *
from down_yt import *

# Load the .env file
load_dotenv()

# Access environment variables
ngrok_token = os.getenv("ngrok_token")
telegram_token = os.getenv("telegram_token")

def run_command(command, shell=False):
    """Runs a shell command and prints output."""
    try:
        result = subprocess.run(command, shell=shell, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(e.stderr)
        return None

def is_package_installed(package_name):
    """Check if a package is installed."""
    try:
        result = subprocess.run(["dpkg", "-l", package_name], check=True, text=True, capture_output=True)
        return package_name in result.stdout
    except subprocess.CalledProcessError:
        return False

def is_ngrok_installed():
    """Check if ngrok is installed."""
    try:
        result = subprocess.run(["ngrok", "version"], check=True, text=True, capture_output=True)
        return "ngrok" in result.stdout
    except FileNotFoundError:
        return False

def send_telegram_message(message, bot_token, chat_id):
    """Send a message to a Telegram bot."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Failed to send Telegram message. Response: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")




# Telegram bot details
bot_token = telegram_token
chat_id = "7132001605"



# Step 2: Check and install ngrok
if is_ngrok_installed():
    print("ngrok is already installed. Skipping installation.")
else:
    print("Downloading ngrok...")
    run_command(["wget", "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"])
    
    print("Extracting ngrok...")
    run_command(["tar", "-xvzf", "ngrok-v3-stable-linux-amd64.tgz"])
    
    print("Moving ngrok to /usr/local/bin...")
    run_command(["mv", "ngrok", "/usr/local/bin/"])

    print("Adding ngrok auth token...")
    auth_token = ngrok_token
    run_command(["ngrok", "config", "add-authtoken", auth_token])

# Step 3: Run ngrok and send the URL
print("Starting ngrok on port 5000...")
ngrok_process = subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

time.sleep(5)

# Get ngrok URL from API
try:
    response = requests.get("http://localhost:4040/api/tunnels")
    if response.status_code == 200:
        tunnels = response.json().get("tunnels", [])
        if tunnels:
            public_url = tunnels[0].get("public_url", "No URL found")
            print(f"ngrok public URL: {public_url}")
            send_telegram_message(f"ngrok public URL: {public_url}", bot_token, chat_id)
        else:
            print("No tunnels found.")
    else:
        print(f"Failed to retrieve ngrok tunnels. Response: {response.text}")
except Exception as e:
    print(f"Error retrieving ngrok URL: {e}")




app = Flask(__name__)
app.secret_key = 'srfxdz'



stream_url = 'rtmp://a.rtmp.youtube.com/live2'
streaming_process = None
def is_streaming():
    """Check if the streaming process is running."""
    global streaming_process
    return streaming_process is not None and streaming_process.poll() is None


def init_db():
    conn = sqlite3.connect('stream.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS stream_key (id INTEGER PRIMARY KEY, key TEXT)''')
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        key = request.form.get('key')
        if key == 'srfxdz':
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Key!", 403
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('stream.db')
    cursor = conn.cursor()

    # Fetch the current stream key
    cursor.execute('SELECT key FROM stream_key WHERE id=1')
    data = cursor.fetchone()
    saved_stream_key = data[0] if data else ''

    # Fetch all saved keys
    cursor.execute('SELECT key FROM stream_key')
    all_keys = [row[0] for row in cursor.fetchall()]
    conn.close()

    if request.method == 'POST':
        stream_key = request.form.get('stream_key')
        conn = sqlite3.connect('stream.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stream_key WHERE id=1')
        cursor.execute('INSERT INTO stream_key (id, key) VALUES (1, ?)', (stream_key,))
        conn.commit()
        conn.close()
        saved_stream_key = stream_key  # Update the displayed key
        return redirect(url_for('dashboard'))

    return render_template(
        'dashboard.html',
        stream_key=saved_stream_key,
        all_keys=all_keys,
        streaming=is_streaming()  # Check if the stream is running
    )


def prepare_next_song():
    """Prepare the next song to stream."""
    try:
        get_song_details = get_random_song()
        song_name = get_song_details[1]
        song_path = get_song_details[0]
        input_path = f"uploaded_files/{song_path}.webm"
        output_path = f"slowed_reverbed/{song_path}.wav"
        slowedreverb(input_path, output_path)
        return song_name, output_path, input_path
    except Exception as e:
        print(f"Error preparing next song: {e}")
        return None, None, None


def stream_video():
    global streaming_process
    current_song = None
    current_reverb_path = None
    input_path = None

    while True:
        # Prepare the first song if not already prepared
        if not current_song:
            current_song, current_reverb_path, input_path = prepare_next_song()
            # If there's an error preparing the song, skip to the next iteration
            if not current_song:
                continue

        conn = sqlite3.connect('stream.db')
        cursor = conn.cursor()
        cursor.execute('SELECT key FROM stream_key WHERE id=1')
        data = cursor.fetchone()
        conn.close()

        if not data:
            print("Stream key not set.")
            break

        stream_key = data[0]

        # Start streaming the current song
        ffmpeg_command = [
            "ffmpeg",
            "-stream_loop", "-1",
            "-i", "dddddd.mp4",
            "-i", current_reverb_path,
            "-r", "30",
            "-shortest",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "500k",
            "-c:a", "aac",
            "-b:a", "96k",
            "-pix_fmt", "yuv420p",
            "-bufsize", "100k",
            "-maxrate", "500k",
            "-f", "flv",
            f'{stream_url}/{stream_key}'
        ]

        try:
            # Start streaming in a subprocess
            streaming_process = subprocess.Popen(ffmpeg_command)

            # Calculate the song duration using ffprobe
            duration_command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                current_reverb_path
            ]
            song_duration = float(subprocess.check_output(duration_command))

            # Start preparing the next song a few seconds before the current song ends
            time.sleep(max(0, song_duration - 5))

            # Prepare the next song in a separate thread
            next_song_thread = threading.Thread(target=prepare_next_song)
            next_song_thread.start()

            # Wait for the current song to finish
            streaming_process.wait()

            # Delete the played song
            if current_reverb_path:
                os.remove(current_reverb_path)
            if input_path:
                os.remove(input_path)

            # Set the next song as the current song
            next_song_thread.join()
            current_song, current_reverb_path, input_path = prepare_next_song()

        except Exception as e:
            print(f"Error during streaming: {e}")
            # Skip to the next song if there's an error
            current_song, current_reverb_path, input_path = None, None, None


@app.route('/start', methods=['POST'])
def start_stream():
    global streaming_process
    if not is_streaming():
        thread = threading.Thread(target=stream_video, daemon=True)
        thread.start()
    return redirect(url_for('dashboard'))


@app.route('/stop', methods=['POST'])
def stop_stream():
    global streaming_process
    if streaming_process is not None:
        streaming_process.terminate()
        streaming_process = None
    return redirect(url_for('dashboard'))


@app.route('/playlist')
def index():
    playlists = load_config_file(CONFIG_FILE_NAME)
    return render_template('index.html', playlists=playlists)


@app.route('/add_playlist', methods=['POST'])
def add_playlist():
    playlist_url = request.form.get('playlist_url')
    if not playlist_url:
        return redirect(url_for('index'))

    # Extract playlist ID from the URL
    if "list=" in playlist_url:
        playlist_id = playlist_url.split("list=")[1].split("&")[0]
    else:
        return redirect(url_for('index'))

    playlists = load_config_file(CONFIG_FILE_NAME)
    if playlist_id not in playlists:
        try:
            playlists[playlist_id] = get_playlist_videos(playlist_id)
            save_to_config_file(CONFIG_FILE_NAME, playlists)
        except Exception as e:
            print(f"Error adding playlist: {e}")
    return redirect(url_for('index'))


@app.route('/delete_playlist/<playlist_id>', methods=['POST'])
def delete_playlist(playlist_id):
    playlists = load_config_file(CONFIG_FILE_NAME)
    if playlist_id in playlists:
        del playlists[playlist_id]
        save_to_config_file(CONFIG_FILE_NAME, playlists)
    return redirect(url_for('index'))


@app.route('/delete_video/<playlist_id>/<video_id>', methods=['POST'])
def delete_video(playlist_id, video_id):
    playlists = load_config_file(CONFIG_FILE_NAME)
    if playlist_id in playlists:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        if video_url in playlists[playlist_id]:
            playlists[playlist_id].remove(video_url)
            # If the playlist becomes empty, remove it
            if not playlists[playlist_id]:
                del playlists[playlist_id]
            save_to_config_file(CONFIG_FILE_NAME, playlists)
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    port = 5000
    app.run(host='0.0.0.0', port=port, debug=True)