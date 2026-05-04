"""Stripe checkout and webhook handler."""
from __future__ import annotations

import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from config import settings
from db import supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

ACTIVE_STATUSES = {"trial", "trialing", "active", "pilot", "starter"}


def _stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _tier_from_price(price_id: str | None) -> str:
    if price_id and price_id == settings.STRIPE_PILOT_PRICE_ID:
        return "pilot"
    if price_id and price_id == settings.STRIPE_STARTER_PRICE_ID:
        return "starter"
    return "active"


def _resolve_clinic(token: str) -> dict:
    client = supabase_admin()
    try:
        user = client.auth.get_user(token).user
    except Exception as exc:
        raise HTTPException(401, "Invalid token") from exc
    res = (
        client.table("clinics")
        .select("id,name,email,stripe_customer_id,subscription_status")
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "No clinic linked to this user")
    return res.data[0]


class CheckoutRequest(BaseModel):
    price_id: str


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if payload.price_id not in {
        settings.STRIPE_PILOT_PRICE_ID,
        settings.STRIPE_STARTER_PRICE_ID,
    } or not payload.price_id:
        raise HTTPException(400, "Unknown price_id")

    clinic = _resolve_clinic(token)
    s = _stripe()
    customer_id = clinic.get("stripe_customer_id")
    if not customer_id:
        cust = s.Customer.create(
            email=clinic.get("email"),
            name=clinic.get("name") or "CareCall AI clinic",
            metadata={"clinic_id": clinic["id"]},
        )
        customer_id = cust["id"]
        supabase_admin().table("clinics").update(
            {"stripe_customer_id": customer_id}
        ).eq("id", clinic["id"]).execute()

    session = s.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": payload.price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/dashboard?checkout=success",
        cancel_url=f"{settings.FRONTEND_URL}/pricing?checkout=cancel",
        client_reference_id=clinic["id"],
        metadata={"clinic_id": clinic["id"]},
        allow_promotion_codes=True,
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "Stripe webhook secret not configured")
    payload = await request.body()
    s = _stripe()
    try:
        event = s.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as exc:
        logger.warning("Stripe webhook signature failed: %s", exc)
        raise HTTPException(400, "Invalid signature") from exc

    etype = event["type"]
    obj = event["data"]["object"]
    customer_id = obj.get("customer")

    clinic_id: str | None = None
    if customer_id:
        res = (
            supabase_admin()
            .table("clinics")
            .select("id")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
        )
        if res.data:
            clinic_id = res.data[0]["id"]
    if not clinic_id:
        clinic_id = (obj.get("metadata") or {}).get("clinic_id") or obj.get(
            "client_reference_id"
        )

    if not clinic_id:
        logger.info("Stripe %s — no clinic resolved, ignoring", etype)
        return {"received": True}

    update: dict = {}
    if etype == "checkout.session.completed":
        sub_id = obj.get("subscription")
        if sub_id:
            sub = s.Subscription.retrieve(sub_id)
            price_id = (sub["items"]["data"][0]["price"]["id"] if sub.get("items") else None)
            update["stripe_subscription_id"] = sub_id
            update["subscription_status"] = _tier_from_price(price_id)
    elif etype == "customer.subscription.updated":
        status = obj.get("status")
        items = (obj.get("items") or {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        if status in {"active", "trialing"}:
            update["subscription_status"] = _tier_from_price(price_id)
        elif status == "past_due":
            update["subscription_status"] = "past_due"
        elif status in {"canceled", "unpaid", "incomplete_expired"}:
            update["subscription_status"] = "canceled"
        update["stripe_subscription_id"] = obj.get("id")
    elif etype == "customer.subscription.deleted":
        update["subscription_status"] = "canceled"
        update["stripe_subscription_id"] = None
    elif etype == "invoice.payment_failed":
        update["subscription_status"] = "past_due"
    elif etype == "invoice.payment_succeeded":
        # subscription.updated will follow with the active status — no-op here
        pass

    if update:
        try:
            supabase_admin().table("clinics").update(update).eq(
                "id", clinic_id
            ).execute()
        except Exception as exc:
            logger.warning("clinic update for %s failed: %s", clinic_id, exc)
    return {"received": True}
