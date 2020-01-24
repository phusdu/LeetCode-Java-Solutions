import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock

from asynctest import create_autospec

from app.commons.providers.stripe.stripe_models import (
    PaymentIntent as StripePaymentIntent,
    Refund as StripeRefund,
    Charge as StripeCharge,
)
from app.commons.types import CountryCode, Currency, LegacyCountryId, PgpCode
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyConsumerCharge,
    LegacyPayment,
    LegacyStripeCharge,
    PaymentCharge,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentCharge,
    PgpPaymentIntent,
    PgpRefund,
    Refund,
)
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ChargeStatus,
    IntentStatus,
    LegacyConsumerChargeId,
    LegacyStripeChargeStatus,
    RefundReason,
    RefundStatus,
)
from app.payin.core.dispute.model import Dispute, DisputeChargeMetadata
from app.payin.core.payer.model import Payer, RawPayer
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.core.types import PgpPayerResourceId, PayerReferenceIdType
from app.payin.repository.dispute_repo import (
    ConsumerChargeDbEntity,
    StripeDisputeDbEntity,
)
from app.payin.repository.payer_repo import (
    PayerDbEntity,
    PgpCustomerDbEntity,
    DeletePayerRequestDbEntity,
    StripeCustomerDbEntity,
)
from app.payin.repository.payment_method_repo import (
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


class ContextMock(MagicMock):
    async def __aenter__(self, *args, **kwargs):
        pass

    async def __aexit__(self, *args, **kwargs):
        pass


def generate_payment_intent(
    id: uuid.UUID = None,
    cart_payment_id: uuid.UUID = None,
    status: str = "init",
    amount: int = 500,
    idempotency_key: str = None,
    capture_method: str = "manual",
    captured_at: Optional[datetime] = None,
    legacy_consumer_charge_id: LegacyConsumerChargeId = LegacyConsumerChargeId(1),
    application_fee_amount: int = 0,
    created_at: datetime = datetime.now(timezone.utc),
    capture_after: Optional[datetime] = None,
):
    return PaymentIntent(
        id=id if id else uuid.uuid4(),
        cart_payment_id=cart_payment_id if cart_payment_id else uuid.uuid4(),
        idempotency_key=idempotency_key if idempotency_key else str(uuid.uuid4()),
        amount_initiated=0,
        amount=amount,
        application_fee_amount=application_fee_amount,
        capture_method=capture_method,
        country=CountryCode.US,
        currency=Currency.USD.value,
        status=IntentStatus.from_str(status),
        statement_descriptor="descriptor",
        payment_method_id=uuid.uuid4(),
        legacy_consumer_charge_id=legacy_consumer_charge_id,
        created_at=created_at,
        updated_at=datetime.now(timezone.utc),
        captured_at=captured_at,
        cancelled_at=None,
        capture_after=capture_after,
    )


def generate_pgp_payment_intent(
    id: uuid.UUID = None,
    payment_intent_id: uuid.UUID = None,
    status: str = "init",
    amount: int = 500,
    amount_capturable: int = 500,
    amount_received: int = 0,
    capture_method: str = "manual",
    resource_id: str = None,
    charge_resource_id: str = "charge_resource_id",
    payout_account_id: str = None,
    created_at: datetime = datetime.now(timezone.utc),
) -> PgpPaymentIntent:
    return PgpPaymentIntent(
        id=id if id else uuid.uuid4(),
        payment_intent_id=payment_intent_id if payment_intent_id else uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        pgp_code=PgpCode.STRIPE,
        resource_id=resource_id if resource_id else str(uuid.uuid4()),
        status=IntentStatus.from_str(status),
        invoice_resource_id=None,
        charge_resource_id="charge_resource_id",
        payment_method_resource_id=str(uuid.uuid4()),
        customer_resource_id=str(uuid.uuid4()),
        currency=Currency.USD.value,
        amount=amount,
        amount_capturable=amount_capturable,
        amount_received=amount_received,
        application_fee_amount=0,
        payout_account_id=payout_account_id,
        capture_method=capture_method,
        created_at=created_at,
        updated_at=datetime.now(timezone.utc),
        captured_at=None,
        cancelled_at=None,
    )


def generate_payer() -> Payer:
    return Payer(country=CountryCode.US)


def generate_cart_payment(
    id: uuid.UUID = None,
    payer_id: uuid.UUID = uuid.uuid4(),
    payment_method_id: uuid.UUID = uuid.uuid4(),
    amount=500,
    capture_method=CaptureMethod.MANUAL.value,
    deleted_at: datetime = None,
    created_at: datetime = None,
    reference_id: str = None,
    reference_type: str = None,
) -> CartPayment:
    return CartPayment(
        id=id if id else uuid.uuid4(),
        amount=amount,
        payer_id=payer_id,
        payment_method_id=payment_method_id,
        capture_method=capture_method,
        correlation_ids=CorrelationIds(
            reference_id=reference_id, reference_type=reference_type
        )
        if reference_id and reference_type
        else CorrelationIds(reference_id="0", reference_type="2"),
        delay_capture=True,
        client_description="Test description",
        deleted_at=deleted_at,
        created_at=created_at,
    )


def generate_refund(
    payment_intent_id: uuid.UUID = None,
    status: RefundStatus = RefundStatus.PROCESSING,
    idempotency_key: str = None,
):
    return Refund(
        id=uuid.uuid4(),
        payment_intent_id=payment_intent_id if payment_intent_id else uuid.uuid4(),
        idempotency_key=idempotency_key if idempotency_key else str(uuid.uuid4()),
        status=status,
        amount=500,
        currency=Currency.USD,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def generate_pgp_refund(
    status: RefundStatus = RefundStatus.PROCESSING,
    pgp_resource_id: str = None,
    charge_resource_id: str = None,
):
    return PgpRefund(
        id=uuid.uuid4(),
        refund_id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        status=status,
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id=pgp_resource_id,
        charge_resource_id=charge_resource_id,
        amount=500,
        currency=Currency.USD,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def generate_payment_intent_adjustment_history(
    payment_intent_id: uuid.UUID = None, idempotency_key: str = None
):
    return PaymentIntentAdjustmentHistory(
        id=uuid.uuid4(),
        payer_id=uuid.uuid4(),
        payment_intent_id=payment_intent_id if payment_intent_id else uuid.uuid4(),
        amount=500,
        amount_original=400,
        amount_delta=100,
        currency=Currency.USD,
        idempotency_key=idempotency_key if idempotency_key else str(uuid.uuid4()),
        created_at=datetime.now(),
    )


def generate_legacy_payment() -> LegacyPayment:
    return LegacyPayment(
        dd_consumer_id=1,
        dd_country_id=1,
        dd_stripe_card_id=1,
        dd_additional_payment_info={"test_key": f"{uuid.uuid4()}"},
        stripe_charge_id=None,
        stripe_customer_id=PgpPayerResourceId("cus_ja7lka"),
        stripe_card_id=None,
    )


def generate_legacy_consumer_charge(charge_id: int = 1) -> LegacyConsumerCharge:
    now = datetime.now()
    return LegacyConsumerCharge(
        id=LegacyConsumerChargeId(charge_id),
        target_id=1,
        target_ct_id=2,
        idempotency_key=str(uuid.uuid4()),
        is_stripe_connect_based=False,
        total=100,
        original_total=100,
        currency=Currency.USD,
        country_id=LegacyCountryId.US,
        issue_id=None,
        stripe_customer_id=None,
        created_at=now,
        updated_at=now,
    )


def generate_legacy_stripe_charge(
    id: int = 1,
    charge_id: int = None,
    stripe_id: str = None,
    amount: int = 100,
    amount_refunded: int = 0,
    refunded_at: datetime = None,
    idempotency_key: Optional[str] = None,
    status: str = LegacyStripeChargeStatus.SUCCEEDED,
    currency: Currency = Currency.USD,
    error_reason: str = None,
) -> LegacyStripeCharge:
    return LegacyStripeCharge(
        id=id,
        amount=amount,
        amount_refunded=amount_refunded,
        currency=currency,
        status=status,
        error_reason=error_reason,
        additional_payment_info=None,
        description=None,
        idempotency_key=idempotency_key if idempotency_key else str(uuid.uuid4()),
        card_id=None,
        charge_id=charge_id if charge_id else 1,
        stripe_id=stripe_id if stripe_id else str(uuid.uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        refunded_at=refunded_at,
    )


def generate_payment_charge(
    payment_intent_id: uuid.UUID = uuid.uuid4(),
    status: ChargeStatus = ChargeStatus.REQUIRES_CAPTURE,
    amount: int = 700,
    amount_refunded=0,
) -> PaymentCharge:
    return PaymentCharge(
        id=uuid.uuid4(),
        payment_intent_id=payment_intent_id,
        pgp_code=PgpCode.STRIPE,
        idempotency_key=str(uuid.uuid4()),
        status=status,
        currency=Currency.USD.value,
        amount=amount,
        amount_refunded=amount_refunded,
        application_fee_amount=None,
        payout_account_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_pgp_payment_charge(
    payment_charge_id: uuid.UUID = uuid.uuid4(),
    status: ChargeStatus = ChargeStatus.REQUIRES_CAPTURE,
    amount: int = 700,
    amount_refunded=0,
) -> PgpPaymentCharge:
    return PgpPaymentCharge(
        id=uuid.uuid4(),
        payment_charge_id=payment_charge_id,
        pgp_code=PgpCode.STRIPE,
        idempotency_key=str(uuid.uuid4()),
        status=status,
        currency=Currency.USD.value,
        amount=amount,
        amount_refunded=amount_refunded,
        application_fee_amount=None,
        payout_account_id=None,
        resource_id="resource_id",
        intent_resource_id="intent_id",
        invoice_resource_id=None,
        payment_method_resource_id="payment_id",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def _generate_provider_charge(
    payment_intent: PaymentIntent,
    pgp_payment_intent: PgpPaymentIntent,
    amount_refunded: int = 0,
):
    provider_charge = MagicMock()
    provider_charge.currency = pgp_payment_intent.currency
    provider_charge.amount = pgp_payment_intent.amount
    provider_charge.amount_refunded = amount_refunded
    provider_charge.application_fee_amount = pgp_payment_intent.application_fee_amount
    provider_charge.on_behalf_of = pgp_payment_intent.payout_account_id
    provider_charge.charge_id = str(uuid.uuid4())
    provider_charge.payment_intent = pgp_payment_intent.resource_id
    provider_charge.invoice = str(uuid.uuid4())
    provider_charge.payment_method = str(uuid.uuid4())
    provider_charge.status = "succeeded"
    provider_charge.id = str(uuid.uuid4())
    return provider_charge


def generate_provider_charges(
    payment_intent: PaymentIntent,
    pgp_payment_intent: PgpPaymentIntent,
    amount_refunded: int = 0,
):
    charges = MagicMock()
    charges.data = [
        _generate_provider_charge(payment_intent, pgp_payment_intent, amount_refunded)
    ]

    return charges


def generate_provider_intent(
    amount: int = 500,
    amount_received: int = 0,
    amount_capturable: int = 500,
    amount_refunded: int = 0,
    status: str = "requires_capture",
):
    mocked_intent = create_autospec(StripePaymentIntent)
    mocked_intent.id = "test_intent_id"
    mocked_intent.status = status
    mocked_intent.amount = amount
    mocked_intent.amount_received = amount_received
    mocked_intent.amount_capturable = amount_capturable
    mocked_intent.charges = MagicMock()
    mocked_intent.charges.data = [create_autospec(StripeCharge)]
    mocked_intent.charges.data[0].status = "succeeded"
    mocked_intent.charges.data[0].currency = "usd"
    mocked_intent.charges.data[0].id = str(uuid.uuid4())
    mocked_intent.charges.data[0].amount = amount
    mocked_intent.charges.data[0].amount_refunded = amount_refunded
    mocked_intent.charges.data[0].refunds = None

    if amount_refunded > 0:
        mocked_intent.charges.data[0].refunds = MagicMock()
        mocked_intent.charges.data[0].refunds.data = [
            generate_provider_refund(amount=amount_refunded)
        ]

    return mocked_intent


def generate_provider_refund(amount: int = 200, reason: str = None):
    mocked_refund = create_autospec(StripeRefund)
    mocked_refund.id = "test_refund_id"
    mocked_refund.object = "refund"
    mocked_refund.amount = amount
    mocked_refund.balance_transaction = "balance_transaction"
    mocked_refund.charge = "refund charge_id"
    mocked_refund.currency = Currency.USD
    mocked_refund.metadata = {}
    mocked_refund.reason = reason
    mocked_refund.receipt_number = None
    mocked_refund.source_transfer_reversal = None
    mocked_refund.status = "succeeded"
    mocked_refund.transfer_reversal = None
    return mocked_refund


def generate_dispute() -> Dispute:
    return Dispute(
        id=1,
        stripe_dispute_id="1",
        disputed_at=datetime.now(),
        amount=100,
        fee=10,
        net=110,
        charged_at=datetime.now(),
        reason="subscription_cancelled",
        status="needs_response",
        evidence_due_by=datetime.now(),
        stripe_charge_id=1,
        stripe_card_id=1,
    )


def generate_dispute_db_entity() -> StripeDisputeDbEntity:
    return StripeDisputeDbEntity(
        id=1,
        stripe_dispute_id="1",
        disputed_at=datetime.now(),
        amount=100,
        fee=10,
        net=110,
        charged_at=datetime.now(),
        reason="subscription_cancelled",
        status="needs_response",
        evidence_due_by=datetime.now(),
        stripe_charge_id=1,
        stripe_card_id=1,
    )


def generate_dispute_charge_metadata() -> DisputeChargeMetadata:
    return DisputeChargeMetadata(
        dd_order_cart_id="1",
        dd_charge_id="1",
        dd_consumer_id="1",
        stripe_card_id="VALID_CARD_ID",
        stripe_dispute_status="needs_response",
        stripe_dispute_reason="subscription_cancelled",
    )


def generate_consumer_charge_entity() -> ConsumerChargeDbEntity:
    return ConsumerChargeDbEntity(
        id=1,
        target_ct_id=1,
        target_id=1,
        is_stripe_connect_based=True,
        country_id=1,
        consumer_id=1,
        stripe_customer_id=1,
        total=100,
        original_total=100,
    )


def generate_pgp_payment_method() -> PgpPaymentMethodDbEntity:
    return PgpPaymentMethodDbEntity(
        id=uuid.uuid4(),
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id="VALID_STRIPE_ID",
        payer_id=uuid.uuid4(),
        payment_method_id=uuid.uuid4(),
        type="visa",
    )


def generate_stripe_card(
    active: bool = True, stripe_id: str = "VALID_STRIPE_ID", country=CountryCode.US
) -> StripeCardDbEntity:
    return StripeCardDbEntity(
        id=uuid.uuid4(),
        stripe_id=stripe_id,
        fingerprint="",
        last4="",
        dynamic_last4="",
        exp_month="01",
        exp_year="2020",
        type="Visa",
        active=active,
        country_of_origin=country,
    )


def generate_raw_payer() -> RawPayer:
    payer_id = uuid.uuid4()
    return RawPayer(
        payer_entity=PayerDbEntity(
            id=payer_id,
            country=CountryCode.US,
            legacy_stripe_customer_id="cus_fakeid",
            payer_reference_id="1",
            payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
            updated_at=datetime.now(timezone.utc),
            primary_pgp_payer_resource_id="cus_fakeid",
        ),
        pgp_customer_entity=PgpCustomerDbEntity(
            id=uuid.uuid4(),
            payer_id=payer_id,
            pgp_resource_id="cus_fakeid",
            updated_at=datetime.now(timezone.utc),
            pgp_code=PgpCode.STRIPE,
        ),
        stripe_customer_entity=StripeCustomerDbEntity(
            id=1,
            stripe_id="VALID_STRIPE_ID",
            country_shortname=CountryCode.US,
            owner_type="VALID_OWNER_TYPE",
            owner_id=1,
            default_source=PgpCode.STRIPE,
        ),
    )


def generate_payer_entity() -> PayerDbEntity:
    return PayerDbEntity(
        id=uuid.uuid4(),
        country=CountryCode.US,
        primary_pgp_payer_resource_id="cus_fakeid",
    )


def generate_delete_payer_request(
    id: uuid.UUID = uuid.uuid4(),
    client_request_id: uuid.UUID = uuid.uuid4(),
    consumer_id: int = 1,
    payer_id: Optional[uuid.UUID] = None,
    status: str = DeletePayerRequestStatus.IN_PROGRESS,
    summary: str = "",
    retry_count: int = 0,
    created_at: datetime = datetime.now(timezone.utc),
    updated_at: datetime = datetime.now(timezone.utc),
    acknowledged: bool = False,
) -> DeletePayerRequestDbEntity:
    return DeletePayerRequestDbEntity(
        id=id,
        client_request_id=client_request_id,
        consumer_id=consumer_id,
        payer_id=payer_id,
        status=status,
        summary=summary,
        retry_count=retry_count,
        created_at=created_at,
        updated_at=updated_at,
        acknowledged=acknowledged,
    )
