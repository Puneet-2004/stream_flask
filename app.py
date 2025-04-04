from flask import Flask, render_template, Response, jsonify
import cv2
import time
import threading
import os
import dropbox
from dotenv import load_dotenv
import os

load_dotenv()
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")


app = Flask(__name__)

# Global variables
camera = None
streaming = False
recording_thread = None


# Duration (in seconds) for each video segment
SEGMENT_DURATION = 10

def open_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

def close_camera():
    global camera
    if camera:
        camera.release()
        camera = None

def record_and_upload():
    """
    Records video in SEGMENT_DURATION chunks and uploads each segment to Dropbox in real-time.
    After upload, the local segment file is removed.
    """
    global streaming, camera
    while streaming:
        # Create a unique filename using the current timestamp
        segment_filename = f"recorded_{int(time.time())}.avi"
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(segment_filename, fourcc, 20.0, (640, 480))
        
        start_time = time.time()
        while streaming and (time.time() - start_time < SEGMENT_DURATION):
            ret, frame = camera.read()
            if not ret:
                break
            out.write(frame)
        out.release()
        
        # Upload the recorded segment to Dropbox
        upload_to_dropbox(segment_filename)
        
        # Remove the local file after upload
        if os.path.exists(segment_filename):
            os.remove(segment_filename)
        
        # Small pause before starting next segment
        time.sleep(0.5)

def upload_to_dropbox(file_path):
    """Uploads the given file to Dropbox (overwriting any file with the same name)."""
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), f"/{os.path.basename(file_path)}", mode=dropbox.files.WriteMode("overwrite"))
    print(f"Uploaded {file_path} to Dropbox")

@app.route('/')
def index():
    return render_template('index.html', state=streaming)

@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    """
    Toggles video streaming ON/OFF.
    When ON, the camera is opened and a background thread starts recording segments.
    When OFF, streaming stops and the camera is released.
    """
    global streaming, recording_thread
    streaming = not streaming
    if streaming:
        open_camera()
        recording_thread = threading.Thread(target=record_and_upload)
        recording_thread.start()
    else:
        # Stop streaming and wait for the recording thread to finish
        streaming = False
        if recording_thread is not None:
            recording_thread.join()
        close_camera()
    return jsonify({"state": streaming})

@app.route('/video_feed')
def video_feed():
    """
    Provides live MJPEG streaming for display purposes.
    (This is optional and independent of the recording/upload process.)
    """
    def generate_frames():
        global camera
        while streaming:
            ret, frame = camera.read()
            if not ret:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)
