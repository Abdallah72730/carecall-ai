"""Seed a test dental clinic with 30 FAQs and default business hours.

Run from the backend/ directory:
    python scripts/seed_faqs.py

Idempotent: re-running replaces FAQs and upserts hours for the same test clinic.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import supabase_admin  # noqa: E402
from services.embedding import batch_encode  # noqa: E402

TEST_CLINIC_NAME = "Test Dental Clinic"

FAQS: list[dict] = [
    {"category": "hours", "question": "What are your hours?", "answer": "We're open Monday to Friday, 8 AM to 5 PM Mountain Time."},
    {"category": "hours", "question": "Are you open on weekends?", "answer": "We're closed on Saturdays and Sundays."},
    {"category": "hours", "question": "Are you open on statutory holidays?", "answer": "We're closed on all Alberta statutory holidays. Check our website for specific dates."},
    {"category": "booking", "question": "How do I book an appointment?", "answer": "You can call us during office hours, or use our online booking portal on our website."},
    {"category": "booking", "question": "Do you accept walk-ins?", "answer": "We strongly prefer appointments. Walk-ins are accepted only for dental emergencies during office hours."},
    {"category": "booking", "question": "How do I cancel an appointment?", "answer": "Please call at least 24 hours before your appointment to avoid a cancellation fee."},
    {"category": "booking", "question": "What is your cancellation policy?", "answer": "Less than 24 hours' notice may incur a 50 dollar cancellation fee."},
    {"category": "new-patient", "question": "Are you accepting new patients?", "answer": "Yes, we welcome new patients. Call us or book online to register."},
    {"category": "new-patient", "question": "What should I bring to my first appointment?", "answer": "Bring a piece of government ID, your insurance card if applicable, and a list of any medications you're taking."},
    {"category": "insurance", "question": "What insurance plans do you accept?", "answer": "We accept most major Alberta plans including Alberta Blue Cross, Sun Life, Manulife, Canada Life, and Pacific Blue Cross."},
    {"category": "insurance", "question": "Do you direct-bill insurance?", "answer": "Yes, we direct-bill most major insurance providers so you only pay any remaining portion at the visit."},
    {"category": "insurance", "question": "What if I don't have insurance?", "answer": "We follow the Alberta Dental Fee Guide and offer payment plans for major treatments. We can give you a written estimate before any procedure."},
    {"category": "pricing", "question": "How much does a checkup cost?", "answer": "A standard exam runs about 90 dollars and a routine cleaning starts at 120 dollars. Final cost depends on your insurance coverage."},
    {"category": "pricing", "question": "What forms of payment do you accept?", "answer": "We accept cash, debit, Visa, Mastercard, and direct insurance billing."},
    {"category": "pricing", "question": "Do you offer payment plans?", "answer": "Yes, we offer interest-free monthly payment plans for major treatments such as crowns, root canals, and Invisalign."},
    {"category": "services", "question": "What dental services do you offer?", "answer": "We offer general dentistry, cleanings, fillings, crowns, root canals, extractions, whitening, Invisalign, and orthodontic referrals."},
    {"category": "services", "question": "Do you offer teeth whitening?", "answer": "Yes, we offer both in-office whitening and take-home whitening kits."},
    {"category": "services", "question": "Do you offer Invisalign?", "answer": "Yes, we are a certified Invisalign provider for clear-aligner orthodontic treatment."},
    {"category": "services", "question": "Do you do wisdom tooth extractions?", "answer": "Yes, we perform wisdom tooth extractions in-office under local anesthetic, and refer complex cases to an oral surgeon."},
    {"category": "services", "question": "Do you offer sedation dentistry?", "answer": "We offer nitrous oxide for anxious patients. We refer patients needing IV sedation to a partner clinic."},
    {"category": "services", "question": "How often should I come for a cleaning?", "answer": "Every six months is the standard recommendation for most patients."},
    {"category": "services", "question": "How long does a typical cleaning take?", "answer": "A routine cleaning appointment usually takes 45 to 60 minutes."},
    {"category": "pediatric", "question": "Do you treat children?", "answer": "Yes, we provide general dentistry for patients of all ages, including children from age 3 and up."},
    {"category": "pediatric", "question": "At what age should my child have their first dental visit?", "answer": "We recommend a first dental visit by age 1 or within 6 months of the first tooth appearing."},
    {"category": "emergency", "question": "What should I do for a dental emergency?", "answer": "During office hours, call us right away. After hours, please go to your nearest emergency room or call 911 if it is life-threatening."},
    {"category": "emergency", "question": "Do you have a 24/7 emergency line?", "answer": "We don't operate a 24/7 line. If you leave an after-hours message, we'll return your call the next business day."},
    {"category": "x-rays", "question": "How often do you take dental X-rays?", "answer": "We take a full set of X-rays every 1 to 2 years for healthy adult patients, or sooner if clinically needed."},
    {"category": "x-rays", "question": "Are dental X-rays safe?", "answer": "Yes. We use modern digital X-rays which use a very low dose of radiation, and we always shield non-target areas."},
    {"category": "location", "question": "Where are you located?", "answer": "We are located in Calgary, Alberta. The exact street address and a map are on our website."},
    {"category": "location", "question": "Is there parking at the clinic?", "answer": "Yes, free patient parking is available on-site."},
]


def _normalize_phone(p: str) -> str:
    return p.strip()


def seed() -> None:
    client = supabase_admin()

    existing = (
        client.table("clinics").select("id").eq("name", TEST_CLINIC_NAME).limit(1).execute()
    )
    if existing.data:
        clinic_id = existing.data[0]["id"]
        print(f"Using existing test clinic: {clinic_id}")
    else:
        created = client.table("clinics").insert(
            {
                "name": TEST_CLINIC_NAME,
                "subscription_status": "trial",
                "is_active": True,
            }
        ).execute()
        clinic_id = created.data[0]["id"]
        print(f"Created test clinic: {clinic_id}")

    # Default business hours: Mon-Fri 08:00-17:00, weekends closed.
    hours = []
    for dow in range(5):
        hours.append(
            {
                "clinic_id": clinic_id,
                "day_of_week": dow,
                "open_time": "08:00",
                "close_time": "17:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        )
    for dow in (5, 6):
        hours.append(
            {
                "clinic_id": clinic_id,
                "day_of_week": dow,
                "is_closed": True,
                "timezone": "America/Edmonton",
            }
        )
    client.table("clinic_hours").upsert(hours, on_conflict="clinic_id,day_of_week").execute()

    # Replace FAQs (idempotent re-seed)
    client.table("faq_entries").delete().eq("clinic_id", clinic_id).execute()

    print(f"Embedding {len(FAQS)} FAQs (this may take ~10s on first run)...")
    texts = [f"{f['question']}\n{f['answer']}" for f in FAQS]
    embeddings = batch_encode(texts)

    rows = [
        {
            "clinic_id": clinic_id,
            "question": f["question"],
            "answer": f["answer"],
            "category": f["category"],
            "embedding": e,
        }
        for f, e in zip(FAQS, embeddings)
    ]
    client.table("faq_entries").insert(rows).execute()
    print(f"Inserted {len(FAQS)} FAQs.")
    print()
    print(f"TEST_CLINIC_ID={clinic_id}")
    print("Add this line to backend/.env and to Railway env vars.")


if __name__ == "__main__":
    seed()
