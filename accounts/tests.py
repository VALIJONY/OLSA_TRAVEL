from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import tokens
from .models import RefreshToken

User = get_user_model()
ACCESS, REFRESH = settings.JWT["ACCESS_COOKIE"], settings.JWT["REFRESH_COOKIE"]


class JWTFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("ali", password="s3cret-pass!", first_name="Ali")

    def login(self):
        return self.client.post(reverse("accounts:login"), {"username": "ali", "password": "s3cret-pass!"})

    def test_login_sets_httponly_cookies_and_no_session(self):
        response = self.login()
        self.assertRedirects(response, reverse("accounts:profile"), fetch_redirect_response=False)
        for name in (ACCESS, REFRESH):
            self.assertTrue(response.cookies[name]["httponly"])
            self.assertEqual(response.cookies[name]["samesite"], "Lax")
        self.assertNotIn("sessionid", response.cookies)
        self.assertEqual(RefreshToken.objects.filter(user=self.user).count(), 1)

    def test_wrong_password_shows_error_without_cookies(self):
        response = self.client.post(reverse("accounts:login"), {"username": "ali", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(ACCESS, response.cookies)

    def test_access_token_authenticates_profile(self):
        self.login()
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Salom, Ali.")

    def test_profile_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")

    def test_expired_access_is_refreshed_transparently_and_rotates(self):
        self.login()
        old_refresh = self.client.cookies[REFRESH].value
        self.client.cookies[ACCESS] = jwt.encode(
            {"sub": str(self.user.pk), "typ": "access", "jti": "x", "iat": timezone.now() - timedelta(hours=2),
             "exp": timezone.now() - timedelta(hours=1)},
            settings.JWT["SIGNING_KEY"], algorithm="HS256",
        )
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(ACCESS, response.cookies)
        self.assertNotEqual(response.cookies[REFRESH].value, old_refresh)
        self.assertEqual(RefreshToken.objects.filter(revoked_at__isnull=True).count(), 1)
        self.assertEqual(RefreshToken.objects.count(), 2)

    @override_settings(JWT={**settings.JWT, "REUSE_GRACE_SECONDS": 0})
    def test_reused_refresh_token_revokes_whole_family(self):
        self.login()
        stolen = self.client.cookies[REFRESH].value
        del self.client.cookies[ACCESS]
        self.client.get(reverse("accounts:profile"))  # rotatsiya: `stolen` endi eski
        fresh = self.client.cookies[REFRESH].value

        self.client.cookies.clear()
        self.client.cookies[REFRESH] = stolen
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)  # avtorizatsiya yo'q
        self.assertFalse(RefreshToken.objects.active().exists())  # yangi token ham bekor qilindi
        with self.assertRaises(tokens.TokenError):
            tokens.rotate(fresh)

    def test_parallel_request_within_grace_is_authenticated_without_new_cookies(self):
        self.login()
        stale = self.client.cookies[REFRESH].value
        del self.client.cookies[ACCESS]
        self.client.get(reverse("accounts:profile"))
        self.client.cookies.clear()
        self.client.cookies[REFRESH] = stale
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(REFRESH, response.cookies)

    def test_tampered_tokens_are_rejected_and_cookies_cleared(self):
        self.client.cookies[ACCESS] = "abc.def.ghi"
        self.client.cookies[REFRESH] = "abc.def.ghi"
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[ACCESS].value, "")

    def test_access_token_cannot_be_used_as_refresh(self):
        pair = tokens.issue_pair(self.user)
        with self.assertRaises(tokens.TokenError):
            tokens.rotate(pair.access)

    def test_logout_requires_post_revokes_and_clears(self):
        self.login()
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("main:home"), fetch_redirect_response=False)
        self.assertEqual(response.cookies[REFRESH].value, "")
        self.assertFalse(RefreshToken.objects.active().exists())

    def test_logout_everywhere_revokes_other_sessions(self):
        tokens.issue_pair(self.user)  # boshqa qurilma
        self.login()
        self.client.post(reverse("accounts:logout"), {"everywhere": "1"})
        self.assertFalse(RefreshToken.objects.active().exists())

    def test_next_redirect_rejects_foreign_hosts(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "ali", "password": "s3cret-pass!", "next": "https://evil.example/"}
        )
        self.assertRedirects(response, reverse("accounts:profile"), fetch_redirect_response=False)

    def test_login_is_throttled_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "ali", "password": "bad"})
        response = self.login()  # to'g'ri parol ham bloklanadi
        self.assertNotIn(ACCESS, response.cookies)
        self.assertContains(response, "Urinishlar juda ko&#39;p", html=False)

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "vali", "first_name": "Vali", "email": "",
            "password1": "Tr4vel-Secure-99", "password2": "Tr4vel-Secure-99",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(REFRESH, response.cookies)
        self.assertTrue(User.objects.filter(username="vali").exists())

    def test_deactivated_user_loses_access(self):
        self.login()
        self.user.is_active = False
        self.user.save()
        del self.client.cookies[ACCESS]
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 302)
