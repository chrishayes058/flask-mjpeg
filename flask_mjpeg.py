import logging
import os
import threading
import yaml
import argparse

import cv2
from flask import Flask, Response, render_template


LOGLEVEL = os.environ.get("LOGLEVEL", "DEBUG").upper()
logging.basicConfig(level=LOGLEVEL)
log = logging.getLogger(__name__)

output_frame = None
lock = threading.Lock()
image_queue = None

# Initialize a flask object
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("flask_index.html")


def generate():

    global output_frame, lock, image_queue

    while True:
        with lock:
            # Image queue should only have a single queue
            for id_name in image_queue.keys():
                output_frame = image_queue[id_name].get()

                if output_frame is None:
                    continue
                (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
                if not flag:
                    continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + bytearray(encodedImage) + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


def start_server(queue, config, logger):

    global image_queue
    image_queue = queue

    app.run(
        host=config["liveview_url"],
        port=config["liveview_port"],
        debug=True,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "-f",
        "--frame-count",
        type=int,
        default=32,
        help="# of frames used to construct the background model",
    )
    ap.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="location in file system of config for camera",
    )
    args = vars(ap.parse_args())

    config_path = os.path.expanduser(args["config"])
    with open(config_path, "r") as fs:
        configuration = yaml.safe_load(fs)

    # start the Flask app
    app.run(
        host=configuration["liveview_url"],
        port=configuration["liveview_port"],
        debug=True,
        threaded=True,
        use_reloader=False,
    )
