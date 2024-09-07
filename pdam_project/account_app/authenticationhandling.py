from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, AuthenticationFailed):
        response_data = {
            # "detail": "Given token not valid for any token type",
            # "code": "token_not_valid",
            # "messages": [
            #     {
            #         "token_class": "AccessToken",
            #         "token_type": "access",
            #         "message": "Token is invalid or expired"
            #     }
            # ]
            "message":"error",
            "data":{
                "detail":"Given token not valid for any token type",
                "code":"Token is not valid",
                "error_message":"Token is invalid or expired"
            }
        }
        response = Response(response_data, status=exc.status_code)

    return response



