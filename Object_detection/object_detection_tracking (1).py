"""
Object Detection and Tracking
==============================
Uses YOLOv8 (pre-trained) for detection + SORT algorithm for tracking.
Supports: webcam, video file, or demo with generated test frames.

Usage:
    python object_detection_tracking.py                  # webcam (index 0)
    python object_detection_tracking.py --source video.mp4
    python object_detection_tracking.py --demo           # synthetic demo (no camera needed)
    python object_detection_tracking.py --source 0 --conf 0.4 --save output.mp4
"""

import argparse
import time
import numpy as np
import cv2
from collections import defaultdict
from ultralytics import YOLO

# ─── SORT Tracker (pure-Python, no extra deps) ───────────────────────────────
from scipy.optimize import linear_sum_assignment

def iou(bb_test, bb_gt):
    """Intersection-over-Union between two [x1,y1,x2,y2] boxes."""
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
    """Kalman-filter-based tracker for a single bounding box."""
    count = 0

    def __init__(self, bbox):
        # State: [cx, cy, s, r, cx', cy', s'] where s=area, r=aspect ratio
        self.kf = cv2.KalmanFilter(7, 4)
        self.kf.measurementMatrix = np.array(
            [[1,0,0,0,0,0,0],
             [0,1,0,0,0,0,0],
             [0,0,1,0,0,0,0],
             [0,0,0,1,0,0,0]], dtype=np.float32)
        self.kf.transitionMatrix = np.array(
            [[1,0,0,0,1,0,0],
             [0,1,0,0,0,1,0],
             [0,0,1,0,0,0,1],
             [0,0,0,1,0,0,0],
             [0,0,0,0,1,0,0],
             [0,0,0,0,0,1,0],
             [0,0,0,0,0,0,1]], dtype=np.float32)
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
    """SORT: Simple Online and Realtime Tracking."""

    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.frame_count = 0

    def update(self, detections, class_ids=None, class_names=None):
        """
        detections: Nx4 array of [x1,y1,x2,y2]
        Returns Mx5 array of [x1,y1,x2,y2,id] for confirmed tracks.
        """
        self.frame_count += 1
        predicted = []
        for t in self.trackers:
            p = t.predict()
            predicted.append(p)

        # Associate detections to trackers
        matched, unmatched_dets, unmatched_trks = self._associate(
            detections, predicted)

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
    (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134),
    (26, 147, 52), (0, 212, 187), (44, 153, 168), (0, 194, 255),
    (52, 69, 147), (100, 115, 255), (0, 24, 236), (132, 56, 255),
    (82, 0, 133), (203, 56, 255), (255, 149, 200), (255, 55, 199),
]

def get_color(track_id):
    return PALETTE[int(track_id) % len(PALETTE)]


