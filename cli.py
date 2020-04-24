import logging
import os
import time
from collections import namedtuple
import asyncio

import numpy as np
import click
import six  # bug with pyinstaller without this
from pytictoc import TicToc

from translation import get_pinyin, get_all_phrase_translations, contains_chinese, get_translate_fn
from ocr import make_default_ocr
from ocr.detection.utils import resize


def _awaitable(f, *args):
    return asyncio.get_running_loop().run_in_executor(None, f, *args)


async def get_ocr_results(ocr, image, max_height):
    """Runs OCR on a given image and returns the recognized text,
    text as pinyin, position and dictionary translations."""
    tic_toc = TicToc()

    # Determine the ratio from detection coords to image coords.
    # Downscale if the hight exceeds the max height.
    image_to_screen = [1, 1]
    if image.shape[0] > max_height:
        tic_toc.tic()
        orig_shape = image.shape
        image = resize(image, height=max_height)
        image_to_screen = [
            orig_shape[0] / image.shape[0],
            orig_shape[1] / image.shape[1]
        ]
        tic_toc.toc("Downscaled image in")

    # Detect sentences in image
    tic_toc.tic()
    print("Image shape:", image.shape, "dtype", image.dtype)
    result, _ = await _awaitable(ocr.run, image)
    sentences = [
        {"text": r[1], "position": r[0][:2]}
        for r in result.values()
    ]
    tic_toc.toc("OCR in", restart=True)

    # Translate the detected sentences and store results
    results = []
    for sentence in sentences:
        orig_text = sentence["text"]
        if contains_chinese(orig_text):
            pinyin_text = get_pinyin(orig_text)
            translations = get_all_phrase_translations(orig_text)
            translation_text = "\n".join(
                ["%s: %s" % (t[0], ", ".join(t[1])) for t in translations])

            position = (
                int(sentence["position"][0] * image_to_screen[0]),
                int((sentence["position"][1] * image_to_screen[1]) + 20)
            )

            results.append({
                "text": orig_text,
                "position": position,
                "pinyin_text": pinyin_text,
                "translation_text": translation_text
            })

    tic_toc.toc("Translate in")

    return results

BaseArgs = namedtuple("BaseArgs", ["ocr", "max_height"])


@click.group()
@click.option("--max-height", type=click.INT, default=1440,
              help="Height that images will be resized to when exceeded.")
@click.option("--detector-model-path", type=click.Path(exists=True, dir_okay=False), default=os.path.join("data", "cptn.onnx"),
              help="File path to the detector network onnx.")
@click.option("--recognizer-model-path", type=click.Path(exists=True, dir_okay=False), default=os.path.join("data", "crnn.onnx"),
              help="File path to the recognizer network onnx.")
@click.option("--alphabet-path", type=click.Path(exists=True, dir_okay=False), default=os.path.join("data", "alphabet.pkl"),
              help="File path to the pickled alphabet.")
@click.option("--execution-providers", multiple=True, default=["DmlExecutionProvider"],
              help="ONNX runtime execution providers to use for running the networks.")
@click.pass_context
def main(ctx, max_height, detector_model_path, recognizer_model_path, alphabet_path, execution_providers):
    ctx.obj = BaseArgs(max_height=max_height, ocr=make_default_ocr(
        detector_model_path=detector_model_path,
        recognizer_model_path=recognizer_model_path,
        alphabet_path=alphabet_path,
        execution_providers=execution_providers
    ))


@main.command()
@click.option("--host", type=click.STRING, default="127.0.0.1")
@click.option("--port", type=click.INT, default=8081)
@click.option("--image-max-size", type=click.INT, default=1024*1024*128)
@click.pass_obj
def server(ctx, host, port, image_max_size):
    """Runs an http server that can receive images and run OCR on them."""
    from aiohttp import web
    from imageio import imread

    routes = web.RouteTableDef()

    @routes.post("/")
    async def ocr_translate(request):
        tic_toc = TicToc()

        # Read the image from the web request
        tic_toc.tic()
        image_bytes = await request.read()
        image = imread(image_bytes, pilmode="RGB")
        tic_toc.toc("Read image in")

        results = await get_ocr_results(ctx.ocr, image, ctx.max_height)

        return web.json_response({
            "results": results
        })

    app = web.Application(client_max_size=image_max_size)
    app.add_routes(routes)
    web.run_app(app, host=host, port=port)


def get_screenshot(sct, monitor):
    """Takes a screenshot on the given monitor
    and returns it as a numpy array."""
    from PIL import Image
    image = sct.grab(monitor)
    image = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX")
    image = image.resize((image.size[0], image.size[1]))
    image = np.asarray(image.convert("RGB"))
    print(image.shape)
    return image


def get_text_fn(google_trans):
    """Returns a function that constructs the text and tooltip
    given OCR results."""
    if google_trans:
        translate = get_translate_fn()

        def text_from_result(results):
            return translate(results["text"]), results["translation_text"]
    else:
        def text_from_result(results):
            return results["pinyin_text"], results["translation_text"]

    return text_from_result


@main.command()
@click.option("--toggle-key", type=click.STRING, default="F8",
              help="Hotkey to use for toggling the overlay.")
@click.option("--monitor-id", type=click.INT, default=1,
              help="Id of the monitor to capture from.")
@click.option("--monitor-bounds", nargs=4, type=click.INT, default=None,
              help="Pixel-bounds to capture from as (left, top, width, height).")
@click.option("--google-trans/--no-google-trans", default=False,
              help="Whether to google-translate the detected text.")
@click.pass_obj
def ui(ctx, toggle_key, monitor_id, monitor_bounds, google_trans):
    """Displays an overlay UI and translates within it."""
    import keyboard
    import mss
    import sys
    import signal
    from ui.overlay import LabelManager
    from threading import Thread

    label_manager = LabelManager(toggle_input_transparency=True)

    get_text = get_text_fn(google_trans)

    stop = False

    def _loop():
        sct = mss.mss()
        tic_toc = TicToc()

        monitor = sct.monitors[monitor_id]

        print("Orig monitor:", monitor)

        if monitor_bounds is not None and len(monitor_bounds) == 4:
            monitor["left"] += monitor_bounds[0]
            monitor["top"] += monitor_bounds[1]
            monitor["width"] = monitor_bounds[2]
            monitor["height"] = monitor_bounds[3]

        print("Monitor:", monitor)

        time.sleep(1)

        print("Ready")

        image = None
        while not stop:
            monitor = label_manager.get_monitor()

            keyboard.wait(toggle_key)

            print("Getting screenshot")
            image = get_screenshot(sct, monitor)

            print("Processing")
            results = asyncio.run(get_ocr_results(
                ctx.ocr, image, ctx.max_height))

            print("Updating UI")
            for result in results:
                result["position"] = (
                    result["position"][0],
                    result["position"][1]
                )

                text, tooltip = get_text(result)

                label_manager.add(result["position"], text, tooltip)

            print("Waiting")
            keyboard.wait(toggle_key)

            print("Resetting")
            label_manager.reset()
            print("Reset")

            time.sleep(0.1)

    thread = Thread(target=_loop, daemon=True)
    thread.start()
    exit_code = label_manager.start()
    print("Done")
    stop = True
    print("Exiting")
    sys.exit(exit_code)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
