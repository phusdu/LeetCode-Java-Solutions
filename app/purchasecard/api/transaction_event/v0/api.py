from typing import List

from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_201_CREATED,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError
from app.purchasecard.api.transaction_event.v0.models import (
    TransactionEvent,
    RecordTransactionEventsRequest,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.errors import (
    MarqetaTransactionEventErrorCode,
    MarqetaTransactionErrorCode,
    INPUT_PARAM_INVALID_ERROR_CODE,
)

api_tags = ["TransactionEvent"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_201_CREATED,
    operation_id="RecordTransactionEvents",
    response_model=List[TransactionEvent],
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def record_transaction_events(
    request: RecordTransactionEventsRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        transaction_events = await dependency_container.transaction_event_processor.record_transaction_event(
            marqeta_user_token=request.marqeta_user_token,
            shift_id=request.shift_id,
            anchor_day=request.anchor_day,
        )
        return [TransactionEvent(**event.dict()) for event in transaction_events]
    except PaymentError as e:
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )


@router.get(
    "/last/{delivery_id}",
    status_code=HTTP_200_OK,
    operation_id="GetLatestMarqetaTransactionEvent",
    response_model=TransactionEvent,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_latest_marqeta_transaction_event(
    delivery_id: str,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        internal_transaction_event = await dependency_container.transaction_event_processor.get_latest_marqeta_transaction_event(
            delivery_id=delivery_id
        )
        return TransactionEvent(**internal_transaction_event.dict())
    except PaymentError as e:
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if (
            e.error_code
            == MarqetaTransactionErrorCode.MARQEATA_TRANSACTION_NOT_FOUND_ERROR
            or e.error_code
            == MarqetaTransactionEventErrorCode.MARQETA_TRANSACTION_EVENT_NOT_FOUND_ERROR
        ):
            status_code = HTTP_404_NOT_FOUND
        elif e.error_code == INPUT_PARAM_INVALID_ERROR_CODE:
            status_code = HTTP_400_BAD_REQUEST
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
