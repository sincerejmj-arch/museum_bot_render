import requests
import os
from datetime import datetime, timezone, timedelta
import json

# 환경 변수에서 텔레그램 정보 가져오기
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 알림 모드 설정 파일
CONFIG_FILE = "/tmp/notification_mode.txt"

def get_notification_mode():
    """현재 알림 모드 가져오기 (기본값: always)"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                mode = f.read().strip()
                return mode if mode in ['always', 'available_only', 'stopped'] else 'always'
    except:
        pass
    return 'always'

def set_notification_mode(mode):
    """알림 모드 설정"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(mode)
        return True
    except Exception as e:
        print(f"모드 저장 실패: {e}")
        return False

def get_bot_updates(offset=None):
    """텔레그램 봇의 새 메시지 확인"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"메시지 확인 실패: {e}")
    return None

def process_commands():
    """사용자 명령어 처리"""
    updates = get_bot_updates()
    if not updates or 'result' not in updates:
        return None
    
    current_mode = get_notification_mode()
    command_result = None
    last_update_id = None
    
    for update in updates['result']:
        # 마지막 update_id 추적
        if 'update_id' in update:
            last_update_id = update['update_id']
        
        if 'message' in update and 'text' in update['message']:
            text = update['message']['text'].strip().lower()
            chat_id = str(update['message']['chat']['id'])
            
            # 본인이 보낸 메시지만 처리
            if chat_id != TELEGRAM_CHAT_ID:
                continue
            
            # 명령어 처리
            if text == '/mode' or text == '/상태':
                mode_text = "매번 알림" if current_mode == 'always' else "예약 가능할 때만 알림" if current_mode == 'available_only' else "중지됨"
                send_telegram_message(
                    f"📌 <b>현재 알림 모드</b>\n\n"
                    f"모드: {mode_text}\n\n"
                    f"변경 방법:\n"
                    f"/always - 매번 알림\n"
                    f"/available - 예약 가능할 때만"
                )
            
            elif text == '/always' or text == '/매번':
                set_notification_mode('always')
                send_telegram_message(
                    "✅ 알림 모드 변경됨\n\n"
                    "📢 <b>매번 알림 모드</b>\n"
                    "5분마다 체크 결과를 모두 알려드립니다."
                )
            
            elif text == '/available' or text == '/예약가능시':
                set_notification_mode('available_only')
                send_telegram_message(
                    "✅ 알림 모드 변경됨\n\n"
                    "🔕 <b>예약 가능할 때만 알림</b>\n"
                    "2월 14일 10시 예약이 가능해지면 알려드립니다.\n"
                    "평소에는 조용히 백그라운드에서 체크합니다."
                )
            
            elif text == '/status' or text == '/현황':
                # 즉시 예약 현황 확인 요청
                command_result = 'status'
                send_telegram_message("🔄 예약 현황을 확인하고 있습니다...")
            
            elif text == '/test' or text == '/테스트':
                # 즉시 1회 체크 실행
                command_result = 'test'
                send_telegram_message("🧪 테스트 체크를 실행합니다...")
            
            elif text == '/stop' or text == '/중지':
                set_notification_mode('stopped')
                send_telegram_message(
                    "⏸️ <b>모니터링 중지됨</b>\n\n"
                    "백그라운드 체크는 계속 실행되지만\n"
                    "알림을 전송하지 않습니다.\n\n"
                    "재시작: /start"
                )
            
            elif text == '/start' or text == '/시작':
                old_mode = get_notification_mode()
                if old_mode == 'stopped':
                    set_notification_mode('available_only')
                    send_telegram_message(
                        "▶️ <b>모니터링 재시작됨</b>\n\n"
                        "모드: 예약 가능할 때만 알림\n\n"
                        "변경하려면:\n"
                        "/always - 매번 알림으로 변경"
                    )
                # 이미 실행 중인 경우 조용히 무시 (메시지 안 보냄)
            
            elif text == '/help' or text == '/도움말':
                mode_text = "매번 알림" if current_mode == 'always' else "예약 가능할 때만 알림" if current_mode == 'available_only' else "중지됨"
                send_telegram_message(
                    "🤖 <b>박물관 예약 봇 사용법</b>\n\n"
                    "<b>📊 조회 명령어:</b>\n"
                    "/status - 지금 즉시 예약 현황 확인\n"
                    "/test - 테스트 체크 실행\n\n"
                    "<b>🔔 알림 설정:</b>\n"
                    "/mode - 현재 모드 확인\n"
                    "/always - 매번 알림 모드\n"
                    "/available - 예약 가능할 때만\n\n"
                    "<b>⚙️ 제어:</b>\n"
                    "/stop - 모니터링 중지\n"
                    "/start - 모니터링 재시작\n"
                    "/help - 도움말\n\n"
                    "<b>현재 설정:</b>\n"
                    f"모드: {mode_text}\n"
                    f"조회 날짜: 2026년 2월 14일\n"
                    f"체크 주기: 5분마다 (Render.com)"
                )
    
    # 처리한 메시지 삭제 (다음번에 다시 처리하지 않도록)
    if last_update_id:
        get_bot_updates(offset=last_update_id + 1)
    
    return command_result

def send_telegram_message(message):
    """텔레그램으로 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return None