def draw_box(frame, x1, y1, x2, y2, track_id, label, conf=None):
    color = get_color(track_id)
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

    # Bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Corner accents
    L = max(10, min(20, (x2-x1)//5))
    T = 3
    for px, py, dx, dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
        cv2.line(frame, (px, py), (px+dx*L, py), color, T)
        cv2.line(frame, (px, py), (px, py+dy*L), color, T)

    # Label
    text = f"ID:{track_id} {label}"
    if conf is not None:
        text += f" {conf:.2f}"
    (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1-th-bl-4), (x1+tw+4, y1), color, -1)
    cv2.putText(frame, text, (x1+2, y1-bl-2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,0), 1, cv2.LINE_AA)
    return frame


def draw_overlay(frame, fps, n_tracks, frame_idx):
    h, w = frame.shape[:2]
    # Semi-transparent top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (w, 38), (20,20,20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, f"YOLOv8 + SORT | FPS: {fps:5.1f} | Tracks: {n_tracks:3d} | Frame: {frame_idx}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,230,255), 1, cv2.LINE_AA)
    return frame


# ─── Demo Frame Generator ─────────────────────────────────────────────────────

def generate_demo_frame(frame_idx, w=1280, h=720):
    """Generate a synthetic frame with moving rectangles for demo without camera."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Background grid
    for i in range(0, w, 80):
        cv2.line(frame, (i, 0), (i, h), (30, 30, 30), 1)
    for i in range(0, h, 80):
        cv2.line(frame, (0, i), (w, i), (30, 30, 30), 1)

    objects = [
        {"cx": 200 + int(150*np.sin(frame_idx*0.03)), "cy": 200 + int(80*np.cos(frame_idx*0.02)), "bw":100, "bh":120, "color":(0,120,255), "label":"person"},
        {"cx": 600 + int(200*np.cos(frame_idx*0.025)), "cy": 350 + int(100*np.sin(frame_idx*0.015)), "bw":160, "bh":90, "color":(0,200,100), "label":"car"},
        {"cx": 950 + int(80*np.sin(frame_idx*0.04+1)), "cy": 180 + int(120*np.cos(frame_idx*0.03+1)), "bw":80, "bh":80, "color":(200,50,255), "label":"dog"},
        {"cx": 400 + int(100*np.cos(frame_idx*0.02+2)), "cy": 500 + int(60*np.sin(frame_idx*0.035+2)), "bw":130, "bh":70, "color":(255,180,0), "label":"bicycle"},
    ]
    # Draw filled rounded rects
    for obj in objects:
        x1 = obj["cx"] - obj["bw"]//2
        y1 = obj["cy"] - obj["bh"]//2
        x2 = obj["cx"] + obj["bw"]//2
        y2 = obj["cy"] + obj["bh"]//2
        cv2.rectangle(frame, (x1,y1),(x2,y2), obj["color"], -1)
        cv2.putText(frame, obj["label"], (x1+4, y1+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

    return frame, objects


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def run(source=0, conf=0.35, iou_thresh=0.45, save=None, demo=False,
        display=True, max_frames=None):

    # Load YOLOv8 nano (downloads ~6 MB if not cached; skipped in --demo mode)
    if not demo:
        print("[INFO] Loading YOLOv8n model …")
        model = YOLO("yolov8n.pt")
        class_names = model.names  # dict {int: str}
        print(f"[INFO] Model loaded. Classes: {len(class_names)}")
    else:
        model = None
        class_names = {0:"person", 1:"bicycle", 2:"car", 16:"dog", 17:"cat"}

    tracker = SORTTracker(max_age=30, min_hits=2, iou_threshold=0.3)
    track_history = defaultdict(list)  # for trajectory lines

    # Open video
    if demo:
        cap = None
        W, H = 1280, 720
        print("[INFO] Running in DEMO mode (synthetic frames, no camera needed).")
    else:
        cap = cv2.VideoCapture(source if isinstance(source, str) else int(source))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open source: {source}")
        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_src = cap.get(cv2.CAP_PROP_FPS) or 30
        print(f"[INFO] Source: {source}  |  {W}x{H} @ {fps_src:.1f} fps")

    writer = None
    if save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(save, fourcc, 25.0, (W, H))
        print(f"[INFO] Saving output to: {save}")

    frame_idx = 0
    t_prev = time.perf_counter()
    fps_display = 0.0

    print("[INFO] Press 'q' to quit, 's' to screenshot.")

    while True:
        if demo:
            frame, _ = generate_demo_frame(frame_idx, W, H)
            # Simulate detections from the synthetic objects
            # (In demo mode we skip YOLO to avoid needing real image content)
            objects = [
                {"cx": 200+int(150*np.sin(frame_idx*0.03)), "cy":200+int(80*np.cos(frame_idx*0.02)), "bw":100,"bh":120,"cid":0},
                {"cx": 600+int(200*np.cos(frame_idx*0.025)), "cy":350+int(100*np.sin(frame_idx*0.015)), "bw":160,"bh":90,"cid":2},
                {"cx": 950+int(80*np.sin(frame_idx*0.04+1)), "cy":180+int(120*np.cos(frame_idx*0.03+1)), "bw":80,"bh":80,"cid":16},
                {"cx": 400+int(100*np.cos(frame_idx*0.02+2)), "cy":500+int(60*np.sin(frame_idx*0.035+2)), "bw":130,"bh":70,"cid":1},
            ]
            dets = np.array([[o["cx"]-o["bw"]//2, o["cy"]-o["bh"]//2,
                               o["cx"]+o["bw"]//2, o["cy"]+o["bh"]//2] for o in objects], dtype=float)
            cids = [o["cid"] for o in objects]
            confs_list = [0.90]*len(objects)
            ret = True
        else:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Stream ended.")
                break

            # ── YOLO Detection ──
            results = model.predict(frame, conf=conf, iou=iou_thresh,
                                    verbose=False, device="cpu")[0]
            boxes = results.boxes
            if len(boxes):
                dets = boxes.xyxy.cpu().numpy()
                cids = boxes.cls.cpu().numpy().astype(int).tolist()
                confs_list = boxes.conf.cpu().numpy().tolist()
            else:
                dets = np.empty((0,4))
                cids, confs_list = [], []

        # ── SORT Tracking ──
        tracks = tracker.update(
            dets if len(dets) else np.empty((0,4)),
            class_ids=cids,
            class_names=class_names
        )

        # ── Draw Tracks ──
        for trk in tracks:
            x1, y1, x2, y2, tid, cid, cname = trk
            # Trajectory
            cx, cy = int((x1+x2)/2), int((y1+y2)/2)
            track_history[tid].append((cx, cy))
            if len(track_history[tid]) > 40:
                track_history[tid].pop(0)
            pts = track_history[tid]
            for i in range(1, len(pts)):
                alpha = i / len(pts)
                color = tuple(int(c*alpha) for c in get_color(tid))
                cv2.line(frame, pts[i-1], pts[i], color, 2)
            # Box
            draw_box(frame, x1, y1, x2, y2, int(tid), str(cname))

        # ── HUD ──
        t_now = time.perf_counter()
        fps_display = 0.8*fps_display + 0.2*(1.0/(t_now - t_prev + 1e-9))
        t_prev = t_now
        draw_overlay(frame, fps_display, len(tracks), frame_idx)

        if writer:
            writer.write(frame)

        if display:
            cv2.imshow("Object Detection & Tracking — press Q to quit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                fname = f"screenshot_{frame_idx:05d}.jpg"
                cv2.imwrite(fname, frame)
                print(f"[INFO] Saved {fname}")

        frame_idx += 1
        if max_frames and frame_idx >= max_frames:
            break

    if cap:
        cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Done. Processed {frame_idx} frames.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8 + SORT Object Detection & Tracking")
    parser.add_argument("--source", default="0",
        help="Video source: '0' for webcam, path to video file, or RTSP URL")
    parser.add_argument("--conf", type=float, default=0.35,
        help="YOLO confidence threshold (default: 0.35)")
    parser.add_argument("--iou", type=float, default=0.45,
        help="YOLO IoU threshold for NMS (default: 0.45)")
    parser.add_argument("--save", default=None,
        help="Save output to this .mp4 file")
    parser.add_argument("--demo", action="store_true",
        help="Run synthetic demo without a camera or video file")
    parser.add_argument("--no-display", action="store_true",
        help="Run headless (useful for servers)")
    parser.add_argument("--max-frames", type=int, default=None,
        help="Stop after N frames (useful for testing)")
    args = parser.parse_args()

    source = args.source
    if source.isdigit():
        source = int(source)

    run(
        source=source,
        conf=args.conf,
        iou_thresh=args.iou,
        save=args.save,
        demo=args.demo,
        display=not args.no_display,
        max_frames=args.max_frames,
    )
