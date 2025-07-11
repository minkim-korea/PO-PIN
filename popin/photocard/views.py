from django.shortcuts import render, redirect, get_object_or_404

from signupFT.models import User
from photocard.models import Photocard
from idols.models import Member
from photocard.models import TempWish

from django.db.models import Count
from datetime import date

from django.http import JsonResponse

# 포토카드 거래글 전체 읽어오기 (추후 위치 기반으로 수정 필요)
def list(request):
    # 쿼리 파라미터 받아오기
    idol_names = request.GET.getlist('idol')
    place = request.GET.get('place')
    category = request.GET.get('category')
    sort = request.GET.get('sort')
    
    # 전체 포토카드 리스트 불러오기
    photocards = Photocard.objects.select_related('member__group').annotate(
        wish_count=Count('wished_by_users')
    )
    
    # 조건부 필터링 (값이 있을 경우에만 필터링)
    if idol_names:
        photocards = photocards.filter(member__name__in=idol_names)
    if place:
        photocards = photocards.filter(place=place)
    if category:
        photocards = photocards.filter(category=category)
        
    # 좋아요 순 정렬 옵션 적용
    if sort == 'likes':
        photocards = photocards.annotate(wish_count=Count('wished_by_users')).order_by('-wish_count')
    
    # 조회수 정렬 옵션 적용
    elif sort == 'hit':
        photocards = photocards.order_by('-hit')
    
    context = {'list': photocards}
    return render(request, 'list.html', context)

# 선택 포토카드 거래글 상세정보
def view(request, pno):
    user_id = request.session.get('user_id')
    
    if user_id: # 유저 정보가 있는 경우
        latest_list = request.session.get('latest_poca', []) # 세선 안에 latest_poca 있으면 리스트 불러오기 or []
        
        if pno in latest_list: # 리스트 안에 해당 게시글 pno가 있을 때
            if latest_list[0] != pno: # pno가 리스트 안에 존재하지만 가장 최근이 아닐 때
                latest_list.remove(pno) # 리스트 내 pno 제거
                latest_list.insert(0,pno) # 가장 최근으로 insert
        else:
            latest_list.insert(0,pno) # 가장 최근으로 insert
            
        request.session['latest_poca'] = latest_list
            
    # pno 포토카드 불러오기
    qs = Photocard.objects.get(pno=pno)
    
    # 조회수 증가
    qs.hit += 1
    qs.save()
    
    tags = qs.tag.split(',') # 태그별 분리
    
    # 포토카드 상세정보 반환
    context = {
        "info":qs,
        "tags":tags,
    }
    return render(request, 'view.html', context)
  
def exchange(request):
    # 기본 데이터 로드
    groupMember = Member.objects.select_related('group').all()
    
    # GET 요청에서 필터 값 가져오기
    selected_trade = request.GET.get('trade_type', '전체')
    selected_state = request.GET.get('sell_state', '전체')
    selected_place = request.GET.get('place', '전체')
    selected_members = request.GET.getlist('members[]')

    # 쿼리 파라미터 받아오기
    idol_names = request.GET.getlist('idol')
    place = request.GET.get('place')
    category = request.GET.get('category')
    sort = request.GET.get('sort')

    # 전체 포토카드 리스트 불러오기
    photocards = Photocard.objects.filter(sell_state="중", buy_state=None).annotate(wish_count=Count('wished_by_users')).order_by('-hit')
    
    if searchgroup:
        photocards = photocards.filter(member__group__name=searchgroup)
    
    # 멤버 선택 처리
    if selected_members and '전체' not in selected_members:
        photocards = photocards.filter(member__name__in=selected_members)

    # 아이돌, 카테고리 필터링 (필요시 추가)
    if idol_names:
        photocards = photocards.filter(member__name__in=idol_names)

    if category:
        photocards = photocards.filter(category=category)

    # 좋아요 순 정렬 옵션 적용
    if sort == 'likes':
        photocards = photocards.order_by('-wish_count')

    # 필터링된 포토카드를 템플릿에 전달
    context = {
        'list': groupMember,
        'photocards': photocards,
        'trade_choices': Photocard.TRADE_CHOICES,
        'state_choices': Photocard.TRADE_STATE_CHOICES,
        'place_choices': Photocard.PLACE_CHOICES,
        'trade':trade,
        'place':place,
        'searchgroup':searchgroup,
        'selected_members':selected_members,
    }
    
    return render(request, 'exchange.html', context)

