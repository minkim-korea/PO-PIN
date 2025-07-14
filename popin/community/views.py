from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import SharingPost, SharingTag, SharingImage
from django.db.models import Avg
from datetime import datetime, timedelta
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpResponse
from community.models import ExchangeReview, ReviewImage, ReviewTag
from signupFT.models import User  # 너의 커스텀 유저 모델 import
from django.contrib import messages
from .models import CompanionPost, CompanionTag, CompanionImage
from django.views.decorators.csrf import csrf_exempt
from community.models import ProxyPost, ProxyImage, ProxyTag
from django.utils.timezone import make_aware
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from community.models import StatusPost, StatusImage, StatusTag
from itertools import chain
from operator import attrgetter
from django.db.models import Q
from django.core.paginator import Paginator
from .models import ProxyStatus
from community.models import SharingStatus  
from community.models import CompanionPost, CompanionComment
from django.utils import timezone
from community.models import  StatusStatus 


User = get_user_model()
#########  urls.py 순서대로 정리함 



def chgReviewmain(request):
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    weekly_reviews = ExchangeReview.objects.filter(created_at__gte=start_of_week)
    weekly_count = weekly_reviews.count()
    average_score = ExchangeReview.objects.aggregate(avg_score=Avg("overall_score"))["avg_score"]
    average_score = round(average_score or 0, 1)

    query = request.GET.get('q', '')
    if query:
        filtered_reviews = ExchangeReview.objects.filter(
            Q(title__icontains=query) | Q(writer__user_id__icontains=query)
        ).order_by('-created_at')
    else:
        filtered_reviews = ExchangeReview.objects.all().order_by('-created_at')

    paginator = Paginator(filtered_reviews, 7)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "weekly_count": weekly_count,
        "average_score": average_score,
        "page_obj": page_obj,
        "query": query,
    }

    return render(request, "chgReview/main.html", context)


################################################################################
##교환/판매 상세보기 

def chgReviewview(request, pk):
    post = get_object_or_404(
        ExchangeReview.objects.prefetch_related('tags', 'images'),
        id=pk
    )

    # 조회수 증가 (선택)
    post.views += 1
    post.save(update_fields=["views"])

    return render(request, 'chgReview/chgR_view.html', {
        'post': post
    })
################################################################################

# 교환후기글 수정 
def chgReview_update(request, pk):
    post = get_object_or_404(ExchangeReview, id=pk)

    if request.method == "POST":
        post.title = request.POST.get("title")
        post.content = request.POST.get("content")
        post.overall_score = request.POST.get("overall_score")
        post.save()
        return redirect('community:chgReviewview', pk=post.id)

    return render(request, 'chgReview/chgR_edit.html', {'post': post})


   
################################################################################
## 최근게시글
def recent(request):
    def annotate_type(qs, type_name):
        for post in qs:
            post.post_type = type_name
        return qs

    # GET 파라미터 받기
    type_filter = request.GET.get("type", "all")
    sort = request.GET.get("sort", "latest")

    post_sources = []
    if type_filter in ["review", "all"]:
        post_sources += annotate_type(ExchangeReview.objects.all(), "review")
    if type_filter in ["sharing", "all"]:
        post_sources += annotate_type(SharingPost.objects.all(), "sharing")
    if type_filter in ["proxy", "all"]:
        post_sources += annotate_type(ProxyPost.objects.all(), "proxy")
    if type_filter in ["companion", "all"]:
        post_sources += annotate_type(CompanionPost.objects.all(), "companion")
    if type_filter in ["status", "all"]:
        post_sources += annotate_type(StatusPost.objects.all(), "status")

    if sort == "latest":
        post_sources = sorted(post_sources, key=attrgetter("created_at"), reverse=True)
    elif sort == "popular":
        post_sources = sorted(post_sources, key=attrgetter("views"), reverse=True)
    elif sort == "comments":
        post_sources = sorted(post_sources, key=attrgetter("comments_count"), reverse=True)

    paginator = Paginator(post_sources, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/community_recent.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'sort': sort,
    })

#############################################################################
# 동행모집글 작성

