"""
DROPBOX_ACCESS_TOKEN = "sl.u.AFoR7cSpWwVfm9wKObEVg5mi9JtGq7agokYXdx1FqKu4fxI1wDXnysy_MQSPku9ddk3vkLJwGlmX2FpTu2HScgmXUDUOcofACbcBJVcSzhghS7Tu0fE2n1N2C5KGzW8CpG7vgrinQ0G-1eUg8up8pvr4U3-GH8SmOD5gysjj5nsZfl1udao6QCEeLUsbh-wAdNxR_3HP0OwZyQSR25Obr59cz9jXjqKIZZBIk6I0YC9sl6siFnlJ4fZnEpXkOnNGCwfSzFSZX7dHBCXcJ1v06_2YFSmoRobeRGWNPvIyM0TNGvSO1QUpad278ZkcO_gQN-1cMcbfaMKfxfLhJZWjAIVEAwrFc8z60_fNKdmoYq1oRjqWLn7IzI0JguXa_tB87rHza0YWvbgLwIAZqQYcQf7KeeXelP1xm4DkEB_gWD9UTjvyvv2W-e4ec9Tm2cP3xXJt0S_ic5R0vRUNOu83JeKFOh0GvdVoUAZpmnyeK_gnmpvT_E88WjDN1FjyYy_9EwHYyJxc1thHPDiag_8LHXJNnz5mDlD8tDinyRdrODMc6rpiipXyjiL-DvPA9a2Njr491BQ4aVc-9tLolNPaG5Z39GRLRhxwc9XUHq1F64HHLk-sVFVRNaqmqzgn0QFnPY7y0zEYMvi_JB_0HGrNCqdjHKTJVP2M3BeHK-8Gc11rdbdkxgj6bSveRpvYdVzVn-_SpAUNOwbtCBLEINA1ZAl9ksVdl9_xfSayYsoGW4kzcEEdx5eHe9w21qV1ymO-oI29cRHsDciegbQqjMoo1dH9ezwzhM7Q1v5FxpF0CCCD6-gJGlIzNJrl3NYe_MFl_bGcYbiTcpYAzkuH13PTfQkhwftmyLYZs8j5Mqs8Ha5QuRKrypp3Iua8YxanBx-EGtXRTBvCI1t-D8cRJhbNLGGuPOuH61O9BDr6PK0erTMp0SN4XygH-r6rgYlroaRw4a-c7F1oruKdcToBetDCddcWeGTSKZ27KYQTvq-bshvCw0hvOsJsCmDGB0pkOM527hQ4JlzUCtgN9f9ZEOcGoTVa0D6ohj90DUT5r76qMdAx7a2DdZRD974Ciuorr-PCvYRWcFg1i_chwBGp7MaSGeVHgK2auRPeK4-0L6SV3peXEIPBWKN1GvZD3QenJqLQrGfWeJDUdjJ8RSfexgO_3AYRog1tT4iljsgPT_qrEu6MfiaTQWLM8jBBfk9NyloUuEpjQkT9c1q64PxIN-n8IOiMf-ewKLFHtonAR6KorKDolDHUNfeejDv23PKnssNPrFCwZ3TWnoDv0GwnVceM1SN8Ejgji3awmSoq--n9nAXWIRzjfFqrhLu0es3N5dXlzyGqjQeh8sJt0HZ1NkaHdCIgTdDpYvG35HiT3bAKc_CmaM6zTk0qT6ztBWsLZ8hkPy5S_ds1mRsFRwGY_50z8YZfy7gTJaRQ-ND1egsKk-JsrA"
"""


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
    app.run(debug=True)