def detail(request, pno):
    user_id = request.session.get('user_id')
    
    if user_id: # 유저 정보가 있는 경우
        latest_list = request.session.get('latest_poca', []) # 세선 안에 latest_poca 있으면 리스트 불러오기 or []
        
        if pno in latest_list: # 리스트 안에 해당 게시글 pno가 있을 때
            if latest_list[0] != pno: # pno가 리스트 안에 존재하지만 가장 최근이 아닐 때
                latest_list.remove(pno) # 리스트 내 pno 제거
                latest_list.insert(0,pno) # 가장 최근으로 insert
        else:
            latest_list.insert(0,pno) # 가장 최근으로 insert
            
        request.session['latest_poca'] = latest_list
            
    # pno 포토카드 불러오기
    qs = Photocard.objects.annotate(wish_count=Count('wished_by_users')).get(pno=pno)
    is_wish = TempWish.objects.filter(user=user_id, photocard=qs).exists()
    
    qs.hit += 1
    qs.save()
    
    if not qs.latitude and not qs.longitude:
        if qs.place == "올림픽공원":
            qs.latitude = 37.51784192112613
            qs.longitude = 127.1276152266286
        elif qs.place == "상암":
            qs.latitude = 37.580534952338624
            qs.longitude = 126.89203603891819
        elif qs.place == "더현대":
            qs.latitude = 37.52586982023892
            qs.longitude = 126.92844895447732
        elif qs.place == "고척":
            qs.latitude = 37.49823024363382
            qs.longitude = 126.86710307179943
        elif qs.place == "인스파이어":
            qs.latitude = 37.46667138168973
            qs.longitude = 126.39058501167706
        elif qs.place == "홍대":
            qs.latitude = 37.55683650372744
            qs.longitude = 126.9237735042553
    
    # 포토카드 상세정보 반환
    if qs.tag:
        tags = qs.tag.split(",")
        context = {"info":qs, "is_wish":is_wish, "tags":tags}
    else:
        context = {"info":qs, "is_wish":is_wish}

    
    return render(request, 'pocadetail.html', context)

def toggle_wish(request, pno):
    user_id = request.session.get('user_id')  # 로그인 시 저장한 user_id 세션

    if not user_id:
        return redirect('login:loginp')  # 로그인 안 되어있으면 로그인 페이지로
    
    user = get_object_or_404(User, user_id=user_id)
    photocard = get_object_or_404(Photocard, pno=pno)

    temp_wish = TempWish.objects.filter(user=user, photocard=photocard).first()
    
    if temp_wish:
        temp_wish.delete()
        action = 'decreased'
    else:
        TempWish.objects.create(user=user, photocard=photocard)
        action = 'increased'
        
    wish_count = photocard.wished_by_users.count()
    
    # ajax 요청에 대해서는 JSON 응답을 반환
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'action': action, 'new_like_count': wish_count})

    # 일반적인 요청에는 포토카드 교환 페이지로 리다이렉트
    return redirect('/photocard/exchange/')


