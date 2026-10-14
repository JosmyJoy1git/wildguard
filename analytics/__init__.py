"""Analytics package for crop damage modeling and animal activity."""
from .damage_model import estimate_crop_damage, get_damage_model_metrics, train_and_evaluate_damage_model
from .activity_analysis import analyze_animal_activity