def write_companion(request):
    if request.method == "POST":

        try:
            # 1. 사용자
            user_id = request.session.get('user_id')
            user = User.objects.get(user_id=user_id)

            # 2. 기본 정보
            title = request.POST.get('title')
            artist = request.POST.get('artist')
            category = request.POST.get('category')
            location = request.POST.get('location')
            content = request.POST.get('content')
            max_people = request.POST.get('max_people')  
            tags = request.POST.get('tags', '')

            # 3. 날짜 + 시간 → datetime 필드
            date_str = request.POST.get('eventDate')
            time_str = request.POST.get('eventTime')
            event_datetime = timezone.make_aware(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))

            # 4. 게시글 저장
            post = CompanionPost.objects.create(
                title=title,
                artist=artist,
                category=category,
                location=location,
                content=content,
                max_people=max_people,
                event_date=event_datetime,
                author=user,
            )


            # 5. 태그 처리
            tag_list = [tag.strip().lstrip('#') for tag in tags.split(',') if tag.strip()]
            for tag_name in tag_list:
                tag_obj, _ = CompanionTag.objects.get_or_create(name=tag_name)
                post.tags.add(tag_obj)


            # 6. 이미지 저장
            for file in request.FILES.getlist('images'):
                CompanionImage.objects.create(post=post, image=file)


            return redirect('community:companion')
        except Exception as e:
            import traceback
            print(traceback.format_exc())  # 콘솔 확인용
            return render(request, 'community/community_write_companion.html', {'error': str(e)})
    
    return render(request, 'community/community_write_companion.html')
  ########################################################################################## 
    
## 대리구매글 작성

