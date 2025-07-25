from rest_framework.views import exception_handler



# Custom Exception Handler 
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Flatten the validation error response to a string
        if isinstance(response.data, dict) and 'detail' in response.data and isinstance(response.data['detail'], list):
            response.data['detail'] = ' '.join(response.data['detail'])
    return response

