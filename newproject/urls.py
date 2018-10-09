"""newproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from newapp import views
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls) , url('^users/', include('accounts.urls')),
    url('boardImage_upload/', views.boardImage_upload),
    url('shelfImage_upload/', views.shelfImage_upload),
    url('my_shelf_images/',views.load_shelf_images),
    url('my_board_images/',views.load_board_images),
    url(r'^img/$',views.image_urls),
    url(r'^filter_request/brand/$' , views.dropdown_webapp_brands),
    url(r'^filter_request/region/$' , views.dropdown_webapp_region),
    url(r'^filter_request/userid/$' , views.dropdown_webapp_userid),
    url(r'^filter_request/outlet/$' , views.dropdown_webapp_locality),
    url('nearby_stores/' , views.location),
    url(r'^charts_brand/$',views.charts_brand),
    url(r'^charts_region/$',views.charts_region),
    url(r'^total_number/$',views.total_number),
    url(r'^pie_data/$',views.pie_chart),
    url(r'current_address/$',views.return_address),
    url(r'add_outlet/$',views.add_NewOutlet),
    url(r'database_query/', views.getData)
]