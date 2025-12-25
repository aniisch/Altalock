"""Routes API pour les logs"""
import json
import sys
import functools
import traceback
from flask import Blueprint, request, jsonify

# Forcer les logs dans stderr
print = functools.partial(print, file=sys.stderr, flush=True)

from backend.services.alert_service import get_alert_service

logs_bp = Blueprint("logs", __name__, url_prefix="/api/logs")


@logs_bp.route("", methods=["GET"])
def get_logs():
    """Récupère les logs avec pagination"""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    event_type = request.args.get("type")

    # Limiter les résultats
    limit = min(limit, 500)

    alert_service = get_alert_service()
    logs = alert_service.get_logs(limit=limit, offset=offset, event_type=event_type)

    # Parser les détails JSON
    for log in logs:
        if log.get("details"):
            try:
                log["details"] = json.loads(log["details"])
            except json.JSONDecodeError:
                pass

    return jsonify({
        "logs": logs,
        "limit": limit,
        "offset": offset,
        "count": len(logs)
    })


@logs_bp.route("/<int:log_id>", methods=["GET"])
def get_log(log_id):
    """Récupère un log spécifique"""
    from backend.models.database import get_db

    db = get_db()
    log = db.fetch_one("""
        SELECT l.*, u.name as user_name
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.id = ?
    """, (log_id,))

    if not log:
        return jsonify({"error": "Log non trouvé"}), 404

    # Parser les détails JSON
    if log.get("details"):
        try:
            log["details"] = json.loads(log["details"])
        except json.JSONDecodeError:
            pass

    return jsonify(log)


@logs_bp.route("/stats", methods=["GET"])
def get_stats():
    """Statistiques des logs"""
    from backend.models.database import get_db

    db = get_db()

    # Nombre total de logs
    total = db.fetch_one("SELECT COUNT(*) as count FROM logs")

    # Logs par type
    by_type = db.fetch_all("""
        SELECT event_type, COUNT(*) as count
        FROM logs
        GROUP BY event_type
        ORDER BY count DESC
    """)

    # Logs des dernières 24h
    last_24h = db.fetch_one("""
        SELECT COUNT(*) as count
        FROM logs
        WHERE created_at >= datetime('now', '-1 day')
    """)

    # Dernières alertes
    last_alerts = db.fetch_all("""
        SELECT l.*, u.name as user_name
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.event_type = 'alert'
        ORDER BY l.created_at DESC
        LIMIT 5
    """)

    return jsonify({
        "total": total["count"] if total else 0,
        "by_type": by_type,
        "last_24h": last_24h["count"] if last_24h else 0,
        "last_alerts": last_alerts
    })


@logs_bp.route("", methods=["DELETE"])
def clear_logs():
    """Supprime les logs (avec filtre optionnel)"""
    try:
        print("[CLEAR LOGS] Début de la suppression des logs...")
        event_type = request.args.get("type")
        days = request.args.get("older_than_days", type=int)

        from backend.models.database import get_db
        db = get_db()

        query = "DELETE FROM logs WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if days:
            query += " AND created_at < datetime('now', ?)"
            params.append(f"-{days} days")

        print(f"[CLEAR LOGS] Query: {query}, Params: {params}")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            deleted = cursor.rowcount
            conn.commit()

        print(f"[CLEAR LOGS] {deleted} log(s) supprimé(s)")
        return jsonify({
            "message": f"{deleted} log(s) supprimé(s)"
        })

    except Exception as e:
        print(f"[CLEAR LOGS] EXCEPTION: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
