import logging

from inapppy import AppStoreValidator, InAppPyValidationError

logger = logging.getLogger(__name__)


class IOSValidator:
    def __init__(self, credentials):
        self.bundle_id = credentials.get('ios_app_bundle_id')

    def validate(self, purchase_token, retry_on_sandbox, exclude_old_transactions):
        """
        Takes purchase token and product as arguments and validates that
        product is already purchased from App Store.
        """
        validator = AppStoreValidator(self.bundle_id, auto_retry_wrong_env_request=retry_on_sandbox)

        try:
            result = validator.validate(
                purchase_token,
                exclude_old_transactions=exclude_old_transactions
            )
        except InAppPyValidationError as ex:
            logger.error('Purchase validation failed %s', ex.raw_response)
            result = {'error': ex.raw_response}

        return result
