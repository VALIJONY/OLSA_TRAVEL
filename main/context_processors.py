from datetime import date

from django.conf import settings


def site(request):
    return {"site_name": settings.SITE_NAME, "currency_label": settings.CURRENCY_LABEL, "year": date.today().year}
