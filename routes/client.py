from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
from decorators import role_required
from models import Client, WorkoutPlan
from models import Payment

client_bp = Blueprint("client", __name__)

@client_bp.get("/client/workouts")
@role_required("client")
def view_workouts():
    client_id = int(get_jwt_identity())

    client = Client.query.filter_by(id=client_id).first_or_404()

    if not client.subscription_active:
        return jsonify({"error": "Subscription inactive"}), 403

    plans = WorkoutPlan.query.filter_by(client_id=client.id).all()

    return jsonify([
        {
            "title": p.title,
            "description": p.description,
            "created_at": p.created_at
        }
        for p in plans
    ])


@client_bp.get("/client/payments")
@role_required("client")
def my_payments():
    client_id = int(get_jwt_identity())

    payments = Payment.query.filter_by(client_id=client_id).all()

    return jsonify([
        {
            "amount": p.amount,
            "status": p.status,
            "paid_at": p.paid_at
        }
        for p in payments
    ])