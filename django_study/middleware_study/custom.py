
class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print('Init! ')

    # call은
    def __call__(self, request):

        print('뷰 들어가기 전엥')
        response = self.get_response(request)
        print('뷰 나왔따잉')

        return response
