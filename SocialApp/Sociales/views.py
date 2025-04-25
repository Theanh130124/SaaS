
import json
from asyncio import Future

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, permissions
# Sử dụng permission mới
from .permissions import CanUseAIFeature
# Import hàm AI mới
from .ai_services import generate_single_post_content_ai #, generate_survey_content_ai
from .models import Post, Account # Import Account
from .serializers import PostSerializer
from django.db import transaction # Import transaction

from oauthlib.uri_validate import query
from rest_framework.parsers import JSONParser , MultiPartParser
from .security.security_mes import *
from functools import partial
from lib2to3.fixes.fix_input import context

from pickle import FALSE
from django.db.models import Max

from celery.worker.control import active
from crontab import current_user
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import logout
from Sociales.utils import *
import cloudinary.uploader
from django.views.generic import View
from cloudinary.cache.responsive_breakpoints_cache import instance
from cloudinary.exceptions import NotFound
from cloudinary.uploader import upload
from django.contrib.admin.templatetags.admin_list import pagination
from django.core.exceptions import ObjectDoesNotExist
from dbm import error
from re import search
from django.db.models import Count, Q
from django.db.models.functions import TruncYear
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect
from django.template.defaultfilters import first
from django.utils.decorators import method_decorator
from rest_framework import viewsets , generics , permissions ,status ,parsers
from rest_framework.decorators import action, api_view
from .permissions import *
from rest_framework.viewsets import ModelViewSet
from Sociales.models  import *
from .paginators import MyPageSize, MyPageListReaction
from .serializers import *
from django.db import transaction
from django_redis import get_redis_connection #có localhost trong settings host web nhwos chỉnh
from django.utils.timezone import now
redis_connection = get_redis_connection("default")



#Chỉ cần truyền fields = ['','']
import requests

class FileUploadHelper:
    @staticmethod
    def upload_files(request, fields):
        try:
            upload_res = {}
            url = "https://api.cloudinary.com/v1_1/dxiawzgnz/image/upload"
            # Duyệt qua các trường dữ liệu
            for field in fields:
                file = request.FILES.get(field)  # Dùng request.FILES để lấy file từ form
                if file:
                    files = {'file': file}  # Thêm file vào đối tượng 'files'
                    data = {
                        'upload_preset': 'socialapp',  # Đảm bảo bạn cung cấp tên preset đã tạo
                    }
                    # Gửi POST request tới Cloudinary
                    response = requests.post(url, files=files, data=data)
                    response_data = response.json()
                    if 'secure_url' in response_data:
                        upload_res[field] = response_data['secure_url']
                    else:
                        raise Exception(f"Lỗi từ Cloudinary: {response_data.get('error', 'Không xác định')}")
                else:
                    raise ValueError(f"File không tồn tại cho trường {field}")
            return upload_res
        except Exception as ex:
            # Xử lý các lỗi khác
            raise Exception(f'Phát hiện lỗi: {str(ex)}')





