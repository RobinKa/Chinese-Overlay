from time import time
import cv2
import numpy as np
from .detection.cptn import CPTNDetector
from .recognition.crnn import CRNNRecognizer


def sort_box(box):
    box = sorted(box, key=lambda x: sum([x[1], x[3], x[5], x[7]]))
    return box


def dump_rotate_image(img, rot_deg, pt1, pt2, pt3, pt4):
    rot_rad = np.radians(rot_deg)
    abs_cos_rot = np.fabs(np.cos(rot_rad))
    abs_sin_rot = np.fabs(np.sin(rot_rad))

    height, width = img.shape[:2]
    height_new = int(width * abs_sin_rot + height * abs_cos_rot)
    width_new = int(height * abs_sin_rot + width * abs_cos_rot)
    rot_mat = cv2.getRotationMatrix2D((width // 2, height // 2), rot_deg, 1)
    rot_mat[0, 2] += (width_new - width) // 2
    rot_mat[1, 2] += (height_new - height) // 2
    image_rotation = cv2.warpAffine(
        img, rot_mat, (width_new, height_new), borderValue=(255, 255, 255))
    pt1 = list(pt1)
    pt3 = list(pt3)

    [[pt1[0]], [pt1[1]]] = np.dot(rot_mat, np.array([[pt1[0]], [pt1[1]], [1]]))
    [[pt3[0]], [pt3[1]]] = np.dot(rot_mat, np.array([[pt3[0]], [pt3[1]], [1]]))
    ydim, xdim = image_rotation.shape[:2]

    return image_rotation[
        max(1, int(pt1[1])): min(ydim - 1, int(pt3[1])),
        max(1, int(pt1[0])): min(xdim - 1, int(pt3[0]))
    ]


class OCR:
    """Uses a detector to detect regions of text
    which will then be recognized using a recognizer."""

    def __init__(self, detector, recognizer):
        self.detector = detector
        self.recognizer = recognizer

    def run(self, image):
        # Detect bounding box
        t = time()
        text_recs, img_framed, image = self.detector.detect(image)
        text_recs = sort_box(text_recs)
        print("Detection:", time() - t)

        # Recognize text in bounding boxes
        t = time()
        result = self._char_rec(image, text_recs)
        print("Recognition:", time() - t)

        return result, img_framed

    def _char_rec(self, img, text_recs, adjust=False):
        results = {}
        x_dim, y_dim = img.shape[1], img.shape[0]

        for index, rec in enumerate(text_recs):
            x_length = int((rec[6] - rec[0]) * 0.1)
            y_length = int((rec[7] - rec[1]) * 0.2)
            if adjust:
                pt1 = (max(1, rec[0] - x_length), max(1, rec[1] - y_length))
                pt2 = (rec[2], rec[3])
                pt3 = (min(rec[6] + x_length, x_dim - 2),
                       min(y_dim - 2, rec[7] + y_length))
                pt4 = (rec[4], rec[5])
            else:
                pt1 = (max(1, rec[0]), max(1, rec[1]))
                pt2 = (rec[2], rec[3])
                pt3 = (min(rec[6], x_dim - 2), min(y_dim - 2, rec[7]))
                pt4 = (rec[4], rec[5])

            degree = np.degrees(np.arctan2(
                pt2[1] - pt1[1], pt2[0] - pt1[0]))  # 图像倾斜角度

            part_img = dump_rotate_image(img, degree, pt1, pt2, pt3, pt4)

            if part_img.shape[0] < 1 or part_img.shape[1] < 1 or part_img.shape[0] > part_img.shape[1]:  # 过滤异常图片
                continue
            text = self.recognizer.recognize(part_img)
            if len(text) > 0:
                results[index] = [rec]
                results[index].append(text)  # 识别文字

        return results


def make_default_ocr(detector_model_path, recognizer_model_path, alphabet_path, execution_providers):
    return OCR(
        detector=CPTNDetector(detector_model_path, execution_providers),
        recognizer=CRNNRecognizer(
            recognizer_model_path, alphabet_path, execution_providers)
    )