def write_proxy(request):

    if request.method == "POST":
        title = request.POST.get("title")
        artist = request.POST.get("artist")
        category = request.POST.get("category", "기타")
        status = request.POST.get("status", "모집중")


        # 날짜와 시간 조합 → DateTimeField에 맞게
        event_date = request.POST.get("eventDate")
        event_time = request.POST.get("eventTime")
        event_datetime = timezone.make_aware(datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M"))


        location = request.POST.get("location")
        max_people = request.POST.get('max_people')
        reward = request.POST.get("fee")
        description = request.POST.get("content")
        tag_string = request.POST.get("tags", "")

        # 세션에서 사용자 가져오기
        user_id = request.session.get("user_id")
        if not user_id:
            return redirect("login")  # 로그인 안 되어 있으면 로그인 페이지로


        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return render(request, "community/write_proxy.html", {"error": "사용자를 찾을 수 없습니다."})

        # 저장
        proxy_post = ProxyPost.objects.create(
            title=title,
            artist=artist,
            category=category,
            status=status,
            event_date=event_datetime,
            location=location,
            max_people=max_people,
            reward=reward,
            description=description,
            author=user
        )

        # 태그 처리
        tags = [t.strip().replace("#", "") for t in tag_string.split() if t.strip()]
        for tag_name in tags:
            tag_obj, _ = ProxyTag.objects.get_or_create(name=tag_name)
            proxy_post.tags.add(tag_obj)

        # 이미지 업로드
        images = request.FILES.getlist("images")
        for img in images:
            ProxyImage.objects.create(post=proxy_post, image=img)

        return redirect("community:main")  # 작성 완료 후 메인으로 이동

    
    return render(request, 'community/community_write_proxy.html')

#############################################
## 교환후기 글작성 
def write_review(request):
    if request.method == 'POST':
        try:
            # 세션에서 user_id 가져오기
            user_id = request.session.get('user_id')
            if not user_id:
                messages.error(request, "[오류] 로그인 정보가 없습니다.")
                return redirect('community:write_review')

            try:
                writer = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                messages.error(request, "[오류] 유저 정보를 찾을 수 없습니다.")
                return redirect('community:write_review')

            title = request.POST.get('title')
            content = request.POST.get('content')
            artist = request.POST.get('artist', '기타')
            method = request.POST.get('method')
            transaction_type = request.POST.get('transaction_type', '교환')
            score = int(request.POST.get('overall_score', 3))
            tag_str = request.POST.get('tags', '')
            partner_id = request.POST.get('partner')

            try:
                partner = User.objects.get(user_id=partner_id)
            except User.DoesNotExist:
                partner = writer  # fallback

            with transaction.atomic():
                review = ExchangeReview.objects.create(
                    writer=writer,
                    partner=partner,
                    title=title,
                    content=content,
                    artist=artist,
                    method=method,
                    transaction_type=transaction_type,
                    overall_score=score
                )

                if tag_str:
                    tag_list = [tag.lstrip('#') for tag in tag_str.strip().split()]
                    for tag in tag_list:
                        tag_obj, _ = ReviewTag.objects.get_or_create(name=tag)
                        review.tags.add(tag_obj)

                for img in request.FILES.getlist('images'):
                    ReviewImage.objects.create(review=review, image=img)

            messages.success(request, "리뷰가 저장되었습니다.")
            return redirect('community:main')

        except Exception as e:
            print("[리뷰 저장 실패]", e)
            messages.error(request, f"[오류] {str(e)}")
            return redirect('community:write_review')

    return render(request, 'community/community_write_review.html')
#########################################

#나눔 

def write_sharing(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                messages.error(request, "[오류] 로그인 정보가 없습니다.")
                return redirect('community:write_sharing')

            try:
                author = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                messages.error(request, "[오류] 작성자 정보를 찾을 수 없습니다.")
                return redirect('community:write_sharing')

            # POST 데이터 받기
            title = request.POST.get('title')
            content = request.POST.get('content')
            artist = request.POST.get('artist', '기타')
            category = request.POST.get('category')
            sharing_type = request.POST.get('type')
            if not sharing_type: sharing_type = '오프라인'
            location = request.POST.get('location')
            requirement = request.POST.get('requirement')
            tag_str = request.POST.get('tags', '')
            share_date_str = request.POST.get('share_date')

            # 타입 누락 시 오류 처리
            if not sharing_type:
                messages.error(request, "[오류] 나눔 형태(type)는 필수 선택 항목입니다.")
                return redirect('community:write_sharing')

            # 날짜 변환
            share_date = None
            if share_date_str:
                naive_datetime = datetime.strptime(share_date_str, "%Y-%m-%dT%H:%M")
                share_date = make_aware(naive_datetime)

            with transaction.atomic():
                post = SharingPost.objects.create(
                    author=author,
                    title=title,
                    content=content,
                    artist=artist,
                    category=category,
                    type=sharing_type,  #  정확히 전달
                    share_date=share_date,
                    location=location,
                    requirement=requirement
                )

                # 태그 저장
                if tag_str:
                    tag_list = [tag.strip().lstrip('#') for tag in tag_str.split(',')]
                    for tag in tag_list:
                        tag_obj, _ = SharingTag.objects.get_or_create(name=tag)
                        post.tags.add(tag_obj)

                # 이미지 저장
                for img in request.FILES.getlist('images'):
                    SharingImage.objects.create(post=post, image=img)

            messages.success(request, "나눔 글이 저장되었습니다.")
            return redirect('community:main')

        except Exception as e:
            print("[나눔 저장 실패]", e)
            messages.error(request, f"[오류] {str(e)}")
            return redirect('community:write_sharing')

    return render(request, 'community/community_write_sharing.html')
#################################################################

 
@csrf_exempt
def write_status(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'error': '로그인이 필요합니다.'}, status=403)

            user = User.objects.get(user_id=user_id)

            title = request.POST.get('title', '').strip()
            artist = request.POST.get('artist', '').strip()
            category = request.POST.get('category', '').strip()
            event_datetime_str = request.POST.get('event_datetime')
            event_datetime = parse_datetime(event_datetime_str) if event_datetime_str else None
            location = request.POST.get('location', '').strip()
            region = request.POST.get('region', '').strip()
            content = request.POST.get('content', '').strip()
            tag_string = request.POST.get('tags', '')
            tag_names = [tag.strip() for tag in tag_string.split(',') if tag.strip()]

            # 필수값 누락 시 예외
            if not (title and artist and category and event_datetime and location and content):
                return JsonResponse({'error': '필수 항목이 누락되었습니다.'}, status=400)

            # 게시글 저장
            post = StatusPost.objects.create(
                author=user,
                title=title,
                artist=artist,
                category=category,
                event_datetime=event_datetime,
                place=location,
                region=region,
                content=content
            )

            # 태그 저장
            for tag_name in tag_names:
                tag, _ = StatusTag.objects.get_or_create(name=tag_name)
                post.tags.add(tag)

            # 이미지 저장
            for image in request.FILES.getlist('images'):
                StatusImage.objects.create(post=post, image=image)

            return JsonResponse({'success': True})


        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET 요청일 경우 템플릿 렌더링
    return render(request, 'community/community_write_status.html')
 #현황공유 작성



#######################################################################
# 메인페이지

def main(request):
    all_posts = sorted(
        chain(
            SharingPost.objects.all(),
            CompanionPost.objects.all(),
            ProxyPost.objects.all()
        ),
        key=attrgetter('created_at'),
        reverse=True
    )
    return render(request, 'community/main.html', {'posts': all_posts})

#########################################

def companion(request):
    query = request.GET.get('q', '')  # 검색어 받아오기

    if query:
        all_posts = CompanionPost.objects.filter(
            Q(title__icontains=query)
        ).order_by('-created_at')
    else:
        all_posts = CompanionPost.objects.all().order_by('-created_at')

    # 통계 수치
    ongoing_count = CompanionPost.objects.count()
    completed_count = CompanionPost.objects.filter(status='모집완료').count() 
    weekly_count = CompanionPost.objects.filter(created_at__week=timezone.now().isocalendar()[1]).count()

    # 페이지네이터
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'posts': page_obj,
        'query': query,
        'ongoing_count': ongoing_count,
        'completed_count': completed_count,
        'weekly_count': weekly_count,
    }

    return render(request, 'companion/main.html', context)
