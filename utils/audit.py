import json

from flask_jwt_extended import get_jwt_identity

from extensions import db
from models.audit_log import AuditLog


def _normalize_details(details):
    if details is None:
        return None
    if isinstance(details, str):
        return details
    return json.dumps(details, default=str, sort_keys=True)


def log_action(action, entity=None, entity_id=None, details=None, session=None, commit=False):
    try:
        user_id = int(get_jwt_identity())
    except Exception:
        user_id = None

    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=_normalize_details(details),
    )

    active_session = session or db.session
    active_session.add(log)

    if commit:
        active_session.commit()

    return log