# post user còn lại dành create admin
class UserViewSet(viewsets.ViewSet , generics.RetrieveAPIView, generics.ListAPIView,  generics.CreateAPIView , generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = MyPageSize
    parser_classes = [JSONParser, MultiPartParser] # De upload FIle , và jSOn-> raw
    #http://127.0.0.1:8000/users/?full_name=Đào -> tìm trên họ tên không nằm trên API này dùng cho thanh tìm kiêm Fe
    def get_queryset(self):
        queryset = self.queryset
        full_name = self.request.query_params.get('full_name')
        if action.__eq__('list'):
            if full_name:
                list_names = full_name.split() #-> tách thành list
                for name in list_names:
                 queryset = queryset.filter(Q(first_name__icontains=name) | Q(last_name__icontains=name)) #Có họ ho hoặc tên là được
            return queryset
    def get_permissions(self):
        if self.action.__eq__('create_lecturer'):#do admin tạo lecturer
            return [IsAdminUserRole()]
        if self.action in ['list' , 'retrieve' ,'current_user','account' ,'search_account','recent_search']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), OwnerCurrent()]
        return  [permissions.AllowAny()] #'create_alumni' .... ngta đk đc

    #Gọi acction bên serializers  -> của thằng khác mới không viết ở đây vd như create_alumni
    def get_serializer_class(self):
        if self.action == 'create': #Gọi vậy thì phải gọi thêm generics.CreateAPIView
            return CreateUserSerializer
        # partial_update -> update khi chỉ cập nhật password
        if self.action in ['update', 'partial_update']:
            return UpdateUserSerializer
        return UserSerializer

    #current_user
    @action(methods=['get'],detail=False, url_path='current_user')
    def current_user(self,request):  #request.user -> người dùng htai
        return  Response(UserSerializer(request.user).data,status=status.HTTP_200_OK)

    #Truy vấn ngược -> lấy account dựa trên user id
    @action(methods=['get'], detail=True, url_path='account')
    def get_account_by_user_id(self,request,pk):
        try:
            user = self.get_object()
            account = user.account
            return Response(AccountSerializer(account,context={'request':request}).data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'detail': 'Tài khoản không tồn tại!!!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            error_message = str(e)
            return Response({'Lỗi : ': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #Phải tạo user trước khi tạo account dưới nên không viet create vào bên serializers được
    #Bật detail true được truyền id vào
    @action(methods=['post'],detail=False,url_path='create_alumni')
    def create_alumni(self,request):

        parser_classes = [JSONParser, MultiPartParser]
        try:
            # Xem coi ngày tạo với ngày update
            with transaction.atomic(): #Đảm bảo xảy ra , không thì không lưu
                #Có confirm_status default pending khỏi thêm
                username = request.data.get('username')
                password = request.data.get('password')
                email = request.data.get('email')
                phone_number = request.data.get('phone')
                date_of_birth = request.data.get('date_of_birth')
                first_name = request.data.get('first_name')
                last_name = request.data.get('last_name')
                gender = request.data.get('gender')
                alumni_account_code = request.data.get('alumni_account_code')
                duplicate_username = User.objects.filter(username=username).exists()
                if duplicate_username:
                    return Response({"Username đã tồn tại trong hệ thống": username} , status=status.HTTP_400_BAD_REQUEST)
                duplicate_alumni_account_code = AlumniAccount.objects.filter(alumni_account_code=alumni_account_code).exists()
                if duplicate_alumni_account_code:
                    return Response({"Mã sinh viên đã tồn tại trong hệ thống": username}, status=status.HTTP_400_BAD_REQUEST)
                user = User.objects.create_user(username= username , email=email , first_name=first_name, last_name=last_name )
                user.set_password(password)
                user.save()
                account = Account.objects.create(user=user,gender=gender , role=UserRole.ALUMNI.name,  phone_number=phone_number , date_of_birth=date_of_birth  )
                alumni = AlumniAccount.objects.create(account=account,alumni_account_code=alumni_account_code )
                return  Response(AlumniAccountSerializer(alumni).data,status=status.HTTP_201_CREATED)
        except Exception as e:
            error_message = str(e)
            return Response({'Phát hiện lỗi: ': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(methods=['post'], detail=False , url_path='create_lecturer')
    def create_lecturer(self ,request):
        try:
            with transaction.atomic() :
                username = request.data.get('username')
                #Password ou@123
                email = request.data.get('email')
                first_name = request.data.get('first_name')
                last_name = request.data.get('last_name')
                phone_number = request.data.get('phone')
                date_of_birth = request.data.get('date_of_birth')
                gender = request.data.get('gender')
                # role = UserRole.LECTURER default rồi
                duplicate_username = User.objects.filter(username=username).exists()
                if duplicate_username:
                    return Response({"Username đã tồn tại trong hệ thống": username} , status=status.HTTP_400_BAD_REQUEST)
                user = User.objects.create_user(username=username,email=email  ,first_name = first_name ,last_name = last_name)
                user.set_password('ou@123')
                user.save()
                account = Account.objects.create(user=user , gender = gender , phone_number=phone_number , date_of_birth=date_of_birth )
                send_account_creation_email(user, 'ou@123') #Chưa cài SMTP
                return Response(AccountSerializer(account).data , status=status.HTTP_200_OK)
        except Exception as e:
            error_message = str(e)
            return Response({'Phát hiện lỗi: ': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #Tìm kiếm gần đây  -> de fix sau
    @action(methods=['get'] , detail=False,url_path='recent_search')
    def recent_search(self, request):
        try:
            full_name = self.request.query_params.get('full_name')
            cached_data = redis_connection.get(full_name if full_name is None else '')
            if cached_data:
                #json.loads -> python (dictionary)
                data = json.loads(cached_data)
                return Response(data, status=status.HTTP_200_OK)
            user = User.objects.all()
            if full_name:
                names = full_name.split()
                for name in names:
                    user = user.filter(Q(first_name__icontains=name) | Q(last_name__icontains=name) ,ex=3600) #1 giờ
                    account = Account.objects.filter(user__in=user)
                    #Chuyển dữ liệu thành str Json để lưu bằng dumps
                    redis_connection.set(full_name,json.dumps(AccountSerializer(account,many=True),status=status.HTTP_200_OK))
        except Exception as ex:
            return Response({'Phát hiện lỗi': str(ex)} ,status=status.HTTP_500_INTERNAL_SERVER_ERROR )
    #Khác với get_params ở trên là cái này lấy account trong hệ thống
    @action(methods=['get'] , detail=False ,url_path='search_account')
    def search_account(self,request):
        try:
            full_name = self.request.query_params.get('full_name')
            user = User.objects.all()
            if full_name:
                names = full_name.split()
                for name in names:
                    user = user.filter(Q(first_name__icontains=name) | Q(last_name__icontains=name))
                    account = Account.objects.filter(user__in=user)
                    #Xem coi co nen tach ra thanh UserSerializerForSearch khong ?
            else:
                account = Account.objects.none()
            return Response(AccountSerializer(account, many=True).data, status=status.HTTP_200_OK)
        except Exception as ex :
            return Response({'Phát hiện lỗi': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(methods=['post'],detail=False,url_path='update_last_login')
    def update_last_login(self,request):
        user = request.user
        if user.is_authenticated:
            user.last_login = now()
            user.save()
            return Response({"message": "last_login đã được cập nhật"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Bạn cần phải đăng nhập để cập nhật last_login"},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(methods=['post'],detail=False,url_path='change-password')
    def change_password(self,request):
        user = request.user
        old_password = request.data.get('old_pass')
        new_password = request.data.get('new_pass')
        if not old_password or not new_password:
            return Response({'detail': 'Vui lòng cung cấp mật khẩu cũ và mật khẩu mới.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(old_password):
            return Response({'detail': 'Mật khẩu cũ không đúng.'}, status=status.HTTP_400_BAD_REQUEST)

            # Cập nhật mật khẩu mới
        user.set_password(new_password)
        user.password_changed_at = timezone.now()  # Ghi lại thời gian đổi mật khẩu
        user.save()

        return Response({'detail': 'Đổi mật khẩu thành công.'}, status=status.HTTP_200_OK)
class AccountViewSet( viewsets.ViewSet ,generics.ListAPIView,generics.UpdateAPIView):
    queryset = Account.objects.all() #Xem nếu filter comfirm_status ?
    serializer_class = AccountSerializer
    pagination_class = MyPageSize
    parser_classes = [JSONParser, MultiPartParser]# De upload FIle thì dùng

    def get_permissions(self):
        if self.action in ['list' ,'update' , 'partial_update','get_post_of_account']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
#Xử lý uploadcloud
    def perform_update(self, serializer):
        fields = ['avatar', 'cover_avatar']
        upload_res = {}

        # Kiểm tra từng trường và chỉ upload nếu có file
        for field in fields:
            if field in self.request.FILES:
                upload_res.update(FileUploadHelper.upload_files(self.request, fields=[field]))

        # Cập nhật dữ liệu nếu có file upload
        if upload_res:
            serializer.save(**upload_res)
        else:
            # Nếu không có file nào được upload, vẫn cho phép cập nhật các trường khác
            serializer.save()


    def update(self, request, *args, **kwargs):
        return super().update(request,*args,**kwargs)

    #Xem những bài viết của accout đó
    @action(methods=['get'], detail=True, url_path='post')
    def get_post_of_account(self, request, pk):
        try:
            posts = self.get_object().posts.all().order_by('-created_date','-id')


            # Dùng self.paginate_queryset để tự động lấy pagination_class
            paginated_posts = self.paginate_queryset(posts)

            if paginated_posts is not None:
                serialized_posts = PostSerializer(paginated_posts, many=True, context={'request': request})
                return self.get_paginated_response(serialized_posts.data)

            # Nếu không cần phân trang, trả về toàn bộ danh sách
            serialized_posts = PostSerializer(posts, many=True, context={'request': request})
            return Response(serialized_posts.data)

        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Update trạng thái đăng nhập từ admin cho cựu sv
class AlumniAccountViewSet(viewsets.ViewSet ,generics.ListAPIView , generics.RetrieveAPIView,generics.UpdateAPIView):
    queryset = AlumniAccount.objects.all()
    serializer_class = AlumniAccountSerializer
    pagination_class = MyPageSize
    parser_classes = [JSONParser, MultiPartParser]
    def get_permissions(self):
        if self.action in ['list' ,'update' , 'partial_update', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

class PostViewSet(viewsets.ViewSet,generics.ListAPIView, generics.CreateAPIView , generics.RetrieveAPIView , generics.UpdateAPIView , generics.DestroyAPIView):
    queryset = Post.objects.filter(active=True).order_by('-created_date', '-id')

    serializer_class = PostSerializer
  #Truyền vào do có tự định nghĩa PostOwner
    pagination_class =  MyPageSize
    parser_classes = [JSONParser, MultiPartParser]
    #Thêm vậy để lên trên admin upload -> thì nó sẽ trả ra đường dẫn cloudinary


    def get_serializer_class(self):
        if self.action.__eq__('create'):
            return CreatePostSerializer
        if self.action == 'list':
            return PostForListSerializer
        return PostSerializer
    def get_permissions(self):
        if self.action in ['destroy','update','partial_update']:
            return [PostOwner()]
         # Sử dụng permission mới cho action generate_ai_content
        if self.action == 'generate_ai_content':
            # Yêu cầu đăng nhập VÀ (có gói active HOẶC còn lượt dùng thử)
            return [permissions.IsAuthenticated(), CanUseAIFeature()]
        if  self.action in ['list','retrieve','create','get_comments_in_post','get_image_in_post','get_reaction_detail_in_post',
                            ]:
            return [permissions.IsAuthenticated()]
        return  [permissions.AllowAny()]
    @action(methods=['get'] , detail=True,url_path='comments')
    def get_comments_in_post(self,request,pk):
        try:
            #get_querryset().get(pk=pk) sẽ lấy được bài viết theo pk còn get_object thì không
            comments = self.get_queryset().get(pk=pk).comments.filter(active=True).order_by('-created_date').all() #có khai báo related_name rồi
            paginator = MyPageSize()
            paginated = paginator.paginate_queryset(comments, request)
            serializer = CommentSerializer(paginated, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        except Exception as ex:
            return Response({'Phát hiện lỗi',str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#lấy các hình ảnh của bài viết
    @action(methods=['get'],detail=True,url_path='images')
    def get_image_in_post(self,request,pk):
        try:
            post_images =self.get_queryset().get(pk=pk).post_images.filter(active=True).all()
            paginator = MyPageSize()
            paginated = paginator.paginate_queryset(post_images,request)
            serializer = PostImageSerializer(paginated,many=True,context={'request':request})
            return paginator.get_paginated_response(serializer.data)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#lấy reaction -> nếu không truyền parames nào thì nó sẽ không hiện parmes đó -> đồng thời có thể lọc reaction
    @action(methods=['get'],detail=True,url_path='reactions')
    def get_reaction_detail_in_post(self,request,pk):
        try:
            reaction = request.query_params.get('reaction')
            account_id = request.query_params.get('account')
            post_reactions = PostReaction.objects.filter(post_id=pk) #Nếu không truyền parames gì thì nó hiện list reaction thôi
            if reaction :
                 post_reactions = post_reactions.filter(reaction=reaction)
            if account_id:
                post_reactions = post_reactions.filter(account_id=account_id)
            paginator = MyPageListReaction()
            paginated = paginator.paginate_queryset(post_reactions, request)
            return Response(PostReactionSerializer(paginated,many=True,context={'request':request}).data,status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Tạo bài viết AI
    @action(methods=['post'], detail=False, url_path='generate-ai-content')
    def generate_ai_content(self, request):
        """
        API Endpoint để người dùng tạo 1 bài viết bằng AI dựa trên chủ đề.
        """
        topic = request.data.get('topic')
        if not topic:
            return Response({'detail': 'Vui lòng cung cấp chủ đề (topic).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account = request.user.account
            is_trial_user = not account.has_active_subscription

            # Gọi AI để tạo nội dung 1 bài viết
            post_content = generate_single_post_content_ai(topic)

            new_post = Post.objects.create(
                account=account,
                post_content=post_content,
            )

            if is_trial_user:
                Account.objects.filter(pk=account.pk).update(ai_trial_uses=models.F('ai_trial_uses') + 1)

            return Response(
                {
                    'detail': f'Đã tạo thành công 1 bài viết về chủ đề "{topic}".',
                    'post_content': post_content,
                    'trial_uses_remaining': (Account._meta.get_field("ai_trial_uses").default + 2 - (account.ai_trial_uses + (1 if is_trial_user else 0))) if is_trial_user else None
                },
                status=status.HTTP_201_CREATED
            )

        except Account.DoesNotExist:
            return Response({'detail': 'Không tìm thấy tài khoản người dùng.'}, status=status.HTTP_404_NOT_FOUND)

        except (ConnectionError, ValueError) as e:
            return Response({'detail': f'Lỗi: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# #Dem tat ca reaction tren 1 post
#     @action(methods=['get'],detail=True,url_path='count_reaction')
#     def get_count_reaction(self,request,pk):
#         try:
#             reaction_count = PostReaction.objects.filter(post_id=pk).count()
#             return Response(reaction_count,status=status.HTTP_200_OK)
#         except Exception as ex:
#             return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# #Lấy loại cảm xúc trên 1 bài viết
#     @action(methods=['get'],detail=True,url_path="count_type_reaction")
#     def get_count_type_reaction(self,request,pk):
#         try:
#             #annotate -> truyền id để nó đếm số lượng theo id -> nếu 1 post có nhiều postreaction có thể dùng annostate để đếm cảm xúc
#             reaction_type = PostReaction.objects.filter(post_id=pk).annotate(count=Count('id')).values('reaction','count')
#             return Response(reaction_type,status=status.HTTP_200_OK)
#         except Exception as ex:
#             return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             #values -> chọn thuộc tính lấy
# #dem so binh luan
#     @action(methods=['get'],detail=True,url_path="count_comment")
#     def get_count_comment(self,request,pk):
#         try:
#             count_comment = Comment.objects.filter(post_id=pk).count()
#             return Response(count_comment,status=status.HTTP_200_OK)
#         except Exception as ex:
#             return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#Tối ưu bằng gộp và dùng annotate để group_by -> để chia các reaction có cùng post_id -> thành 1 group_by reaction -> từng loại riêng với count từng loại
    def retrieve(self, request, *args, **kwargs):
        try:
            post =self.get_object()
            comment_count = Comment.objects.filter(post_id = post.id).count()
            #Đến từng loại cảm xúc -> kèm theo số lượng
            reactions =PostReaction.objects.filter(post_id=post.id).annotate(count=Count('reaction')).values('reaction','count') #ở đây nó truyền account thì nó sẽ đếm theo account ,
            total_reactions = PostReaction.objects.filter(post_id=post.id).count()
            serializer = self.get_serializer(post)
            data = serializer.data
            data['comment_count'] =comment_count
            data['reactions'] = reactions
            data['total_reactions'] = total_reactions
            return Response(data,status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PostImageViewSet(viewsets.ViewSet, generics.ListAPIView,
                       generics.UpdateAPIView):
    queryset = PostImage.objects.filter(active=True).all()
    serializer_class = PostImageSerializer
    pagination_class = MyPageSize
    parser_classes = [MultiPartParser, ]
    permission_classes = [permissions.IsAuthenticated]


    def perform_update(self, serializer):
        fields = ['multi_images']
        upload_res = FileUploadHelper.upload_files(self.request, fields=fields)
        serializer.save(**upload_res)

    # 2 thằng này là riêng nha -> dùng lại của mixin
    def perform_create(self, serializer):
        fields = ['multi_images']
        upload_res = FileUploadHelper.upload_files(self.request, fields=fields)
        serializer.save(**upload_res)

    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework import status

    @action(methods=['POST'], detail=False, url_path='upload_multi_images')
    def upload_multi_images(self, request):
        try:
            multi_images = self.request.FILES.getlist('multi_images')
            post = self.request.data.get('post')

            print('multi')
            print(multi_images)

            upload_res = []
            url = "https://api.cloudinary.com/v1_1/dxiawzgnz/image/upload"

            # Duyệt qua từng ảnh và upload riêng biệt
            for img in multi_images:
                files = [('file', img)]  # Thêm file vào danh sách

                # Dữ liệu thêm vào POST request
                data = {
                    'upload_preset': 'socialapp',  # Đảm bảo bạn cung cấp tên preset đã tạo
                }

                # Gửi POST request tới Cloudinary
                response = requests.post(url, files=files, data=data)
                response_data = response.json()

                # Kiểm tra nếu có URL trong dữ liệu trả về
                if response.status_code == 200:
                    secure_url = response_data['secure_url']  # Lấy URL của ảnh
                    upload_res.append(secure_url)

                    # Lưu thông tin ảnh vào database
                    PostImage.objects.create(post_id=post, post_image_url=secure_url)
                else:
                    raise Exception(f"Lỗi từ Cloudinary: {response_data.get('error', 'Không xác định')}")

            return Response(upload_res, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = str(e)
            return Response({'error': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#Post -> Việc xử lý Thả cảm xúc , và hủy
class PostReactionViewSet(viewsets.ViewSet,generics.CreateAPIView,generics.DestroyAPIView ,generics.UpdateAPIView):
    queryset = PostReaction.objects.all()
    serializer_class =  PostReactionSerializer
    pagination_class =  MyPageSize
    parser_classes = [JSONParser, MultiPartParser]
    def get_permissions(self):
        if self.action in ['partial_update','destroy']:
            return [PostReactionOwner()]
        else:
            return [permissions.IsAuthenticated()]
    def get_serializer_class(self):
        if self.action in ['update','partial_update']:
            return PostReactionForUpdateSerializer
        if self.action == 'create':
            return PostReactionForCreateSerializer

        return self.serializer_class
    #Lấy danh sách chi tiết cảm xúc
    @action(methods=['get'],detail=True,url_path='reaction_by_account') #Truyen trên này thì
    def get_reaction_by_account(self,request,pk=None):
        try:
            reactions = PostReaction.objects.filter(account_id=pk) #Truyền vào đây nó so account_id có trong Reaction so với pk mình cho vào
            serializer = PostReactionSerializer(reactions, many=True)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#Create
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            account = request.user.account
            post = serializer.validated_data['post'] #lấy post bên serializer
            existing_reaction = PostReaction.objects.filter(account=account,post=post).first() #Kiểm tra có trùng cảm xúc không
            if existing_reaction: #Có thì parse qua bên serializers vào reaction
                 existing_reaction.reaction = serializer.validated_data['reaction']
                 existing_reaction.save()
                 return Response(self.get_serializer(existing_reaction).data, status=status.HTTP_200_OK)
            else:
                serializer.save(account=account)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#Sửa lại cảm xúc
    def partial_update(self, request, *args, **kwargs):
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)

            if serializer.is_valid():
                # Cập nhật cảm xúc
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #Xóa cả xúc -> nhấn đúp
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # Lấy đối tượng cần xóa
        instance.delete()  # Xóa đối tượng
        return Response(status=status.HTTP_204_NO_CONTENT)

#Bình luận
class CommentViewSet(viewsets.ViewSet,generics.CreateAPIView,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = Comment.objects.filter(active=True).all()
    serializer_class = CommentSerializer
    parser_classes = [JSONParser, MultiPartParser]
#Xem côi còn khóa comment_lock thì không bình luận được
    def get_permissions(self):
        if self.action in ['partial_update','destroy','update']:
            return [CommentOwner()]
        else:
            return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['update','partial_update']:
            return CommentForUpdateSerializer
        if self.action == 'create':
            return CommentForCreateSerializer

    def perform_create(self, serializer):
        fields = ['comment_image_url']
        upload_res = {}

        # Chỉ upload nếu có file trong request
        if any(field in self.request.FILES for field in fields):
            upload_res = FileUploadHelper.upload_files(self.request, fields=fields)

        serializer.save(**upload_res)

    def perform_update(self, serializer):
        fields = ['comment_image_url']
        upload_res = {}

        # Chỉ upload nếu có file trong request
        if any(field in self.request.FILES for field in fields):
            upload_res = FileUploadHelper.upload_files(self.request, fields=fields)

        serializer.save(**upload_res)

#Bài đăng dạng thư mời -> để đăng sự kiện của trường mời các cựu sinh viên

#Destroy -> xóa nguyên bài , update -> update lại thời gian kết thúc
class PostInvitationViewSet(viewsets.ViewSet,generics.ListAPIView,generics.RetrieveAPIView,generics.UpdateAPIView,generics.DestroyAPIView,generics.CreateAPIView):
    queryset =  PostInvitation.objects.order_by('-created_date', '-id')
    serializer_class =  PostInvitationSerializer
    pagination_class =  MyPageSize
    parser_classes = [JSONParser, MultiPartParser]


    def get_permissions(self):
        if self.action in ['partial_update','destroy' , 'create' ,'update','get_alumni','invited_alumni','deleted_alumni',
                           'invite_group','invite_all']:
            return [IsAdminUserRole()] #Chỉ có admin
        else:
            return [permissions.IsAuthenticated()]
    def get_serializer_class(self):
        if self.action == 'create':
            return PostInvitationCreateSerializer
        if self.action in ['update', 'partial_update']:
            return PostInvitationUpdateSerializer
        return self.serializer_class
    #Tạo bài đăng lời mời sẳn tạo post
    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                invitation_data = request.data
                post_content = invitation_data.get('post_content','Bài đăng mời tham gia sự kiện') #Tự động là vậy
                comment_lock = invitation_data.get('comment_lock',False)
                account_id = invitation_data.get('account_id')
            post = Post.objects.create(
            post_content=post_content,
            comment_lock=comment_lock,
            account_id=account_id,
            )
            invitation = PostInvitation.objects.create(
            post=post, #Lọc bỏ 3 trường trong post ra khỏi post_invitation
            **{key: invitation_data[key] for key in invitation_data if
               key not in ['post_content', 'comment_lock', 'account_id']}
            )
            serializer = self.get_serializer(invitation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #Bài đăng chỉ mời cựu sinh viên -> xem danh sách cuự sinh viên đã mời
    @action(methods=['get'],detail=True,url_path='alumni_account')
    def get_alumni(self,request,pk):
        try:
            alumni_acc =self.get_object().filter(active=True).all()
            return  Response(AlumniForInvitationSerializer(alumni_acc,many=True ,context={'request': request}).data ,status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #Mời cựu sinh viên  -> sẳn tạo bài viết lời mời luôn -> gộp API lại
    @action(methods=['post'], detail=True, url_path='alumni')
    def invited_alumni(self, request, pk):
        try:
            with transaction.atomic():
                post_invitation = self.get_object()
                # Truyền ID vào
                list_alumni_id = request.data.get('list_alumni_id', [])
                list_alumni_id = set(list_alumni_id)  # account_id là primary key
                account = AlumniAccount.objects.filter(account_id__in=list_alumni_id)  # So sánh với set nên id__in
                if account.count() != len(list_alumni_id):
                    missing_ids = set(list_alumni_id) - set(account.values_list('account_id', flat=True))  # flat true để trả list
                    raise NotFound(f'Tài khoản với ID {missing_ids} không tồn tại')

                post_invitation.accounts_alumni.add(*account)
                # Lấy danh sách email từ mối quan hệ
                emails = account.values_list('account__user__email', flat=True)
                send_mail_for_post_invited(post_invitation, emails)
                post_invitation.save()

                return Response(PostInvitationSerializer(post_invitation).data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({'Phát hiện lỗi': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #Mời thành viên trong group
    @action(methods=['post'], detail=True, url_path='invite_group')
    def invite_group(self, request, pk):
        try:
            with transaction.atomic():
                post_invitation = self.get_object()
                group_ids = request.data.get('group_ids', [])

                # Lấy các nhóm từ group_ids
                groups = Group.objects.filter(id__in=group_ids)
                if not groups.exists():
                    return Response({'error': 'Không tìm thấy nhóm'}, status=status.HTTP_400_BAD_REQUEST)

                # Lấy danh sách tất cả alumni từ các nhóm
                alumni_accounts = AlumniAccount.objects.filter(account__groups__in=groups).distinct()  # distinct để loại bỏ trùng lặp

                if not alumni_accounts.exists():
                    return Response({'error': 'Không có thành viên nào trong các nhóm này'}, status=status.HTTP_400_BAD_REQUEST)

                # Thêm alumni vào post_invitation
                post_invitation.accounts_alumni.add(*alumni_accounts)

                # Lấy danh sách email
                emails = alumni_accounts.values_list('account__user__email', flat=True)

                # Gửi email mời tham gia
                send_mail_for_post_invited(post_invitation, emails)

                # Lưu thay đổi
                post_invitation.save()

                return Response(PostInvitationSerializer(post_invitation).data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({'Phát hiện lỗi': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], detail=True, url_path='invite_all')
    def invite_all(self, request, pk):
        try:
            with transaction.atomic():
                post_invitation = self.get_object()
                all_accounts = AlumniAccount.objects.all()



                # Thêm tất cả alumni vào post_invitation
                post_invitation.accounts_alumni.add(*all_accounts)
                # Lấy danh sách email
                emails = AlumniAccount.objects.filter( #select_related -> neu can lay ca doi tuong
                    account__user__email__isnull=False
                ).values_list('account__user__email', flat=True)
                #values_list -> neu flat = False va 'id' 'account' -> tra ve dict 2 truong

                # Gửi email
                send_mail_for_post_invited(post_invitation, list(emails))
                post_invitation.save()

            return Response(PostInvitationSerializer(post_invitation).data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['delete'],detail=True,url_path='alumni_account')
    def deleted_alumni(self,request,pk):
        try:
            post_invitation = self.get_object()
            list_alumni_id = request.data.get('list_alumni_id',[])
            account = AlumniAccount.objects.filter(account_id__in=list_alumni_id)
            if account.count() != list_alumni_id.count():
                missing_ids = set(list_alumni_id) - set(account.values_list('account_id', flat=True))  #sữa thành account_id  # flat true để trả list
                raise NotFound(f'Tài khoản với ID {missing_ids} không tồn tại')
            post_invitation.accounts_alumni.remove(*account) # đã fix lại accounts_alumni
            post_invitation.save()
            return Response(PostInvitationSerializer(post_invitation).data, status=status.HTTP_204_NO_CONTENT)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 16-01-2025
#Bài đăng dạng khảo sát admin làm -> Xử lý không đồng bộ trên Fe để tạo được bài viết trc rồi -> tạo ds câu hỏi
class PostSurveyViewSet(viewsets.ViewSet,generics.ListAPIView,generics.CreateAPIView,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = PostSurvey.objects.order_by('-created_date', '-post').all()
    serializer_class =  PostSurveySerializer
    pagination_class =  MyPageSize

    parser_classes = [JSONParser,MultiPartParser]



    def get_permissions(self):
        if self.action in ['partial_update','destroy','update','create' ,'create_survey_questions','check_survey_completed']:
            return [IsAdminUserRole()]
        else:
            return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                invitation_data = request.data
                post_content = invitation_data.get('post_content', 'Bài đăng câu hỏi khảo sát')  # Tự động là vậy
                comment_lock = invitation_data.get('comment_lock', False)
                account_id = invitation_data.get('account_id')
            post = Post.objects.create(
                post_content=post_content,
                comment_lock=comment_lock,
                account_id=account_id,
            )
            survey = PostSurvey.objects.create(
                post=post,  # Lọc bỏ 3 trường trong post ra khỏi post_invitation
                **{key: invitation_data[key] for key in invitation_data if
                   key not in ['post_content', 'comment_lock', 'account_id']}
            )
            serializer = self.get_serializer(survey, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            post_survey = self.get_object()
            # if post_survey.end_time <= post_survey.start_time:
            #     raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu ")
            # if timezone.now() > post_survey.end_time:
            #     raise ValidationError("Không thể cập nhật câu hỏi vì quá thời gian cho phép")
            return super().update(request,*args,**kwargs)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response({"error": str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_serializer_class(self):
        if self.action == 'create':
            return PostSurveyCreateSerializer
        if self.action in ['update', 'partial_update']:
            return PostSurveyCreateSerializer
        if self.action == 'list':
            return PostSurveyForListSerializer
        return self.serializer_class
    #Lấy các câu hỏi của 1 post_survey theo id post
    @action(methods=['get'],detail=True,url_path='survey_question')
    def get_survey_questions(self,request,pk):
        try:
            survey_questions = self.get_object().survey_questions.filter(active=True).all() #Truy vấn ngược lấy ds question trong survey
            return Response(SurveyQuestionSerializer(survey_questions, many=True, context={'request': request}).data,
                            status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #Tạo ra câu hỏi ->
    @action(methods=['post'],detail=True,url_path='create_survey_question')
    def create_survey_questions(self,request,pk):
        try:

            post_survey = self.get_object()
            #Xử lý question_order tự động tăng
            last_qes = SurveyQuestion.objects.filter(post_survey=post_survey).aggregate(Max('question_order'))
            next_qes = last_qes['question_order__max'] + 1 if last_qes['question_order__max'] is not None else 1 # Không có thì là câu hỏi 1
            survey_questions = SurveyQuestion(question_content=request.data['question_content'],
                                              question_order=next_qes, #Thứ tự câu hỏi
                                             post_survey=post_survey,
            is_required = request.data['is_required'], #Bắt buộc tra lời
            survey_question_type = request.data['survey_question_type']) #Có cần check lại này không ?
            survey_questions.save()
            return Response(SurveyQuestionSerializer(survey_questions, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #Thong ke tong ket khao sat
    @action(methods=['post'],detail=True,url_path='check_survey_completed')
    def check_survey_completed(self,request,pk):
        try:
            post_survey = self.get_object()
            account = request.data.get('account')
            survey_response = SurveyResponse.objects.get(post_survey=post_survey,account=account)
            if survey_response:
                return Response(SurveyResponseSerializer(survey_response).data,status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#Các câu hỏi -> Có thể sửa lại -> tạo ra

class SurveyQuestionViewSet(viewsets.ViewSet,generics.ListAPIView ,generics.UpdateAPIView):
    queryset = SurveyQuestion.objects.filter(active=True).all()
    serializer_class = SurveyQuestionSerializer
    pagination_class = MyPageSize
    permission_classes = [IsAdminUserRole] #Cũng chỉ admin mới được thêm câu hỏi
    parser_classes = [JSONParser,MultiPartParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSurveyQuestionSerializer
        if self.action in ['update', 'partial_update']:
            return UpdateSurveyQuestionSerializer
        return self.serializer_class
    #Update lại câu hỏi chỉ trong khoảng thời gian chưa hết end-time
    def update(self, request, *args, **kwargs):
        try:
            survey_question = self.get_object()
            post_survey = survey_question.post_survey

            if timezone.now() > post_survey.end_time:
                raise ValidationError("Không thể cập nhật câu hỏi vì quá thời gian cho phép")
            return super().update(request,*args,**kwargs)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response({"error": str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#Từng câu trả lời cho các câu hỏi  -> 4 câu trả lời cho câu hỏi - Chưa test 21.01.2025
class SurveyQuestionOptionViewSet(viewsets.ViewSet,generics.CreateAPIView,):
    queryset = SurveyQuestionOption.objects.all()
    serializer_class = SurveyQuestionOptionSerializer
    pagination_class = MyPageSize
    permissions_class = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSurveyQuestionOptionSerializer
        if self.action in ['update', 'partial_update']:
            return UpdateSurveyQuestionOptionSerializer
        return self.serializer_class
    #Lấy câu trả lời của câu hỏi đó
    @action(methods=['get'],detail=True,url_path='survey_answer')
    def get_survey_answer(self,request,pk):
        survey_answer = self.get_object().survey_answers.select_related('survey_question','survey_response').all()
        return Response(
            SurveyAnswerSerializerForRelated(survey_answer,many=True,context={'request': request}).data,
            status=status.HTTP_200_OK)
    @action(methods=['post'],detail=True,url_path='add_update_survey_answer')
    def add_or_update_survey_answer(self,request,pk):
        try:
            survey_question_option = self.get_object()
            list_survey_answer_id = request.data.get('list_survey_answer_id',[])
            survey_answers = SurveyAnswer.objects.filter(id__in=list_survey_answer_id)
            if survey_answers.count() != list_survey_answer_id.count():
                missing_ids = set(list_survey_answer_id)-set(survey_answers.values_list('id', flat=True))
                raise NotFound(f"Survey Answer with IDs {missing_ids} do not exist.")
            survey_question_option.survey_answers.add(*survey_answers)
            survey_question_option.save()

            return Response(SurveyQuestionOptionSerializer(survey_question_option).data, status=status.HTTP_201_CREATED)

        except Exception as ex:
            return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SurveyResponseViewSet(viewsets.ViewSet,generics.ListAPIView,generics.RetrieveAPIView, generics.CreateAPIView):
    queryset = SurveyResponse.objects.all()
    serializer_class = SurveyResponseSerializer
    pagination_class = MyPageSize
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]

class SurveyAnswerViewSet(viewsets.ViewSet,generics.ListAPIView,generics.CreateAPIView,generics.UpdateAPIView):
    queryset =  SurveyAnswer.objects.all()
    serializer_class = SurveyAnswerSerializer
    pagination_class = MyPageSize
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSurveyAnswerSerializer
        if self.action in ['update', 'partial_update']:
            return UpdateSurveyAnswerSerializer
        return self.serializer_class



class GroupViewSet(viewsets.ViewSet, generics.ListAPIView,generics.CreateAPIView):
    queryset = Group.objects.order_by('-created_date', '-id')
    serializer_class = GroupSerializer
    pagination_class = MyPageSize
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]

    #Thêm thành viên nhưng chỉ là alumni
    def create(self, request, *args, **kwargs):
        data = request.data
        member_ids = data.get('members',[])
        alumni_accounts = Account.objects.filter(user_id__in=member_ids,role=UserRole.ALUMNI)
        if len(alumni_accounts) != len(member_ids):
            return Response({'error': 'Tất cả thành viên phải có role ALUMNI'}, status=status.HTTP_400_BAD_REQUEST)
        # Tiến hành tạo nhóm
        group_serializer = self.get_serializer(data=data)

        if group_serializer.is_valid():
            group = group_serializer.save()

            # Thêm các thành viên ALUMNI vào nhóm
            group.members.add(*alumni_accounts)

            return Response(group_serializer.data, status=status.HTTP_201_CREATED)

        return Response(group_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Room
class RoomViewSet(viewsets.ViewSet,generics.ListAPIView):
    queryset = Room.objects.filter(active=True).all()
    serializer_class =RoomSerializer
    pagination_class = MyPageSize
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateRoomSerializer
        if self.action in ['partial_update']:
            return RoomSerializer
        return self.serializer_class

    @action(methods=['get'], detail=True, url_path='filter_rooms')
    def filter_rooms(self, request, pk=None):
        try:
            if not pk:
                return Response({'error': 'Không tìm thấy first_user_id trong URL.'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Lọc các room theo first_user_id hoặc second_user_id từ URL
            rooms = Room.objects.filter(
                Q(first_user_id=pk) | Q(second_user_id=pk), active=True
            )

            # Phân trang kết quả
            paginator = MyPageSize()
            paginated = paginator.paginate_queryset(rooms, request)
            serializer = RoomSerializer(paginated, many=True)

            return paginator.get_paginated_response(serializer.data)
        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(methods=['post'], detail=False, url_path='create_multiple_rooms')
    def create_multiple_rooms(self, request):
        try:
            first_user_id = request.data.get('first_user_id')
            if not first_user_id:
                return Response({'error': 'Thêm tài khoản hiện tại vào request'}, status=status.HTTP_400_BAD_REQUEST)

            # Lấy danh sách tất cả người dùng, trừ người dùng hiện tại
            second_users = Account.objects.exclude(user_id=first_user_id)  # Loại bỏ first_user
            created_rooms = []
            for second_user in second_users:
                # Kiểm tra nếu phòng đã tồn tại
                room_exists = Room.objects.filter(
                    Q(first_user_id=first_user_id, second_user_id=second_user.user_id) |
                    Q(first_user_id=second_user.user_id, second_user_id=first_user_id)
                ).exists()

                if not room_exists:
                    # Tạo room mới
                    room = Room.objects.create(
                        first_user_id=first_user_id,
                        second_user_id=second_user.user_id
                    )
                    created_rooms.append(room)

            if created_rooms:
                return Response({'message': f'Đã tạo {len(created_rooms)} rooms.'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': 'Không có phòng nào được tạo, tất cả bị trùng.'},
                                status=status.HTTP_200_OK)
        except Exception as ex:
            return Response({'error': str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(methods=['get'], detail=True, url_path='messages')
    # Lấy các tin nhắn của chat
    def messages(self, request, pk):
        messages = Message.objects.filter(room_id=pk).order_by('created_date').all()
        paginator = MyPageSize()
        paginated = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializerForRoom(paginated, many=True)
        serializer_data = serializer.data

        for message in serializer_data:
            content = message['content']
            decoded_content = decode_aes(content)
            message['content'] = decoded_content  # mã hóa

        return paginator.get_paginated_response(serializer_data)

    # # Tìm đoạn chat
    # @action(methods=['post'], detail=False, url_path='find_room')
    # def find_room(self, request):
    #     try:
    #         first_user_id = request.data.get('first_user')
    #         second_user_id = request.data.get('second_user')
    #         if first_user_id and second_user_id:
    #             room = Room.objects.filter(
    #                 Q(first_user_id=first_user_id, second_user_id=second_user_id) |
    #                 Q(first_user_id=second_user_id, second_user_id=first_user_id)
    #             )
    #             return Response(RoomSerializer(room, many=True).data)
    #         else:
    #             return Response({'error': 'Thiếu 1 trong 2 id'}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as ex:
    #         return Response({'Phát hiện lỗi', str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageViewSet(viewsets.ViewSet,generics.ListAPIView,generics.RetrieveAPIView,generics.CreateAPIView,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset =  Message.objects.filter(active=True).all()
    serializer_class = MessageSerializer
    pagination_class = MyPageSize
    permission_classes = [permissions.IsAuthenticated]
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = MessageSerializer(queryset, many=True).data

        for message in serializer:
            if message.get('content'):  # Kiểm tra nếu content tồn tại
                decoded_content = decode_aes(message['content'])
                print(f"Decoded content: {decoded_content}")  # Debug
                message['content'] = decoded_content or "Invalid content"
            else:
                message['content'] = "Content is empty"
        return Response(serializer)

    def perform_create(self, serializer):
        data = self.request.data
        raw_content = data.get('content')
        encode_mes = encode_aes(raw_content)
        # print(encode_mes)
        return serializer.save(content=encode_mes)





from django.http import HttpResponse
import pandas as pd
from django.db.models import Count
from django.db.models.functions import TruncYear, TruncQuarter, TruncMonth
from .models import User, Post  # Đảm bảo import đúng model

def statistics_view(request):
    time_unit = request.POST.get("time_unit", "year")  # Mặc định theo năm
    time_map = {
        "year": TruncYear,
        "quarter": TruncQuarter,
        "month": TruncMonth,
    }
    time_function = time_map.get(time_unit, TruncYear)

    # Thống kê số người dùng
    users_stats = User.objects.annotate(time_unit=time_function("date_joined")) \
        .values("time_unit") \
        .annotate(count=Count("id")) \
        .order_by("time_unit")

    # Thống kê số bài viết
    posts_stats = Post.objects.annotate(time_unit=time_function("created_date")) \
        .values("time_unit") \
        .annotate(count=Count("id")) \
        .order_by("time_unit")

    return render(request, "admin/stats.html", {
        "users_stats": users_stats,
        "posts_stats": posts_stats,
        "time_unit": time_unit,
    })


def export_statistics_to_excel(request):
    # Lấy tham số từ request GET
    time_unit = request.GET.get("time_unit", "year")

    # Map từ khóa với hàm tương ứng
    time_map = {
        "year": TruncYear,
        "quarter": TruncQuarter,
        "month": TruncMonth,
    }
    time_function = time_map.get(time_unit, TruncYear)

    # Lấy số liệu thống kê
    users_stats = User.objects.annotate(time_unit=time_function("date_joined")) \
        .values("time_unit") \
        .annotate(count=Count("id")) \
        .order_by("time_unit")

    posts_stats = Post.objects.annotate(time_unit=time_function("created_date")) \
        .values("time_unit") \
        .annotate(count=Count("id")) \
        .order_by("time_unit")

    # Chuyển dữ liệu thành DataFrame
    df_users = pd.DataFrame(list(users_stats))
    df_posts = pd.DataFrame(list(posts_stats))

    # Chuyển đổi dữ liệu datetime thành chuỗi để tránh lỗi
    df_users["time_unit"] = df_users["time_unit"].astype(str)
    df_posts["time_unit"] = df_posts["time_unit"].astype(str)

    # Ghi dữ liệu vào file Excel
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="statistics.xlsx"'

    with pd.ExcelWriter(response, engine="xlsxwriter") as writer:
        df_users.to_excel(writer, sheet_name="Users", index=False)
        df_posts.to_excel(writer, sheet_name="Posts", index=False)

    return response


#Testing==========================================================
class LogoutView(View):
    def get(self,request):
        logout(request)
        return redirect('app:home')

class HomeView(View):
    template_name = 'login/home.html'
    def get(self,request):
        current_user = request.user
        return render(request,self.template_name,{'current_user':current_user})

from django.shortcuts import render, redirect


def index(request):
    return render(request, "chat/index.html")


def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})
