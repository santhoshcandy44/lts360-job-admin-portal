import copy
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin


class TokenValidationMiddleware(MiddlewareMixin):

    def process_request(self, request):

        # Skip authentication for specific paths
        if request.path in [ '/','/admin/',  reverse('login_view'), reverse('logout_view')]:
            return None

        try:
            match = resolve(request.path_info)
            view_module = match.func.__module__

            if view_module.startswith('job_portal_app'):
                user = request.user
                if request.user.is_anonymous and not request.user.is_authenticated:
                    print("Anonymous")
                    return self.redirect_to_login(request)
                else:
                    if user.is_terminated:
                        if request.path in [reverse('account_terminated'), reverse('account')]:
                            return None
                        return HttpResponseRedirect(reverse('account_terminated'))

        except Resolver404:
            return None
        except:
            return None

        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        # No tokens found - redirect to login
        if not access_token and not refresh_token:
            print("Both tokens not found")
            return self.redirect_to_login(request)
        if not refresh_token:
            print("Tokens not found")
            return self.redirect_to_login(request)

        try:
            # If access token exists, try to verify it
            if access_token:
                data = jwt.decode(access_token, settings.ACCESS_TOKEN_SECRET, algorithms=["HS256"])
                request.user_id = data['userId']
                return None
            else:
                print("Missing refresh token: refreshing")
                # Access token missing → try refresh
                return self.handle_expired_token(request, refresh_token)

        except jwt.ExpiredSignatureError:
            # Access token expired → try refresh
            return self.handle_expired_token(request, refresh_token)

        except jwt.InvalidTokenError:
            # Token is malformed or tampered
            return self.redirect_to_login(request)

    def handle_expired_token(self, request, refresh_token):
        try:
            # Verify refresh token
            payload = jwt.decode(refresh_token, settings.REFRESH_TOKEN_SECRET, algorithms=["HS256"])
            # Generate new tokens
            new_access_token = self.create_access_token(payload['userId'], payload['email'])
            new_refresh_token = self.create_refresh_token(payload['userId'], payload['email'])

            # Create cloned request with new tokens
            cloned_request = self.clone_request_with_tokens(request, new_access_token, new_refresh_token)

            response = (HttpResponseRedirect(cloned_request.get_full_path())if cloned_request.method == 'GET' else self.get_response(cloned_request) )

            return self.add_tokens_to_response(response, new_access_token, new_refresh_token)


        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Clear invalid tokens and redirect to login
            return self.redirect_to_login(request)

    def clone_request_with_tokens(self, original_request, access_token, refresh_token):
        """Clone the request with new tokens while preserving CSRF in both cookies and form data"""
        cloned_request = copy.copy(original_request)

        # Clone cookies and preserve CSRF
        cloned_request.COOKIES = original_request.COOKIES.copy()
        cloned_request.COOKIES.update({
            'access_token': access_token,
            'refresh_token': refresh_token
        })

        # Build new cookie header preserving existing cookies
        cookies = [
            f'csrftoken={original_request.COOKIES.get("csrftoken", "")}',
            f'sessionid={original_request.COOKIES.get("sessionid", "")}',
            f'access_token={access_token}',
            f'refresh_token={refresh_token}'
        ]
        cloned_request.META['HTTP_COOKIE'] = '; '.join(cookies)

        # Clone POST data including CSRF token
        if original_request.method == 'POST':
            # Preserve content type for proper parsing
            content_type = original_request.META.get('CONTENT_TYPE', '')
            cloned_request.META['CONTENT_TYPE'] = content_type

            # Create mutable POST data copy
            cloned_request.POST = original_request.POST.copy()
            cloned_request.POST._mutable = True

            # Ensure CSRF token is present in POST data
            if 'csrfmiddlewaretoken' not in cloned_request.POST:
                csrf_token = cloned_request.COOKIES.get('csrftoken', '')
                cloned_request.POST['csrfmiddlewaretoken'] = csrf_token

            # Clone files if they exist
            if hasattr(original_request, '_files'):
                cloned_request._files = original_request._files.copy()

            # Make POST immutable after modifications
            cloned_request.POST._mutable = False

        # Preserve CSRF headers
        cloned_request.META['CSRF_COOKIE'] = original_request.META.get('CSRF_COOKIE', '')
        cloned_request.META['HTTP_X_CSRFTOKEN'] = original_request.META.get('HTTP_X_CSRFTOKEN', '')

        return cloned_request




    def add_tokens_to_response(self, response, access_token, refresh_token):
        """Add tokens to response cookies"""
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite='Strict',
            max_age=15 * 60  # 15 minutes in seconds
        )
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite='Strict',
            max_age=90 * 24 * 60 * 60  # 90 days in seconds
        )
        return response

    def create_access_token(self, user_id, email, role='User', sign_up_method='web'):
        """
        Create a new access token with an expiration time.
        """
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id_str,  # subject (user's unique identifier)
            'userId': user_id,
            'email': email,
            'role': role,
            'signUpMethod': sign_up_method,
            'iat': now,  # issued at time
            'exp': now + timedelta(minutes=15)
        }

        return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")

    def create_refresh_token(self, user_id, email, role='User', sign_up_method='web'):
        """
        Create a new refresh token with a longer expiration time.
        """
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id_str,  # subject (user's unique identifier)
            'userId': user_id,
            'email': email,
            'role': role,
            'signUpMethod': "web",
            'iat': now,  # issued at time
            'exp': now + timedelta(days=90)
        }
        return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm="HS256")

    def redirect_to_login(self, request):
        if request.user.is_authenticated:
            logout(request)
        """Redirect to login with original request path preserved"""
        login_url = reverse('login_view')
        redirect_url = f"{login_url}?next={request.get_full_path()}"
        return HttpResponseRedirect(redirect_url)

    # Token creation methods remain the same as in original code



