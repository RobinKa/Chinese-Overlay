from time import time
import random
import pickle as pkl
from PIL import Image
import cv2
import numpy as np
import onnxruntime as rt


def get_alphabet(path):
    alphabet_list = pkl.load(open(path, 'rb'))
    alphabet = [ord(ch) for ch in alphabet_list]
    return alphabet


def pil_to_numpy(img):
    img = np.asarray(img, dtype=np.float32) / 255
    if len(img.shape) == 3:
        img = img.transpose(2, 0, 1)
    elif len(img.shape) == 2:
        img = np.expand_dims(img, 0)
    return img


def resize_normalize(img, size, interpolation=Image.LANCZOS, is_test=True):
    w, h = size
    w0 = img.size[0]
    h0 = img.size[1]
    if w <= (w0 / h0 * h):
        img = img.resize(size, interpolation)
        img = pil_to_numpy(img)
        img = (img - 0.5) / 0.5
    else:
        w_real = int(w0 / h0 * h)
        img = img.resize((w_real, h), interpolation)
        img = pil_to_numpy(img)
        img = (img - 0.5) / 0.5
        tmp = np.zeros_like(img)
        start = random.randint(0, w - w_real - 1)
        if is_test:
            start = 0
        tmp[:, :, start:start + w_real] = img
        img = tmp
    return img


class StringLabelConverter(object):
    def __init__(self, alphabet, ignore_case=False):
        self._ignore_case = ignore_case
        if self._ignore_case:
            alphabet = alphabet.lower()
        self.alphabet = alphabet + '_'  # for `-1` index

        self.dict = {}
        for i, char in enumerate(alphabet):
            # NOTE: 0 is reserved for 'blank' required by wrap_ctc
            self.dict[char] = i + 1

    def decode(self, t, length, raw=False):
        if raw:
            return ''.join([self.alphabet[i - 1] for i in t])
        else:
            char_list = []
            for i in range(length):
                if t[i] != 0 and (not (i > 0 and t[i - 1] == t[i])):
                    char_list.append(self.alphabet[t[i] - 1])
            return ''.join(char_list)


class CRNNRecognizer:
    """Recognize characters within areas of potential text."""

    def __init__(self, model_path, alphabet_path, execution_providers):
        alphabet_unicode = get_alphabet(alphabet_path)
        self.alphabet = ''.join([chr(uni) for uni in alphabet_unicode])
        self.nclass = len(self.alphabet) + 1
        session_opts = rt.SessionOptions()
        session_opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_opts.enable_mem_pattern = False
        self.session = rt.InferenceSession(model_path, session_opts)
        self.session.set_providers(execution_providers)
        self.converter = StringLabelConverter(self.alphabet)

    def recognize(self, img):
        h, w = img.shape[:2]
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        image = Image.fromarray(img)
        image = resize_normalize(image, (int(w / h * 32), 32))
        image = np.expand_dims(image, 0)

        preds = self.session.run(None, {"images": image})

        preds = np.array(preds, np.float32)
        preds = np.argmax(preds, axis=-1)
        preds = preds.transpose(1, 0, 2).reshape(-1)

        preds_size = preds.shape[0]

        txt = self.converter.decode(preds, preds_size, raw=False).strip()

        return txt
