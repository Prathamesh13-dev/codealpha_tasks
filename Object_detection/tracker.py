import time
import numpy as np
import cv2
from collections import defaultdict
from ultralytics import YOLO
from scipy.optimize import linear_sum_assignment

# ─── SORT Tracker (pure-Python, no extra deps) ───────────────────────────────
def iou(bb_test, bb_gt):
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[2], bb_gt[2])
    yy2 = min(bb_test[3], bb_gt[3])
    w = max(0.0, xx2 - xx1)
    h = max(0.0, yy2 - yy1)
    inter = w * h
    area_test = (bb_test[2]-bb_test[0]) * (bb_test[3]-bb_test[1])
    area_gt   = (bb_gt[2]-bb_gt[0])   * (bb_gt[3]-bb_gt[1])
    union = area_test + area_gt - inter
    return inter / union if union > 0 else 0.0

class KalmanBoxTracker:
    count = 0
    def __init__(self, bbox):
        self.kf = cv2.KalmanFilter(7, 4)
        self.kf.measurementMatrix = np.array(
            [[1,0,0,0,0,0,0], [0,1,0,0,0,0,0], [0,0,1,0,0,0,0], [0,0,0,1,0,0,0]], dtype=np.float32)
        self.kf.transitionMatrix = np.array(
            [[1,0,0,0,1,0,0], [0,1,0,0,0,1,0], [0,0,1,0,0,0,1], [0,0,0,1,0,0,0],
             [0,0,0,0,1,0,0], [0,0,0,0,0,1,0], [0,0,0,0,0,0,1]], dtype=np.float32)
        self.kf.processNoiseCov[-1,-1] *= 0.01
        self.kf.processNoiseCov[4:,4:] *= 0.01
        self.kf.errorCovPost[4:,4:] *= 10
        self.kf.errorCovPost *= 10
        self.kf.measurementNoiseCov *= 10
        self.kf.statePost[:4] = self._xyxy_to_z(bbox)
        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0
        self.time_since_update = 0
        self.class_id = None
        self.class_name = "object"

    @staticmethod
    def _xyxy_to_z(bbox):
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        cx = bbox[0] + w / 2.
        cy = bbox[1] + h / 2.
        s = w * h
        r = w / float(h) if h > 0 else 1.0
        return np.array([cx, cy, s, r], dtype=np.float32).reshape(4, 1)

    @staticmethod
    def _z_to_xyxy(z):
        s, r = z[2], z[3]
        w = np.sqrt(abs(s * r))
        h = s / w if w > 0 else 0
        return np.array([z[0]-w/2, z[1]-h/2, z[0]+w/2, z[1]+h/2]).flatten()

    def predict(self):
        if self.kf.statePost[6] + self.kf.statePost[2] <= 0:
            self.kf.statePost[6] = 0
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        return self._z_to_xyxy(self.kf.statePre[:4])

    def update(self, bbox):
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.kf.correct(self._xyxy_to_z(bbox))

    def get_state(self):
        return self._z_to_xyxy(self.kf.statePost[:4])

class SORTTracker:
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.frame_count = 0

    def update(self, detections, class_ids=None, class_names=None):
        self.frame_count += 1
        predicted = [t.predict() for t in self.trackers]
        matched, unmatched_dets, unmatched_trks = self._associate(detections, predicted)

        for d, t_idx in matched:
            self.trackers[t_idx].update(detections[d])
            if class_ids is not None and d < len(class_ids):
                self.trackers[t_idx].class_id = class_ids[d]
                self.trackers[t_idx].class_name = (class_names[class_ids[d]]
                    if class_names and class_ids[d] < len(class_names) else "object")

        for d in unmatched_dets:
            trk = KalmanBoxTracker(detections[d])
            if class_ids is not None and d < len(class_ids):
                trk.class_id = class_ids[d]
                trk.class_name = (class_names[class_ids[d]]
                    if class_names and class_ids[d] < len(class_names) else "object")
            self.trackers.append(trk)

        results = []
        to_del = []
        for i, trk in enumerate(self.trackers):
            if trk.time_since_update > self.max_age:
                to_del.append(i)
                continue
            if trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits:
                state = trk.get_state()
                results.append((*state, trk.id, trk.class_id or 0, trk.class_name))
        for i in reversed(to_del):
            self.trackers.pop(i)
        return results

    def _associate(self, dets, preds):
        if len(preds) == 0:
            return [], list(range(len(dets))), []
        if len(dets) == 0:
            return [], [], list(range(len(preds)))
        iou_matrix = np.zeros((len(dets), len(preds)))
        for d, det in enumerate(dets):
            for t, pred in enumerate(preds):
                iou_matrix[d, t] = iou(det, pred)
        row_ind, col_ind = linear_sum_assignment(-iou_matrix)
        matched, unmatched_dets, unmatched_trks = [], [], []
        for d in range(len(dets)):
            if d not in row_ind:
                unmatched_dets.append(d)
        for t in range(len(preds)):
            if t not in col_ind:
                unmatched_trks.append(t)
        for r, c in zip(row_ind, col_ind):
            if iou_matrix[r, c] < self.iou_threshold:
                unmatched_dets.append(r)
                unmatched_trks.append(c)
            else:
                matched.append((r, c))
        return matched, unmatched_dets, unmatched_trks

