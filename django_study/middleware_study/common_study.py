import re    # 정규식 클래스
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_managers
from django.http import HttpResponsePermanentRedirect
from django.urls import is_valid_path
from django.utils.deprecation import MiddlewareMixin # 예전 미들웨어랑 지금 커먼미들웨어랑 이어주는 역할
from django.utils.http import escape_leading_slashes

"""
대표적인 커먼미들웨어를 따라써보믄서 타고타고 겅부
이것만 따라 쓰고 다른 미들웨어는 타고타고 코드 뜯어봄
"""
class CommonMiddlewareStudy(MiddlewareMixin):
    """
    기본적인 것들을 수행하는 미들웨어이다.
        - settings.DISALLOWED_USER_AGENTS에 세팅된 User-Agents의 출입을 막는다.
        - URL을 다시 써준다. APPEND_SLASH, PREPEND_WWW 에 세팅된 것을 기준으로 슬래쉬를 붙이거나 www같은 것들을 다시 써줌
    위의 것들은 CommonMiddleware를 서브클래싱하거나 response_redirect_class 어트리뷰트를 오버라이딩해서 커스터마이징 가능하다.
    """
    response_redirect_class = HttpResponsePermanentRedirect

    def process_request(self, request):
        """
        들어오면 안되는 유저 거르고 URL을 다시 써준다.
        """

        # 거부된 User-Agents 체크 (settings에 DISALLOWED_USER_AGENTS = [] 인데 regex사용했으니깐 )
        user_agent = request.META.get('HTTP_USER_AGENT')
        if user_agent is not None:
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex(user_agent):
                    raise PermissionDenied('Forbidden user agent')

        # settings.PREPEND_WWW를 보고 리다이렉트 체크
        host = request.get_host()
        must_prepend = settings.PREPEND_WWW and host and not host.startswith('www.')
        redirect_url = ('%s://www.%s' % (request.scheme, host)) if must_prepend else ''

        # 슬래시 추가 되어야 하는지 체크하고 슬래시 추가해줌.
        if self.should_redirect_with_slash(request):
            path = self.get_full_path_with_slash(request)
        else:
            path = request.get_full_path()

        # 리다이렉트 필요하면 해줌
        if redirect_url or path != request.get_full_path():
            redirect_url += path
            return self.response_redirect_class(redirect_url)

    def should_redirect_with_slash(self, request):
        """
        settings.APPEND_SLASH가 참이면 참을 리턴하고
        request 경로가 유효하게끔 슬래쉬를 붙여준다.
        """
        if settings.APPEND_SLASH and not request.path_info.endswith('/'):
            urlconf = getattr(request, 'urlconf', None)
            if not is_valid_path(request.path_info, urlconf):
                match = is_valid_path('%s/' % request.path_info, urlconf)
                if match:
                    view = match.func
                    return getattr(view, 'should_append_slash', True)
        return False

    def get_full_path_with_slash(self, request):
        """
        슬래시가 붙음에 따라 request의 풀 경로를 리턴한다.
        settings.DEBUG가 참이고 request.method가 POST, PUT, PATCH이면 런타임에러를 뿜는다.
        """
        new_path = request.get_full_path(force_append_slash=True)
        # relative url들의 구성을 방지함 (relative url = https://www.w3.org/TR/WD-html40-970917/htmlweb.html)
        new_path = escape_leading_slashes(new_path)
        if settings.DEBUG and request.method in ('POST', 'PUT', 'PATCH'):
            raise RuntimeError(
                "니는 지금 %(method)로 호출했는데 URL이 슬래쉬로 안 끝나고 APPEND_SLASH 세팅이 되어있엉"
                "장고는 %(method)의 데이터를 가지고 슬래시 URL로 리디렉션이 안 돼!"
                "%(url)를 가리키도록 양식을 변경하거나 setting에서 APPEND_SLASH=False로 세팅하세영" % {
                    'method': request.method,
                    'url': request.get_host() + new_path,
                }
            )
        return new_path

    def process_response(self, request, response):
        """
        응답의 코드가 404이면, should_redirect_with_slash()가 참일 때
        슬래시가 붙은 경로로 리디렉션할 수 있게한다.
        """
        # 주어진 URL이 "Not Found"이면 슬래쉬 붙은 경로로 리디렉션해야할지 체크
        if response.status_code == 404 and self.should_redirect_with_slash(request):
            return self.response_redirect_class(self.get_full_path_with_slash(request))

        # 세팅이 안 되어있는 비스트리밍 response에 Conent-Length를 추가해준다.
        if not response.streaming and not response.has_header('Content-Length'):
            response.headers['Content-Length'] = str(len(response.content))

        return response

class BrokenLinkEmailsMiddlewareStudy(MiddlewareMixin):

    def process_response(self, request, response):
        """404 NOT FOUND 가 뜨면 깨진 링크를 이메일로 알려준다."""
        if response.status_code == 404 and not settings.DEBUG:
            domain = request.get_host()
            path = request.get_full_path()
            referer = request.META.get('HTTP_REFERER', '')

            if not self.is_ignorable_request(request, path, domain, referer):
                ua = request.META.get('HTTP_USER_AGENT', '<none>')
                ip = request.META.get('REMOTE_ADDR', '<none>')
                mail_managers(
                    "Broken %slink on %s" % (
                        ('INTERNAL' if self.is_internal_request(domain, referer) else ''),
                        domain
                    ),
                    "Referer: %s\nRequested URL: %s\nUser agnet: %s\n"
                    "IP address: %s\n" % (referer, path, ua, ip),
                    fail_silently=True,
                )
        return response

    def is_internal_request(self, domain, referer):
        """
        referring URL이 최근 request와 똑같은 도메인이면 참을 리턴한다.
        """
        # 다른 서브도메인들은 다른 도메인으로 다룸
        return bool(re.match("^https?://%s/" % re.escape(domain), referer))

    def is_ignorable_reqeust(self, request, uri, domain, referer):
        """
        request가 프로젝트 세팅이나 특별한 상황에 의해 사이트 관리자한테 알려지면 안되는 경우에 True
        """
        if not referer:
            return True

        if settings.APPEND_SLASH and uri.endswith('/') and referer == uri[:-1]:
            return True

        # '?' referer은 서치엔진으로 알려짐
        if not self.is_internal_request(domain, referer) and '?' in referer:
            return True

        # 레퍼러가 최근 url랑 똑같으면 스킴을 무시(봇이라고 생각)
        parsed_referer = urlparse(referer)
        if parsed_referer.netloc in ['', domain] and parsed_referer.path == uri:
            return True

        return any(pattern.search(uri) for pattern in settings.IGNORABLE_404_URLS)
