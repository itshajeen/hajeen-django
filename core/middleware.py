from django.utils import translation

# Custom Middleware for accept lanuage in request header 
class CustomLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # get lang from headers if exist 
        language = request.headers.get('Accept-Language', None)
        if language:
            language_code = language.split(',')[0]
            translation.activate(language_code)
            request.LANGUAGE_CODE = language_code

        response = self.get_response(request)
        return response