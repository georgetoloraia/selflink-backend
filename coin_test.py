'''
python manage.py shell
'''


from hashlib import sha256
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.payments.models import PaymentEvent, PaymentEventProvider
from apps.coin.services.payments import mint_from_payment_event

User = get_user_model()
admin = User.objects.filter(is_superuser=True).order_by("id").first()
assert admin, "No superuser found"

amount_cents = 100_000_000  # 1,000,000 SLC @ 1 SLC = $1.00, amounts in cents
provider = PaymentEventProvider.STRIPE
provider_event_id = "bootstrap_superuser_slc_2026_01_22"  # stable, unique

pe, created = PaymentEvent.objects.get_or_create(
    provider=provider,
    provider_event_id=provider_event_id,
    defaults={
        "user": admin,
        "amount_cents": amount_cents,
        "currency": "USD",
        "event_type": "bootstrap_superuser_grant",
        "raw_body_hash": sha256(b"bootstrap_superuser_grant").hexdigest(),
        "verified_at": timezone.now(),
    },
)

# If it already existed but wasn't verified, verify it now (still no code change)
if not pe.verified_at:
    pe.verified_at = timezone.now()
    pe.save(update_fields=["verified_at", "updated_at"])

mint_from_payment_event(payment_event=pe, metadata={"source": "bootstrap_superuser_grant"})

'''
python manage.py coin_invariant_check

'''