# 포토카드 거래글 작성
def write(request):
    user_id = request.session.get('user_id')  # 로그인 시 저장한 user_id 세션

    if not user_id:
        return redirect('login:loginp')  # 로그인 안 되어있으면 로그인 페이지로
        
    try:
        user = User.objects.get(user_id=user_id)
        if request.method == "GET" :
            # choices : select options 반환 >> PHOTOCARD model.py 참고!!
            # ex) Photocard.CATEGORY_CHOICES
            # > ('앨범', '앨범'),('특전', '특전'),('MD', 'MD'),('공방', '공방'),('기타', '기타'),
            # member : idol의 member 반환
            context = {
            'category_choices': Photocard.CATEGORY_CHOICES,
            'poca_state_choices': Photocard.P_STATE_CHOICES,
            'trade_type_choices': Photocard.TRADE_CHOICES,
            'place_choices': Photocard.PLACE_CHOICES,
            }
            return render(request, 'write.html', context)
            
        elif request.method == 'POST':
            # 작성 버튼 클릭 시 필요한 필드 정보
            # 제목, 이미지, 판매자, 카테고리, 앨범, 그룹, 멤버, 하자상태, 태그, 거래 방식, 가격, 상세설명
            # 장소, 구매자 거래 상태(게시글 등록 시 거래중 설정), 거래날짜, 위도, 경도

            title = request.POST.get('title') # 제목
            image = request.FILES.get('image') # 이미지
            
            seller = user # 판매자
            
            category=request.POST.get('album_type') # 카테고리
            album=request.POST.get('album') # 앨범
            
            group=request.POST.get('group') # 그룹
            member=request.POST.get('member') # 멤버
            member_obj = Member.objects.get(name=member, group__name=group)
            
            poca_state=request.POST.get('poca_state') # 하자상태
            
            tags=request.POST.getlist('tag', None) # 태그 리스트
            tag = ','.join(tags) # 하나의 문자열로 태그 전환
            
            trade_type=request.POST.get('trade_type') # 거래방식
            price = request.POST.get('price') # 가격
            description = request.POST.get('description','') # 상세설명
            
            place=request.POST.get('place') # 장소
            
            sell_state = '중' # 구매자 거래 상태 (등록 시 default)
            
            # 거래 날짜
            if request.POST.get('available_at') == "" :
                available_at = str(date.today()) # blank로 들어오면 오늘 날짜
            else:
                available_at = request.POST.get('available_at') # 지정한 경우 지정 날짜
            
            # 위치 문자열 -> 숫자열로 전환
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')

            latitude = float(lat) if lat else None
            longitude = float(lng) if lng else None
            
            # Photocard 객체 생성
            Photocard.objects.create(
                title=title, image=image, seller=seller, category=category, album=album, member=member_obj, poca_state=poca_state, tag=tag, trade_type=trade_type, place=place, sell_state=sell_state, available_at=available_at, latitude=latitude, longitude=longitude
            )
            
            # redirect로 이동
            return redirect('/photocard/list')
            
    except User.DoesNotExist:
        return redirect('login:main')  # 예외 상황 대비

# 포토카드 거래글 수정
def update(request, pno):
    user_id = request.session.get('user_id')  # 로그인 시 저장한 user_id 세션
    
    if not user_id:
        return redirect('login:loginp')  # 로그인 안 되어있으면 로그인 페이지로
    
    user = User.objects.get(user_id=user_id) # 사용자
    photo_qs = Photocard.objects.get(pno=pno) # 수정 포토카드 게시글
    
    # 사용자 아이디와 수정 포토카드 게시글의 판매자가 같을 시 True
    if user.user_id == photo_qs.seller.user_id :
        try:
            if request.method == "GET":
                
                tags = photo_qs.tag.split(',') # 태그별 분리
                context = {
                    'category_choices': Photocard.CATEGORY_CHOICES,
                    'poca_state_choices': Photocard.P_STATE_CHOICES,
                    'trade_type_choices': Photocard.TRADE_CHOICES,
                    'place_choices': Photocard.PLACE_CHOICES,
                    'trade_state_choices' : Photocard.TRADE_STATE_CHOICES,
                    'photocard': photo_qs,
                    'tags':tags,
                }
                return render(request, 'update.html', context)
            
            # 포토카드 상세정보 수정
            elif request.method == "POST":
                photo_qs.title = request.POST.get('title') # 제목
                photo_qs.image = request.FILES.get('image') # 이미지
                
                photo_qs.category=request.POST.get('category') # 카테고리 (공방, 앨범)
                photo_qs.album=request.POST.get('album') # 활동 시기 앨범 (1집, 2집)
                
                group=request.POST.get('group') # 그룹
                member=request.POST.get('member') # 멤버
                member_obj = Member.objects.get(name=member, group__name=group)
                photo_qs.member = member_obj
                
                photo_qs.poca_state=request.POST.get('poca_state') # 포카 하자 상태
                
                photo_qs.trade_type=request.POST.get('trade_type') # 거래 방식
                
                tags=request.POST.getList('tag', None) # 태그 리스트
                photo_qs.tag = ','.join(tags) # 하나의 문자열로 태그 전환
                
                photo_qs.price = request.POST.get('price','') # 가격
                photo_qs.description = request.POST.get('description','') # 상세 설명
                
                photo_qs.place=request.POST.get('place') # 장소 (올공, 더현대)
                
                photo_qs.sell_state = request.POST.get('sell_state') # 판매자 거래 상태
                
                # 거래 가능일
                if request.POST.get('available_at') == "" :
                    available_at = str(date.today())
                else:
                    available_at = request.POST.get('available_at')
                
                photo_qs.available_at = available_at 
                
                #거래 위치 위도 경도
                # 위치 문자열 -> 숫자열로 전환
                lat = request.POST.get('latitude')
                lng = request.POST.get('longitude')

                photo_qs.latitude = float(lat) if lat else None
                photo_qs.longitude = float(lng) if lng else None
                
                # 새로 설정한 값 수정
                photo_qs.save()
                
                # 수정 완료 후 리다이렉트
                return redirect('/photocard/list')
        except User.DoesNotExist:
            return redirect('login:main')  # 예외 상황 대비
    else: 
        # 사용자 아이디와 판매자 아이디가 일치하지 않을 경우 리다이렉트
        return redirect('/photocard/list')
                
        

