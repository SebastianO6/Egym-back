from extensions import db
from models.audit_log import AuditLog
from flask_jwt_extended import get_jwt_identity


def log_action(action, entity=None, entity_id=None, details=None):
    try:
        user_id = int(get_jwt_identity())
    except:
        user_id = None

    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details
    )

    db.session.add(log)
    db.session.commit()