"""
YOLOv8 Animal Intrusion Detection Module
Detects Target Wild Animals: Elephant, Tiger, Monkey.
Explicitly rejects and filters out humans (preventing false elephant detections).
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
CUSTOM_MODEL_PATH = os.path.join(MODELS_DIR, "best.pt")
COCO_MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")
if not os.path.exists(COCO_MODEL_PATH):
    COCO_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")

TARGET_CLASSES = ["Elephant", "Monkey", "Tiger"]

# Visual styling colors in BGR
CLASS_COLORS = {
    "Elephant": (129, 185, 16),   # Emerald Green
    "Tiger": (11, 158, 245),       # Amber / Orange
    "Monkey": (246, 92, 139),      # Electric Purple
    "Default": (0, 200, 255),
}


class AnimalDetector:
    def __init__(self, confidence_threshold: float = 0.50):
        self.conf_threshold = confidence_threshold
        self.animal_model = None
        self.person_model = None
        self.is_custom_model = False
        self._load_models()

    def _load_models(self):
        """Loads target animal detector and COCO person validator."""
        # 1. Load Primary Animal Model
        if os.path.exists(CUSTOM_MODEL_PATH):
            self.animal_model = YOLO(CUSTOM_MODEL_PATH)
            self.is_custom_model = True
            print(f"[AnimalDetector] Loaded custom 3-class YOLOv8 model: {CUSTOM_MODEL_PATH}")
        else:
            print(f"[AnimalDetector] Custom model not found, falling back to COCO model: {COCO_MODEL_PATH}")
            self.animal_model = YOLO(COCO_MODEL_PATH if os.path.exists(COCO_MODEL_PATH) else "yolov8n.pt")
            self.is_custom_model = False

        # 2. Load Person Detector for strict Human Filtering
        # COCO yolov8n detects humans (class 0: person) with high precision
        if os.path.exists(COCO_MODEL_PATH):
            self.person_model = YOLO(COCO_MODEL_PATH)
        else:
            self.person_model = YOLO("yolov8n.pt")
        print("[AnimalDetector] Loaded COCO person detector for human-suppression filtering.")

    def preprocess_image(self, img_bgr: np.ndarray, target_size: int = 640) -> np.ndarray:
        """
        Data Preprocessing Pipeline:
        - Validates image array
        - Standardizes dimensions while preserving aspect ratio
        - Ensures contiguous memory layout
        """
        if img_bgr is None or img_bgr.size == 0:
            raise ValueError("Invalid image input for preprocessing")

        h, w = img_bgr.shape[:2]
        # Only downscale very large images for efficiency, keeping original quality
        if max(h, w) > 1920:
            scale = 1920 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img_resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            img_resized = img_bgr

        return np.ascontiguousarray(img_resized)

    def _detect_humans(self, img_bgr: np.ndarray) -> list:
        """Detects human bounding boxes in the frame to prevent false animal classifications."""
        human_boxes = []
        try:
            results = self.person_model(img_bgr, verbose=False, conf=0.35)[0]
            if results.boxes is not None:
                for b in results.boxes:
                    cls_id = int(b.cls[0])
                    # COCO class 0 is 'person'
                    if cls_id == 0:
                        conf = float(b.conf[0])
                        xyxy = b.xyxy[0].cpu().numpy().tolist()
                        human_boxes.append({"box": xyxy, "conf": conf})
        except Exception as e:
            print(f"[AnimalDetector] Warning during human detection: {e}")
        return human_boxes

    @staticmethod
    def _box_overlap(box_a: list, box_b: list) -> float:
        """Computes overlap ratio of box_a relative to box_b."""
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter_area = inter_w * inter_h

        area_a = max(1.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
        return inter_area / area_a

    def detect(self, img_bgr: np.ndarray) -> tuple:
        """
        Runs detection on an image.
        Returns:
            annotated_img (np.ndarray): Image with bounding boxes and labels drawn
            valid_detections (list): List of dicts with {animal, confidence, box}
            human_detected (bool): Whether a human was seen in the frame
        """
        processed_img = self.preprocess_image(img_bgr)
        human_boxes = self._detect_humans(processed_img)
        has_human = len(human_boxes) > 0

        # Run animal model inference
        results = self.animal_model(processed_img, verbose=False, conf=self.conf_threshold)[0]
        names = results.names
        valid_detections = []

        if results.boxes is not None:
            for b in results.boxes:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                raw_name = names.get(cls_id, str(cls_id)).capitalize()
                box = [round(float(v), 1) for v in b.xyxy[0].cpu().numpy()]

                # Target class filter: ONLY Elephant, Tiger, Monkey
                # If fallback COCO model was used:
                if not self.is_custom_model:
                    if raw_name.lower() == "elephant":
                        animal_label = "Elephant"
                    else:
                        continue  # Skip non-target COCO classes
                else:
                    if raw_name in TARGET_CLASSES:
                        animal_label = raw_name
                    else:
                        continue

                # STRICT HUMAN FILTERING:
                # If this detected box overlaps significantly with any detected human,
                # REJECT IT COMPLETELY to prevent humans being labeled as animals!
                is_false_positive_human = False
                for hb in human_boxes:
                    overlap = self._box_overlap(box, hb["box"])
                    overlap_reverse = self._box_overlap(hb["box"], box)
                    if overlap > 0.20 or overlap_reverse > 0.20:
                        is_false_positive_human = True
                        break

                if is_false_positive_human:
                    # Suppress false detection
                    continue

                valid_detections.append({
                    "animal": animal_label,
                    "confidence": round(conf, 3),
                    "box": box
                })

        # Draw annotations on a copy of the image
        annotated_img = processed_img.copy()
        for det in valid_detections:
            self._draw_box(annotated_img, det)

        return annotated_img, valid_detections, has_human

    def _draw_box(self, img: np.ndarray, detection: dict):
        """Draws aesthetic bounding box and glowing badge label."""
        x1, y1, x2, y2 = [int(v) for v in detection["box"]]
        label = f"{detection['animal']} {int(detection['confidence'] * 100)}%"
        color = CLASS_COLORS.get(detection["animal"], CLASS_COLORS["Default"])

        # Main bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

        # Corner accents for sleek modern UI look
        corner_len = min(20, (x2 - x1) // 4, (y2 - y1) // 4)
        cv2.line(img, (x1, y1), (x1 + corner_len, y1), color, 4, cv2.LINE_AA)
        cv2.line(img, (x1, y1), (x1, y1 + corner_len), color, 4, cv2.LINE_AA)
        cv2.line(img, (x2, y1), (x2 - corner_len, y1), color, 4, cv2.LINE_AA)
        cv2.line(img, (x2, y1), (x2, y1 + corner_len), color, 4, cv2.LINE_AA)
        cv2.line(img, (x1, y2), (x1 + corner_len, y2), color, 4, cv2.LINE_AA)
        cv2.line(img, (x1, y2), (x1, y2 - corner_len), color, 4, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2 - corner_len, y2), color, 4, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2, y2 - corner_len), color, 4, cv2.LINE_AA)

        # Label badge background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        badge_y1 = max(0, y1 - text_h - 12)
        badge_y2 = y1
        badge_x2 = min(img.shape[1], x1 + text_w + 16)

        # Filled badge background
        cv2.rectangle(img, (x1, badge_y1), (badge_x2, badge_y2), color, -1)
        # White text inside badge
        cv2.putText(img, label, (x1 + 8, badge_y2 - 6), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


# Global singleton detector instance
_detector_instance = None


def get_detector() -> AnimalDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnimalDetector(confidence_threshold=0.45)
    return _detector_instance