# 포토카드 거래글 삭제
def delete(request, pno):
    user_id = request.session.get('user_id')  # 로그인 시 저장한 user_id 세션
    
    if not user_id:
        return redirect('login:loginp')  # 로그인 안 되어있으면 로그인 페이지로
    
    user = User.objects.get(user_id=user_id) # 사용자
    photo_qs = Photocard.objects.get(pno=pno) # 수정 포토카드 게시글
    
    # 사용자 아이디와 수정 포토카드 게시글의 판매자가 같을 시 True
    if user.user_id == photo_qs.seller.user_id :
        Photocard.objects.get(pno=pno).delete()
        
    return redirect('/photocard/list/')

# 포토카드 위시 등록 & 삭제
def wish(request, pno):
    user_id = request.session.get('user_id')  # 로그인 시 저장한 user_id 세션

    if not user_id:
        return redirect('login:loginp')  # 로그인 안 되어있으면 로그인 페이지로

    try:
        user = User.objects.get(user_id=user_id)
        photocard = Photocard.objects.get(pno=pno)
        
        try: 
            # 테이블에 해당 유저가 해당 포토카드를 위시 했는지 조회
            qs = TempWish.objects.get(user=user, photocard=photocard)
            # 이미 존재할 경우 삭제
            qs.delete()
        except:
            # 존재하지 않을 경우 추가
            TempWish.objects.create(user=user, photocard=photocard)
        
        return redirect('/photocard/list')
    
    except User.DoesNotExist:
        return redirect('login:main')  # 예외 상황 대비

def location(request):
    return render(request, 'location.html')




###################################
# photocard/views.py
from django.http import JsonResponse
from math import radians, cos, sin, asin, sqrt
from .models import Photocard  # <- 실제 모델명으로 바꿔주세요
import requests
from django.conf import settings

def location2_geocode_api(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'status': 'error', 'message': 'No query provided'})

    # ✅ .env 또는 settings.py에 저장된 KAKAO_REST_API_KEY 사용
    KAKAO_API_KEY = getattr(settings, 'KAKAO_REST_API_KEY', None)
    if not KAKAO_API_KEY:
        return JsonResponse({'status': 'error', 'message': 'No Kakao API Key'})

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        result = response.json()
        if result['documents']:
            location = result['documents'][0]['address']
            return JsonResponse({
                'status': 'ok',
                'lat': location['y'],
                'lng': location['x']
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'No result found'})
    else:
        return JsonResponse({'status': 'error', 'message': 'API request failed'})

# 거리 계산 함수 (하버사인 공식)
def haversine(lon1, lat1, lon2, lat2):
    # 위도, 경도 → 라디안
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # 거리 계산
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # 지구 반지름 (km)
    return c * r
def location2_api(request):
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        radius = float(request.GET.get('radius'))
        query = request.GET.get('query', '').strip().lower()

        results = []
        photocard_list = Photocard.objects.filter(latitude__isnull=False, longitude__isnull=False)

        for card in photocard_list:
            dist = haversine(lng, lat, card.longitude, card.latitude)

            if dist <= radius:
                member_name = card.member.name.lower() if card.member else ''
                group_name = card.member.group.name.lower() if card.member and card.member.group else ''

                if query == '' or query in member_name or query in group_name:
                    results.append({
                        "title": f"{group_name} {member_name} ({card.trade_type})",
                        "lat": card.latitude,
                        "lng": card.longitude,
                        "group": group_name,
                        "member": member_name,
                        "type": card.trade_type,
                        "description": card.description,
                        "distance": f"{dist:.1f}km",
                        "image": card.image.url if card.image else '',
                    })

        return JsonResponse({"status": "ok", "results": results})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    
def location2(request):
    return render(request, 'photocard/location2 copy.html')  # 파일명은 너가 쓰는 대로