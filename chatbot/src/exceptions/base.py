import logging

from fastapi import HTTPException, status


class DetailedHTTPException(HTTPException):
    """
    Base class for all HTTP exceptions so that you don't need to repeat the __init__ method
    """

    STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR
    DETAIL = "Server error"

    def __init__(self, **kwargs) -> None:
        self.DETAIL = kwargs.get("detail", self.DETAIL)
        kwargs.pop("detail", None)
        super().__init__(
            status_code=self.STATUS_CODE, detail=self.DETAIL, **kwargs
        )


class PermissionDenied(DetailedHTTPException):
    STATUS_CODE = status.HTTP_403_FORBIDDEN
    DETAIL = "Permission denied"


class NotFound(DetailedHTTPException):
    STATUS_CODE = status.HTTP_404_NOT_FOUND


class BadRequest(DetailedHTTPException):
    STATUS_CODE = status.HTTP_400_BAD_REQUEST
    DETAIL = "Bad Request"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class NotAuthenticated(DetailedHTTPException):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DETAIL = "User not authenticated"

    def __init__(self) -> None:
        super().__init__(headers={"WWW-Authenticate": "Bearer"})


class InternalServerError(DetailedHTTPException):
    STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR
    DETAIL = "Internal Server Error"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class ServerError(InternalServerError):
    def __init__(self, msg: str):
        super().__init__()
        self.detail = msg
        logging.error(msg)


class EntityWithSameNameExists(BadRequest):
    def __init__(self, entity: str, entity_name: str):
        super().__init__()
        self.detail = f"{entity} with name = {entity_name} already exists"
        logging.error(self.detail)


class EntityNotFound(NotFound):
    def __init__(self, entity: str, entity_id: str):
        super().__init__()
        self.detail = f"{entity} with id = {entity_id} not found"
        logging.error(self.detail)


class EntityWithNameNotFound(NotFound):
    def __init__(self, entity: str, entity_name: str):
        super().__init__()
        self.detail = f"{entity} with name = {entity_name} not found"
        logging.error(self.detail)


class IllegalArgumentException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        logging.error(msg)
