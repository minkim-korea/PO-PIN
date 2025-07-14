from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('chgReview/main/', views.chgReviewmain, name='chgReviewmain'),
    path('chgReview/view/<int:pk>/', views.chgReviewview, name='chgReviewview'),
    path('chgReview/update/<int:pk>/', views.chgReview_update, name='chgReview_update'),#수정
    path('recent/', views.recent, name='recent'),
    path('write/companion/', views.write_companion, name='write_companion'),
    path('write/proxy/', views.write_proxy, name='write_proxy'),
    path('write/review/', views.write_review, name='write_review'),
    path('write/sharing/', views.write_sharing, name='write_sharing'),
    path('write/status/', views.write_status, name='write_status'),

    path('', views.main, name='main'),
   

    path('companion/', views.companion, name='companion'),
    path('proxy/', views.proxy, name='proxy'),
    path('sharing/', views.sharing, name='sharing'),
    path('status/', views.status, name='status'),

    path('companion/<int:pk>/', views.companion_detail, name='companion_detail'),
    path('sharing/<int:pk>/', views.sharing_detail, name='sharing_detail'),
    path('proxy/<int:pk>/', views.proxy_detail, name='proxy_detail'),
   
]