"""Detection engine package."""
from .detector import get_detector, AnimalDetector, TARGET_CLASSES, CLASS_COLORS
from .metrics_evaluator import get_detection_metrics, run_detection_evaluation
