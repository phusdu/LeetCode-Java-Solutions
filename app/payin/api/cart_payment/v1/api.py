from datetime import datetime
from typing import Optional, Tuple, Union
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.payin.api.cart_payment.v1.converter import to_internal_cart_payment
from app.payin.api.cart_payment.v1.request import (
    CreateCartPaymentRequestV1,
    UpdateCartPaymentRequestV1,
)
from app.payin.api.commando_mode import commando_route_dependency
from app.payin.core.cart_payment.model import CartPayment, CartPaymentList
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.payment_method.types import CartPaymentSortKey
from app.payin.core.types import PayerReferenceIdType

api_tags = ["CartPaymentV1"]
router = APIRouter()


@router.post(
    "/cart_payments",
    response_model=CartPayment,
    status_code=HTTP_201_CREATED,
    operation_id="CreateCartPayment",
    tags=api_tags,
)
async def create_cart_payment(
    cart_payment_request: CreateCartPaymentRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Create a cart payment.

    - **payer_id**: DoorDash payer_id or stripe_customer_id
    - **amount**: [int] amount in cents for the payment.  Must be greater than 0.
    - **payment_country**: [string] country ISO code for where payment is happening.  Example: "US".
    - **currency**: [string] currency for the payment.  Must be a doordash supported currency.  Example: "usd".
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **delay_capture**: [bool] whether to capture immediately or delay
    - **idempotency_key**: [string] idempotency key to submit the payment
    - **client_description** [string] client description
    - **metadata** [json object] key-value map for client specified metadata.  Not interpreted, but stored info with cart_payment.
    - **correlation_ids** [json object] Container for referential information to store along with the payment.
    - **correlation_ids.reference_id **- [string] Identifier of external entity this payment is for.  Currently supported: numeric order ID (pass in order ID within this string).
    - **correlation_ids.reference_type **- [string] Type of external identifier provided.  Currently supported: numeric model type ID (pass in type ID within this string).
    - **payer_statement_description** [string] Description that shows up for charge on customer credit card bill.  Max length 22 characters.
    - **split_payment** [json object] information for flow of funds
    - **split_payment.payout_account_id** [string] merchant's payout account id. Now it is stripe_managed_account_id
    - **split_payment.application_fee_amount** [int] fees that we charge merchant on the order

    """

    log.info("Creating cart_payment for payer", payer_id=cart_payment_request.payer_id)

    cart_payment = await cart_payment_processor.create_cart_payment_v1(
        # TODO: this should be moved above as a validation/sanitize step and not embedded in the call to processor
        request_cart_payment=to_internal_cart_payment(cart_payment_request),
        idempotency_key=cart_payment_request.idempotency_key,
        payment_country=cart_payment_request.payment_country,
        currency=cart_payment_request.currency,
        payment_method_token=cart_payment_request.payment_method_token,
    )

    log.info(
        "Created cart_payment",
        cart_payment_id=cart_payment.id,
        payer_id=cart_payment.payer_id,
    )
    # Legacy info not returned for new V1 API
    return cart_payment


@router.post(
    "/cart_payments/{cart_payment_id}/adjust",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="AdjustCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def update_cart_payment(
    cart_payment_id: UUID,
    cart_payment_request: UpdateCartPaymentRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Adjust amount of an existing cart payment.

    - **cart_payment_id**: unique cart_payment id
    - **payer_id**: DoorDash payer_id
    - **amount**: [int] The new amount to use for the cart payment, in cents.  This is the new amount (not delta).  Must be greater than 0.
    - **payer_country**: [string] payer's country ISO code
    - **idempotency_key**: [string] idempotency key to sumibt the payment
    - **client_description** [string] client description
    - **split_payment** [json object] Optional, new split payment to use for the payment
    """
    log.info("Updating cart_payment", cart_payment_id=cart_payment_id)
    cart_payment = await cart_payment_processor.update_payment(
        idempotency_key=cart_payment_request.idempotency_key,
        cart_payment_id=cart_payment_id,
        amount=cart_payment_request.amount,
        client_description=cart_payment_request.client_description,
        split_payment=cart_payment_request.split_payment,
    )
    log.info(
        "Updated cart_payment",
        cart_payment_id=cart_payment.id,
        payer_id=cart_payment.payer_id,
    )
    return cart_payment


@router.post(
    "/cart_payments/{cart_payment_id}/cancel",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="CancelCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def cancel_cart_payment(
    cart_payment_id: UUID,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Cancel an existing cart payment.  If the payment method associated with the cart payment was
    charged, a full refund is issued.

    - **cart_payment_id**: ID of cart payment to cancel.
    """
    log.info("Cancelling cart_payment", cart_payment_id=cart_payment_id)
    cart_payment = await cart_payment_processor.cancel_payment(
        cart_payment_id=cart_payment_id
    )
    log.info("Cancelled cart_payment", cart_payment_id=cart_payment_id)
    return cart_payment


@router.get(
    "/cart_payments",
    response_model=CartPaymentList,
    status_code=HTTP_200_OK,
    operation_id="ListCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def list_cart_payments(
    payer_id: Optional[str] = None,
    payer_reference_id: Optional[str] = None,
    payer_reference_id_type: Optional[PayerReferenceIdType] = None,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
    created_at_gte: Optional[datetime] = None,
    created_at_lte: Optional[datetime] = None,
    sort_by: CartPaymentSortKey = CartPaymentSortKey.CREATED_AT,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
) -> CartPaymentList:
    try:
        return await cart_payment_processor.list_cart_payments(
            payer_id=payer_id,
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
            reference_id=reference_id,
            reference_type=reference_type,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
            sort_by=sort_by,
        )
    except PaymentError:
        log.warn("[list_cart_payments] PaymentError")
        raise


@router.get(
    "/cart_payments/{cart_payment_id}",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="GetCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def get_cart_payment(
    cart_payment_id: UUID,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Get an existing cart payment.
    - **cart_payment_id**: ID of cart payment.
    """
    log.info("Getting cart payment", cart_payment_id=cart_payment_id)
    cart_payment = await cart_payment_processor.get_cart_payment(
        cart_payment_id=cart_payment_id
    )
    log.info("Cart payment retrieved", cart_payment_id=cart_payment_id)
    return cart_payment


@router.post(
    "/cart_payments/upsert",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    responses={HTTP_201_CREATED: {"model": CartPayment}},
    operation_id="UpsertCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def upsert_cart_payment(
    cart_payment_request: CreateCartPaymentRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
) -> Union[JSONResponse, CartPayment]:
    """
    Create a new cart payment or update an existing cart payment by reference id.

    - **payer_id**: DoorDash payer_id or stripe_customer_id
    - **amount**: [int] amount in cents for the payment.  Must be greater than 0.
    - **payment_country**: [string] country ISO code for where payment is happening.  Example: "US".
    - **currency**: [string] currency for the payment.  Must be a doordash supported currency.  Example: "usd".
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **delay_capture**: [bool] whether to capture immediately or delay
    - **idempotency_key**: [string] idempotency key to submit the payment
    - **client_description** [string] client description
    - **metadata** [json object] key-value map for client specified metadata.  Not interpreted, but stored info with cart_payment.
    - **correlation_ids** [json object] Container for referential information to store along with the payment.
    - **correlation_ids.reference_id **- [string] Identifier of external entity this payment is for.  Currently supported: numeric order ID (pass in order ID within this string).
    - **correlation_ids.reference_type **- [string] Type of external identifier provided.  Currently supported: numeric model type ID (pass in type ID within this string).
    - **payer_statement_description** [string] Description that shows up for charge on customer credit card bill.  Max length 22 characters.
    - **split_payment** [json object] information for flow of funds
    - **split_payment.payout_account_id** [string] merchant's payout account id. Now it is stripe_managed_account_id
    - **split_payment.application_fee_amount** [int] fees that we charge merchant on the order
    """
    reference_id: str = cart_payment_request.correlation_ids.reference_id
    reference_type: str = cart_payment_request.correlation_ids.reference_type
    upsert_cart_payment_response: Tuple[
        CartPayment, bool
    ] = await cart_payment_processor.upsert_cart_payment(
        reference_id=reference_id,
        reference_type=reference_type,
        idempotency_key=cart_payment_request.idempotency_key,
        request_cart_payment=to_internal_cart_payment(
            cart_payment_request=cart_payment_request
        ),
        currency=cart_payment_request.currency,
        payment_country=cart_payment_request.payment_country,
        dd_stripe_card_id=cart_payment_request.dd_stripe_card_id,
    )
    cart_payment, updated = upsert_cart_payment_response
    if not updated:
        return JSONResponse(
            status_code=HTTP_201_CREATED, content=jsonable_encoder(cart_payment)
        )
    return cart_payment
