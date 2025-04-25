from os.path import basename

from rest_framework import  routers
from django.contrib.auth.views import  LoginView , LogoutView
from  .views import  *
from django.urls import path, re_path, include
router  = routers.DefaultRouter()

router.register('users',UserViewSet,basename='users') #basename dùng trên FE
router.register('accounts',AccountViewSet,basename='accounts')
router.register('alumni_accounts',AlumniAccountViewSet,basename='alumni_accounts')
router.register('post',PostViewSet,basename='post')
router.register('post_images',PostImageViewSet,basename='post_images')
router.register('post_reaction',PostReactionViewSet,basename='post_reaction')
router.register('comment',CommentViewSet,basename='comment')
router.register('post_invitations',PostInvitationViewSet,basename='post_invitations')
router.register('post_survey',PostSurveyViewSet,basename='post_survey')
router.register('survey_question',SurveyQuestionViewSet,basename='survey_question')

router.register('survey_response',SurveyResponseViewSet,basename='survey_response')
router.register('survey_answer',SurveyAnswerViewSet,basename='survey_answer')
router.register('room',RoomViewSet,basename='room')
router.register('group',GroupViewSet,basename='group')
router.register('message',MessageViewSet,basename='message')
urlpatterns = [
    path('',include(router.urls)),
    path('home/',HomeView.as_view(),name='home'),
    path('home/login/',LoginView.as_view()),
    path('home/logout',LogoutView.as_view(),name='logout'),
    path('chat/', index),
    path("chat/<str:room_name>/", room, name="room"),

    #Thống kê nằm ở đây
    #Thêm đếm cho user ->
    path('stats/', statistics_view, name='stats'),
    path('export_excel/', export_statistics_to_excel, name='export_excel'),

    ]