# ─── Palette & Drawing Helpers ────────────────────────────────────────────────
PALETTE = [
    (255, 56, 56), (255, 157, 151), (255, 112, 31), (255, 178, 29),
    (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134)
]

def get_color(track_id):
    return PALETTE[int(track_id) % len(PALETTE)]

def draw_box(frame, x1, y1, x2, y2, track_id, label):
    color = get_color(track_id)
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text = f"ID:{track_id} {label}"
    (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1-th-bl-4), (x1+tw+4, y1), color, -1)
    cv2.putText(frame, text, (x1+2, y1-bl-2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,0), 1, cv2.LINE_AA)
    return frame

def generate_demo_frame(frame_idx, w=640, h=480):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    objects = [
        {"cx": 100 + int(50*np.sin(frame_idx*0.03)), "cy": 100 + int(40*np.cos(frame_idx*0.02)), "bw":50, "bh":60, "color":(0,120,255), "label":"person", "cid":0},
    ]
    for obj in objects:
        x1, y1, x2, y2 = obj["cx"] - obj["bw"]//2, obj["cy"] - obj["bh"]//2, obj["cx"] + obj["bw"]//2, obj["cy"] + obj["bh"]//2
        cv2.rectangle(frame, (x1,y1),(x2,y2), obj["color"], -1)
        cv2.putText(frame, obj["label"], (x1+4, y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    return frame, objects

# ─── Flask Video Generator ────────────────────────────────────────────────────
def generate_frames(source=0, conf=0.35, iou_thresh=0.45, demo=False):
    if not demo:
        model = YOLO("yolov8n.pt")
        class_names = model.names
        cap = cv2.VideoCapture(source)
    else:
        model = None
        class_names = {0:"person"}
        W, H = 640, 480
        cap = None

    tracker = SORTTracker(max_age=30, min_hits=2, iou_threshold=0.3)
    frame_idx = 0

    while True:
        if demo:
            frame, objects = generate_demo_frame(frame_idx, W, H)
            dets = np.array([[o["cx"]-o["bw"]//2, o["cy"]-o["bh"]//2, o["cx"]+o["bw"]//2, o["cy"]+o["bh"]//2] for o in objects], dtype=float)
            cids = [o["cid"] for o in objects]
        else:
            ret, frame = cap.read()
            # If the webcam fails to open or stream, output an error frame instead of breaking
            if not ret or frame is None:
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, "CAMERA ERROR: Cannot access video source.", (30, 220),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.putText(error_frame, "Check if camera is used by another app or try source=1", (30, 260),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                ret, buffer = cv2.imencode('.jpg', error_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.5)
                continue

            results = model.predict(frame, conf=conf, iou=iou_thresh, verbose=False, device="cpu")[0]
            boxes = results.boxes
            if len(boxes):
                dets = boxes.xyxy.cpu().numpy()
                cids = boxes.cls.cpu().numpy().astype(int).tolist()
                
                # DEBUG: Draw raw YOLO detections in bright green before SORT filters them
                for i in range(len(dets)):
                    rx1, ry1, rx2, ry2 = dets[i]
                    r_label = class_names[cids[i]]
                    cv2.rectangle(frame, (int(rx1), int(ry1)), (int(rx2), int(ry2)), (0, 255, 0), 2)
                    cv2.putText(frame, f"RAW: {r_label}", (int(rx1), int(ry1)-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                dets, cids = np.empty((0,4)), []

        tracks = tracker.update(dets if len(dets) else np.empty((0,4)), class_ids=cids, class_names=class_names)

        for trk in tracks:
            x1, y1, x2, y2, tid, cid, cname = trk
            draw_box(frame, x1, y1, x2, y2, int(tid), str(cname))

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        frame_idx += 1