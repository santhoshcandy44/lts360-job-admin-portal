from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TrialCheckMiddleware(MiddlewareMixin):
    # Paths that should bypass trial checks (use exact paths or prefixes)
    EXEMPT_PATHS = {
        '/',  # Home page
        '/career-listings/plans/',  # Must match your URL exactly
        '/career-listings/login/',
        '/career-listings/account/',
        '/static/',
        '/media/',
    }

    def process_request(self, request):
        # Skip middleware for exempt paths
        if self._should_skip_check(request):
            return None

        # Only check authenticated users
        if request.user.is_authenticated:
            return self._check_trial_status(request)

        return None

    def _should_skip_check(self, request):
        """Check if request path should be exempt from trial checks"""
        return request.path in self.EXEMPT_PATHS


    def _check_trial_status(self, request):
        """Handle trial expiration logic"""
        try:
            profile = request.user.profile
            if profile.is_trial_active and timezone.now() > profile.trial_end_date:
                profile = request.user.profile
                profile.is_trial_active=False
                profile.save()
                # Use reverse() instead of hardcoded path
                return HttpResponseRedirect(reverse('plans'))
        except AttributeError:
            # Skip if user has no profile
            pass
        return None