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
from flask import Flask, render_template, request, jsonify
import os
import threading
import yt_dlp
import uuid
import random
from queue import Queue
from music import slowedreverb

app = Flask(__name__)

# Directories
UPLOAD_DIR = "uploaded_files"
REVERB_DIR = "slowed_reverbed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REVERB_DIR, exist_ok=True)

# Load playlist configuration
PLAYLIST_FILE = "playlists2.config"
try:
    with open(PLAYLIST_FILE, "r") as f:
        songs = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    songs = []

# Shared state for progress tracking
progress = {}
queue = Queue()

# Function to download YouTube audio
def download_youtube_audio(youtube_link):
    uu = str(uuid.uuid4())
    try:
        with yt_dlp.YoutubeDL({
            'format': 'bestaudio/best',
            'outtmpl': f'uploaded_files/{uu}.%(ext)s',
            "quiet": True,
            "noplaylist": True
        }) as ydl:
            info_dict = ydl.extract_info(youtube_link, download=True)
            song_name = info_dict['title']
        return uu, song_name
    except Exception as e:
        print(f"Error downloading {youtube_link}: {e}")
        return None

# Worker thread function
def worker():
    while True:
        song_url, task_id = queue.get()
        if song_url is None:
            break
        progress[task_id] = f"Downloading: {song_url}"
        result = download_youtube_audio(song_url)
        if result:
            progress[task_id] = f"Downloaded: {result[1]}"
        else:
            progress[task_id] = f"Failed: {song_url}"
        queue.task_done()

# Start worker threads
NUM_THREADS = 4
threads = []
for _ in range(NUM_THREADS):
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    threads.append(thread)
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
    all_files = [f for f in os.listdir(REVERB_DIR) if os.path.isfile(os.path.join(REVERB_DIR, f))]
    if not all_files:
        raise FileNotFoundError("No files found in the upload folder.")
    
    random_file = random.choice(all_files)
    file_path = os.path.join(REVERB_DIR, random_file)
    return file_path, random_file


def stream_video():
    global streaming_process
    current_reverb_path = None

    while True:

        current_reverb_path, current_song_file_name = prepare_next_song()

        
        print(current_reverb_path)

        conn = sqlite3.connect('stream.db')
        cursor = conn.cursor()
        cursor.execute('SELECT key FROM stream_key WHERE id=1')
        data = cursor.fetchone()
        conn.close()

        if not data:
            print("Stream key not set.")
            break

        stream_key = data[0]


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
            streaming_process = subprocess.Popen(ffmpeg_command)

            duration_command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                current_reverb_path
            ]
            song_duration = float(subprocess.check_output(duration_command))
            time.sleep(max(0, song_duration - 5))

            next_song_thread = threading.Thread(target=prepare_next_song)
            next_song_thread.start()

            streaming_process.wait()
            next_song_thread.join()
            current_reverb_path, current_song_file_name = prepare_next_song()

        except Exception as e:
            print(f"Error during streaming: {e}")
            current_reverb_path, current_song_file_name = None, None



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



@app.route('/youtube')
def youtube():
    return render_template('youtube.html', songs=songs)

@app.route('/download_all', methods=['POST'])
def download_all():
    task_id = str(uuid.uuid4())
    for song_url in songs:
        queue.put((song_url, task_id))
    return jsonify({"task_id": task_id})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    return jsonify(progress.get(task_id, "No progress available"))

@app.route('/stop', methods=['POST'])
def stop():
    # Stop all threads by sending None to the queue
    for _ in threads:
        queue.put((None, None))
    return "Stopping downloads", 200

@app.route('/songs')
def list_songs():
    files = os.listdir(UPLOAD_DIR)
    songs = [os.path.join(UPLOAD_DIR, f) for f in files if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
    return render_template('songs.html', songs=songs)

@app.route('/convert')
def convert():
    files = os.listdir(REVERB_DIR)
    songs = [os.path.join(REVERB_DIR, f) for f in files if os.path.isfile(os.path.join(REVERB_DIR, f))]
    
    def convert_worker():
        files = os.listdir(UPLOAD_DIR)
        for file in files:
            
            input_path = os.path.join(UPLOAD_DIR, file)
            output_path = f"slowed_reverbed/{file}.wav"
            slowedreverb(input_path, output_path)
    threading.Thread(target=convert_worker, daemon=True).start()
    return render_template('convert.html', files=songs)

@app.route('/delete', methods=['POST'])
def delete_song():
    file_path = request.form.get("file_path")
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"})



@app.route('/delete_all', methods=['POST'])
def delete_all_songs():
    try:
        files = os.listdir(UPLOAD_DIR)
        for file in files:
            os.remove(os.path.join(UPLOAD_DIR, file))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})




@app.route('/delete_all_converted', methods=['POST'])
def delete_all_converted():
    try:
        converted_files = os.listdir(REVERB_DIR)  # Replace with your converted files directory
        for file in converted_files:
            os.remove(os.path.join(REVERB_DIR, file))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})



if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    port = 5000
    app.run(host='0.0.0.0', port=port, debug=True)