def get_reservation_data(target_date="20260214"):
    """특정 날짜의 예약 정보를 API로 가져오기"""
    api_url = "https://www.museum.go.kr/ticket_reservation/Web/Book/GetBookPlaySequence.json"
    
    params = {
        "shop_code": "102830101202",
        "play_date": target_date,
        "product_group_code": "0101"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Referer': 'https://www.museum.go.kr/MUSEUM/contents/M0104010000.do?schM=child&act=intro',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API 요청 실패: {e}")
        return None

def check_reservation():
    """2월 14일 예약 정보 확인"""
    
    # 먼저 명령어 확인
    command = process_commands()
    
    # 한국 시간 (KST = UTC+9)
    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    current_mode = get_notification_mode()
    
    # /stop 명령으로 중지된 경우
    if current_mode == 'stopped' and command not in ['status', 'test']:
        print(f"[{current_time}] 모니터링 중지 상태 - 체크 생략")
        return True
    
    # 2월 14일 예약 정보 가져오기
    data = get_reservation_data("20260214")
    
    if not data:
        # API 실패 시 항상 알림 (중요한 오류)
        error_message = f"⚠️ <b>API 호출 실패</b>\n"
        error_message += f"⏰ 시간: {current_time}\n\n"
        error_message += "예약 정보를 가져올 수 없습니다.\n"
        error_message += "페이지가 변경되었거나 네트워크 오류일 수 있습니다."
        
        print(error_message)
        if current_mode != 'stopped':
            send_telegram_message(error_message)
        return False
    
    # 메시지 생성
    status_message = f"🔍 <b>박물관 예약 체크</b>\n"
    status_message += f"⏰ 체크 시간: {current_time}\n"
    status_message += f"📅 조회 날짜: 2026년 2월 14일\n"
    
    # 명령어에 따른 메시지 추가
    if command == 'status':
        status_message += f"💡 /status 명령으로 즉시 조회\n"
    elif command == 'test':
        status_message += f"🧪 /test 명령으로 테스트 실행\n"
    
    status_message += f"━━━━━━━━━━━━━━━━━\n\n"
    
    target_times_available = False
    
    try:
        if isinstance(data, dict) and 'data' in data:
            book_data = data.get('data', {})
            
            if isinstance(book_data, dict):
                time_slots = book_data.get('bookPlaySequenceList', [])
            else:
                time_slots = []
            
            if time_slots:
                status_message += f"📊 <b>예약 현황</b>\n\n"
                
                found_10am = False
                target_times_available = False  # 목표 시간대 예약 가능 여부
                
                for slot in time_slots:
                    start_time = slot.get('start_time', '')
                    end_time = slot.get('end_time', '')
                    
                    if len(start_time) == 4:
                        start_formatted = f"{start_time[:2]}:{start_time[2:]}"
                    else:
                        start_formatted = start_time
                    
                    if len(end_time) == 4:
                        end_formatted = f"{end_time[:2]}:{end_time[2:]}"
                    else:
                        end_formatted = end_time
                    
                    # 16:30 시간대는 표시하지 않음
                    if start_formatted.startswith('16:30'):
                        continue
                    
                    play_time = f"{start_formatted} ~ {end_formatted}"
                    
                    book_yn = slot.get('book_yn', '0')
                    is_bookable = book_yn == '1'
                    
                    book_remain = slot.get('book_remain_count', 0)
                    
                    # 10시 타임 확인
                    if start_formatted.startswith('10:'):
                        found_10am = True
                    
                    # 목표 시간대(10:00, 12:00, 13:30, 15:00) 중 4명 이상 예약 가능한지 확인
                    if start_formatted in ['10:00', '12:00', '13:30', '15:00']:
                        if is_bookable and book_remain >= 4:
                            target_times_available = True
                    
                    if book_remain > 0:
                        status_icon = "✅"
                        status_text = "예약 가능"
                    else:
                        status_icon = "❌"
                        status_text = "매진"
                    
                    status_message += f"{status_icon} <b>{play_time}</b>\n"
                    status_message += f"   🎫 온라인 예약: {book_remain}명 ({status_text})\n"
                
                if target_times_available:
                    status_message += "\n🎯 <b>목표 시간대 예약 가능!</b>\n"
                    status_message += "<b>(10:00, 12:00, 13:30, 15:00 중 4명 이상)</b>\n\n"
                    status_message += f"🔗 <a href='https://www.museum.go.kr/MUSEUM/contents/M0104010000.do?schM=child&act=intro'>지금 바로 예약하러 가기</a>\n"
                    status_message += "⚠️ <b>서둘러 확인하세요!</b>"
                elif found_10am:
                    status_message += "\nℹ️ 목표 시간대가 아직 4명 이상 예약 가능하지 않습니다."
                else:
                    status_message += "\nℹ️ 아직 10시 타임 정보가 표시되지 않았습니다."
            else:
                status_message += "ℹ️ 예약 가능한 시간대가 없습니다.\n"
                status_message += "아직 예약이 오픈되지 않았을 수 있습니다."
        else:
            status_message += "📋 <b>API 응답 내용:</b>\n"
            status_message += f"<code>{json.dumps(data, ensure_ascii=False, indent=2)[:500]}</code>\n\n"
            status_message += "예약 정보 구조를 확인 중입니다."
    
    except Exception as e:
        status_message += f"❌ 데이터 파싱 오류\n"
        status_message += f"상세: {str(e)}\n\n"
        status_message += f"원본 데이터:\n<code>{str(data)[:300]}</code>"
    
    # 알림 모드에 따라 메시지 전송 결정
    should_send = False
    
    # 명령어로 직접 요청한 경우 항상 전송
    if command in ['status', 'test']:
        should_send = True
    elif current_mode == 'always':
        # 매번 알림 모드
        should_send = True
    elif current_mode == 'available_only':
        # 예약 가능할 때만 알림 (목표 시간대 4명 이상)
        if target_times_available:
            should_send = True
        else:
            print(f"[{current_time}] 목표 시간대 예약 불가 - 알림 생략 (available_only 모드)")
    elif current_mode == 'stopped':
        # 중지 모드 (위에서 이미 처리했지만 안전장치)
        should_send = False
    
    # 메시지 전송
    if should_send:
        print(status_message)
        send_telegram_message(status_message)
    
    return True

if __name__ == "__main__":
    print("박물관 예약 모니터링 시작...")
    
    # 텔레그램 설정 확인
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 텔레그램 설정이 없습니다!")
        print("TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정해주세요.")
    else:
        # 예약 확인 실행
        check_reservation()
