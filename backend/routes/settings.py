"""Routes API pour les paramètres"""
import sys
import functools
import traceback
from flask import Blueprint, request, jsonify

# Forcer les logs dans stderr
print = functools.partial(print, file=sys.stderr, flush=True)

from backend.models.settings import SettingsModel

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.route("", methods=["GET"])
def get_settings():
    """Récupère tous les paramètres"""
    try:
        settings = SettingsModel.get_all()

        # Convertir les booléens et nombres pour le frontend
        bool_keys = ["lockScreenEnabled", "sleepAfterLock", "soundAlert", "auto_lock"]
        int_keys = ["unknownThreshold", "cameraSource", "detection_threshold", "camera_index", "frame_skip"]

        result = {}
        for key, value in settings.items():
            if key in bool_keys:
                result[key] = str(value).lower() == "true"
            elif key in int_keys:
                try:
                    result[key] = int(value)
                except (ValueError, TypeError):
                    result[key] = 0
            else:
                result[key] = value

        return jsonify(result)
    except Exception as e:
        print(f"[GET SETTINGS] EXCEPTION: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@settings_bp.route("", methods=["PUT", "POST"])
def update_settings():
    """Met à jour les paramètres"""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "Données requises"}), 400

        # Valider les paramètres numériques
        validations = {
            "detection_threshold": (1, 100, int),
            "unknownThreshold": (1, 100, int),  # 1-5 secondes * ~3 détections/sec
            "frame_skip": (1, 10, int),
            "tolerance": (0.1, 1.0, float),
            "camera_index": (0, 10, int),
            "cameraSource": (0, 10, int),
        }

        for key, (min_val, max_val, type_fn) in validations.items():
            if key in data:
                try:
                    value = type_fn(data[key])
                    if not (min_val <= value <= max_val):
                        return jsonify({
                            "error": f"{key} doit être entre {min_val} et {max_val}"
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        "error": f"{key} doit être un nombre valide"
                    }), 400

        # Mettre à jour tous les paramètres
        SettingsModel.set_many(data)

        return jsonify({"message": "Paramètres mis à jour"})
    except Exception as e:
        print(f"[UPDATE SETTINGS] EXCEPTION: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/<key>", methods=["GET"])
def get_setting(key):
    """Récupère un paramètre spécifique"""
    value = SettingsModel.get(key)

    if value is None:
        return jsonify({"error": "Paramètre non trouvé"}), 404

    return jsonify({key: value})


@settings_bp.route("/<key>", methods=["PUT"])
def update_setting(key):
    """Met à jour un paramètre spécifique"""
    data = request.json

    if "value" not in data:
        return jsonify({"error": "Valeur requise"}), 400

    SettingsModel.set(key, data["value"])

    return jsonify({"message": f"Paramètre {key} mis à jour"})


@settings_bp.route("/reset", methods=["POST"])
def reset_settings():
    """Réinitialise tous les paramètres aux valeurs par défaut"""
    SettingsModel.reset_to_defaults()
    return jsonify({"message": "Paramètres réinitialisés"})
