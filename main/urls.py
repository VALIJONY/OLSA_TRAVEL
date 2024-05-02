from django.urls import path
from .views import home,about,RASMLAR,Tanlash,CountryDetailView
urlpatterns=[
    path('',home.as_view(),name='home_sahifa'),
    path('about_us/',about.as_view(),name='about'),
    path('gallery/',RASMLAR.as_view(),name='gallery'),
    path('select/',Tanlash.as_view(),name='select'),
    path('countrypic/<id>/',CountryDetailView.as_view(),name='country_detail')
]