###########################################################################
##### 대리구매 게시판

def proxy(request):
    # 🔍 검색어 받기
    query = request.GET.get('q', '')  # 일반 검색어

    # 🔎 기본 queryset
    all_posts = ProxyPost.objects.all()

    # 🔍 검색 필터 (✅ description으로 수정)
    if query:
        all_posts = all_posts.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)  # ✅ 수정된 부분
        )

    all_posts = all_posts.order_by('-created_at')

    # 📊 통계 계산
    ongoing_count = ProxyPost.objects.count()
    completed_count = ProxyPost.objects.filter(status=ProxyStatus.DEADLINE).count()
    weekly_count = ProxyPost.objects.filter(
        created_at__week=timezone.now().isocalendar()[1]
    ).count()

    # 📄 페이지네이션
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 💬 템플릿 전달
    context = {
        'posts': page_obj,
        'ongoing_count': ongoing_count,
        'completed_count': completed_count,
        'weekly_count': weekly_count,
        'query': query,
    }

    return render(request, 'proxy/main.html', context)
#############################################################################################
##### 나눔 게시판

def sharing(request):
    # 1. 검색어 가져오기
    query = request.GET.get('q', '')

    # 2. 필터링 (제목 기준)
    if query:
        all_posts = SharingPost.objects.filter(title__icontains=query).order_by('-created_at')
    else:
        all_posts = SharingPost.objects.all().order_by('-created_at')

    # 3. 통계 수치 계산
    ongoing_count = SharingPost.objects.count()
    completed_count = SharingPost.objects.filter(status=SharingStatus.CLOSED).count()
    weekly_count = SharingPost.objects.filter(created_at__week=timezone.now().isocalendar()[1]).count()

    # 4. 페이지네이션
    paginator = Paginator(all_posts, 6)  # 페이지당 6개
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'posts': page_obj,
        'ongoing_count': ongoing_count,
        'completed_count': completed_count,
        'weekly_count': weekly_count,
        'query': query,  # 템플릿에서 검색어 유지하려면 필요
    }
    return render(request, 'sharing/main.html', context)
 #####################################################   

##### 현황공유 게시판

def status(request):
    query = request.GET.get('q', '')

    if query:
        all_posts = StatusPost.objects.filter(
            Q(title__icontains=query)
        ).order_by('-created_at')
    else:
        all_posts = StatusPost.objects.all().order_by('-created_at')

    # 통계 수치 계산
    ongoing_count = StatusPost.objects.count()
    completed_count = StatusPost.objects.filter(status=StatusStatus.CLOSED).count()
    weekly_count = StatusPost.objects.filter(
        created_at__week=timezone.now().isocalendar()[1]
    ).count()

    # 페이지네이션
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'posts': page_obj,
        'ongoing_count': ongoing_count,
        'completed_count': completed_count,
        'weekly_count': weekly_count,
        'query': query  # 검색어 유지
    }
    return render(request, 'status/main.html', context)


##################


def companion_detail(request, pk):
    post = get_object_or_404(CompanionPost, pk=pk)
    post.views += 1
    post.save(update_fields=["views"])

    return render(request, 'community/companion_detail.html', {
        'post': post,
        'title': post.title,
        'artist': post.artist,
        'category': post.category,
        'location': post.location,
        'content': post.content,
        'tags': post.tags.all(),
        'event_date': post.event_date,
        'max_people': post.max_people,
        'participants': post.participants.all(),
        'status': post.status,
        'images': post.images.all(),
    })


def sharing_detail(request, pk):
    post = get_object_or_404(SharingPost, pk=pk)
    post.views += 1
    post.save(update_fields=["views"])

    return render(request, 'community/sharing_detail.html', {
        'post': post,
        'title': post.title,
        'content': post.content,
        'artist': post.artist,
        'requirement': post.requirement,
        'category': post.category,
        'type': post.type,
        'share_date': post.share_date,
        'location': post.location,
        'tags': post.tags.all(),
        'status': post.status,
        'images': post.images.all(),
    })


def proxy_detail(request, pk):
    post = get_object_or_404(ProxyPost, pk=pk)
    post.views += 1
    post.save(update_fields=["views"])

    return render(request, 'community/proxy_detail.html', {
        'post': post,
        'title': post.title,
        'artist': post.artist,
        'category': post.category,
        'status': post.status,
        'event_date': post.event_date,
        'location': post.location,
        'max_people': post.max_people,
        'reward': post.reward,
        'description': post.description,
        'tags': post.tags.all(),
        'participants': post.participants.all(),
        'images': post.images.all(),
    })