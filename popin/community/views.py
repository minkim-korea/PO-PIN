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
from django.utils.timezone import now


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
        return redirect('chgReview:chgReviewview', pk=post.id)

    return render(request, 'chgReview/chgR_edit.html', {'post': post})


   
################################################################################
## 최근게시글
def recent(request):
    def annotate_type(qs, type_name):
        for post in qs:
            post.post_type = type_name
        return qs

    posts = sorted(
        chain(
            annotate_type(ExchangeReview.objects.all(), 'review'),
            annotate_type(SharingPost.objects.all(), 'sharing'),
            annotate_type(ProxyPost.objects.all(), 'proxy'),
            annotate_type(CompanionPost.objects.all(), 'companion'),
            annotate_type(StatusPost.objects.all(), 'status'),
        ),
        key=attrgetter('created_at'),
        reverse=True
    )

    paginator = Paginator(posts, 10)  # 한 페이지당 10개씩
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'community/community_recent.html', {
        'page_obj': page_obj,
    })

#############################################################################
# 동행모집글 작성
@csrf_exempt
def write_companion(request):
    if request.method == 'POST':
        try:
            user = User.objects.get(user_id=request.session.get('user_id'))
            date = request.POST.get('eventDate')
            time = request.POST.get('eventTime')
            datetime_obj = timezone.make_aware(datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"))

            post = CompanionPost.objects.create(
                author=user,
                title=request.POST.get('title'),
                artist=request.POST.get('artist'),
                category=request.POST.get('category'),
                location=request.POST.get('location'),
                content=request.POST.get('content'),
                max_people=request.POST.get('max_people'),
                event_date=datetime_obj,
            )

            for tag in request.POST.get('tags', '').split(','):
                if tag.strip():
                    tag_obj, _ = CompanionTag.objects.get_or_create(name=tag.strip().lstrip('#'))
                    post.tags.add(tag_obj)

            for file in request.FILES.getlist('images'):
                CompanionImage.objects.create(post=post, image=file)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'community/community_write_companion.html')
  ########################################################################################## 
    
## 대리구매글 작성
@csrf_exempt
def write_proxy(request):
    if request.method == 'POST':
        try:
            user = User.objects.get(user_id=request.session.get('user_id'))
            datetime_obj = timezone.make_aware(datetime.strptime(
                f"{request.POST.get('eventDate')} {request.POST.get('eventTime')}", "%Y-%m-%d %H:%M"))

            post = ProxyPost.objects.create(
                author=user,
                title=request.POST.get('title'),
                artist=request.POST.get('artist'),
                category=request.POST.get('category', '기타'),
                status=request.POST.get('status', '모집중'),
                event_date=datetime_obj,
                location=request.POST.get('location'),
                max_people=request.POST.get('max_people'),
                reward=request.POST.get('fee'),
                description=request.POST.get('content')
            )

            for tag in request.POST.get('tags', '').split():
                tag_obj, _ = ProxyTag.objects.get_or_create(name=tag.lstrip('#'))
                post.tags.add(tag_obj)

            for img in request.FILES.getlist('images'):
                ProxyImage.objects.create(post=post, image=img)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'community/community_write_proxy.html')

#############################################
## 교환후기 글작성 
@csrf_exempt
def write_review(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            writer = User.objects.get(user_id=user_id)
            partner_id = request.POST.get('partner')
            partner = User.objects.get(user_id=partner_id)

            review = ExchangeReview.objects.create(
                writer=writer,
                partner=partner,
                title=request.POST.get('title'),
                content=request.POST.get('content'),
                artist=request.POST.get('artist', '기타'),
                method=request.POST.get('method'),
                transaction_type=request.POST.get('transaction_type', '교환'),
                overall_score=int(request.POST.get('overall_score', 3))
            )

            tag_str = request.POST.get('tags', '')
            for tag in tag_str.strip().split():
                tag_obj, _ = ReviewTag.objects.get_or_create(name=tag.lstrip('#'))
                review.tags.add(tag_obj)

            for img in request.FILES.getlist('images'):
                ReviewImage.objects.create(review=review, image=img)

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'community/community_write_review.html')
#########################################

#나눔 
def write_sharing(request):
    if request.method == 'POST':
        try:
            author = User.objects.get(pk=request.session.get('user_id'))

            post = SharingPost.objects.create(
                author=author,
                title=request.POST.get('title'),
                content=request.POST.get('content'),
                artist=request.POST.get('artist', '기타'),
                category=request.POST.get('category'),
                type=request.POST.get('type', '오프라인'),
                location=request.POST.get('location'),
                requirement=request.POST.get('requirement'),
                share_date=make_aware(datetime.strptime(request.POST.get('share_date'), "%Y-%m-%dT%H:%M"))
            )

            tag_str = request.POST.get('tags', '')
            for tag in tag_str.split(','):
                if tag.strip():
                    tag_obj, _ = SharingTag.objects.get_or_create(name=tag.strip().lstrip('#'))
                    post.tags.add(tag_obj)

            for img in request.FILES.getlist('images'):
                SharingImage.objects.create(post=post, image=img)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

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

    if query:
        all_posts = all_posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )

    all_posts = all_posts.order_by('-created_at')

    # 📊 통계 계산
    ongoing_count = ProxyPost.objects.count()  # 조건 추가 가능
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
        'query': query,  # 🔁 HTML에서 검색어 유지용
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

