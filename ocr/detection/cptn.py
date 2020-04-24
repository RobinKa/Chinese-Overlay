from time import time
import numpy as np
import onnxruntime as rt
from .utils import gen_anchor, bbox_transfor_inv, clip_box, filter_bbox, nms, TextProposalConnectorOriented, softmax


class CPTNDetector:
    """Detect areas of potential texts."""

    prob_thresh = 0.5
    image_mean = np.array([123.68, 116.779, 103.939], dtype=np.float32)

    def __init__(self, model_path, execution_providers):
        session_opts = rt.SessionOptions()
        session_opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_opts.enable_mem_pattern = False
        self.session = rt.InferenceSession(model_path, session_opts)
        self.session.set_providers(execution_providers)

    def detect(self, image, expand=True):
        image_r = image.copy()
        image_c = image.copy()
        h, w = image.shape[:2]
        image = image.astype(np.float32) - self.image_mean
        image = np.expand_dims(image.transpose(2, 0, 1), 0)

        cls, regr = self.session.run(None, {"images": image})

        cls_prob = softmax(cls, axis=-1)

        anchor = gen_anchor((int(h / 16), int(w / 16)), 16)
        bbox = bbox_transfor_inv(anchor, regr)
        bbox = clip_box(bbox, [h, w])
        # print(bbox.shape)

        fg = np.where(cls_prob[0, :, 1] > self.prob_thresh)[0]
        # print(np.max(cls_prob[0, :, 1]))
        select_anchor = bbox[fg, :]
        select_score = cls_prob[0, fg, 1]
        select_anchor = select_anchor.astype(np.int32)
        # print(select_anchor.shape)
        keep_index = filter_bbox(select_anchor, 16)

        # nms
        select_anchor = select_anchor[keep_index]
        select_score = select_score[keep_index]
        select_score = np.reshape(select_score, (select_score.shape[0], 1))
        nmsbox = np.hstack((select_anchor, select_score))
        keep = nms(nmsbox, 0.3)
        # print(keep)
        select_anchor = select_anchor[keep]
        select_score = select_score[keep]

        # text line-
        textConn = TextProposalConnectorOriented()
        text = textConn.get_text_lines(select_anchor, select_score, [h, w])

        # expand text
        if expand:
            for idx in range(len(text)):
                text[idx][0] = max(text[idx][0] - 10, 0)
                text[idx][2] = min(text[idx][2] + 10, w - 1)
                text[idx][4] = max(text[idx][4] - 10, 0)
                text[idx][6] = min(text[idx][6] + 10, w - 1)

        return text, image_c, image_r
