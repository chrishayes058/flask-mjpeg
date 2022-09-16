import argparse
import asyncio
import os
import yaml
import time
import cv2
import numpy
from queue import Queue
from threading import Thread
import logging
import flask_mjpeg

# setting log level based on enviroment variables
LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
log = logging.getLogger(__name__)
log.setLevel(logging.getLevelName(LOGLEVEL))


def create_videofilestream(
    image_queues: dict, video_file: str, endless: bool = False, device_ids=list
) -> None:
    frame_count = 0
    video_file = os.path.expanduser(video_file)

    log.info(f"Streaming {video_file}")

    if not os.path.exists(video_file):
        log.error(f"{video_file} does not exist!")
        raise FileNotFoundError

    cap = cv2.VideoCapture(video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    while True:
        try:
            if cap.isOpened():
                start = time.time()
                if endless and frame_count == max_frames:
                    log.info(f"Restart video")
                    frame_count = 0
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, img = cap.read()
                frame_count += 1

                if not ret:
                    log.warning(f"No Frame received")
                    if not endless:
                        log.info("was not set to endless")
                    elif frame_count != max_frames:
                        log.info(f"frame count was {frame_count}")
                        log.info(f"max_frames was {max_frames}")
                    continue

                for device in device_ids:
                    image_queues[device].put(img)
                # frame cap
                time.sleep(max(1.0 / (fps) - (time.time() - start), 0))
        except Exception as ex:
            log.error(f"{ex}")
            raise ex

    log.warning(f"Shutting down video stream")



async def main(config: dict) -> None:
    image_queues = {}
    for device in config["device_ids"]:
        image_queues[device] = Queue()

    device_ids = []
    for device_id in config["device_ids"]:
        device_ids.append(device_id)

    thread_stream = Thread(
        target=create_videofilestream,
        args=(image_queues, "Big_Buck_Bunny_1080_10s_1MB.mp4", True, device_ids),
    )
    thread_stream.start()

    """
            image_queue:
            an opencv image stream I can rescale stored in a queue.Queue
            """
    fake_img = numpy.zeros((1, 1))
    back_channel_queues = dict()
    log.debug(f"Using Flask as Liveview Interface")

    t = Thread(
        target=flask_mjpeg.start_server,
        args=(image_queues, config, log),
    )
    t.start()


def cmdline():
    parser = argparse.ArgumentParser(description="Live view lib runner")
    parser.add_argument(
        "-c", "--config", type=str, help="Location of the configuration file."
    )

    class Cmdline:
        pass

    parser.parse_args(namespace=cmdline)

    config_filename = os.path.expanduser(cmdline.config)
    with open(config_filename, "r") as fs:
        configuration = yaml.safe_load(fs)

    if "plugin_type" not in configuration.keys():
        raise KeyError("No stream type specified")
    else:
        loop = asyncio.get_event_loop()
        loop.create_task(main(configuration))
        loop.run_forever()
        loop.close()
        # main(configuration)


if __name__ == "__main__":
    cmdline()
