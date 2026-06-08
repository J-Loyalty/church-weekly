from flask import Flask, render_template, request, send_file, jsonify
from playwright.sync_api import sync_playwright
import os, io, json, sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_PATH = 'jubo.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS jubo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT,
        is_draft INTEGER DEFAULT 0,
        data TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')
    # 초기값 삽입 (없을 때만)
    defaults = {
        'church_intro': '주님을 기쁘시게 하는 교회입니다.\n주님과 함께 행복한 교회로써\n주일이 기다려지는 교회, 신앙생활에 기쁨이 있는 교회,\n받은 기쁨 때문에 자신과 이웃을 넘어\n온 민족에 복음을 전하는 소망을 가진 교회입니다.',
        'church_denomination': '김포남현교회는 대한예수교 장로회(합동)로서, 사당동 총신대학(신학대학원)에 소속한 역사와 정통성이 있는 교단으로 황동노회 강서시찰에 소속되어 있습니다.',
        'church_vision': '① 천국의 기쁨을 경험하고 천국을 확장하는 교회(선교)\n② 개인과 이웃· 민족을 치유하는 교회(자유)\n③ 다음 세대를 준비하는 교회(인재양성)\n④ 예수님의 사랑을 실천하는 교회(봉사)',
        'church_pastors': '◆ 담임목사: 송영환(syh-3927@hanmail.net)\n◆ 부 목 사: 김한준(manjun7@hanmail.net)\n◆ 부 목 사: 윤도수(j-load@hanmail.net)\n◆ 교육목사: 김진서(rlawlstj99@naver.com)\n◆ 약목목사: 김기현(kihyun91@naver.com)\n◆ 파송선교사: 이영섭, 김덕순(케냐)',
        'church_elders': '◆ 시무장로: 김기송, 여두현, 장윤봉, 김철희, 박종렬\n◆ 협동장로: 이순홍, 고재욱\n◆ 은퇴장로: 최연김, 오성열, 박문수, 황용구, 김갑식, 이석도, 박종청, 이학구',
        'church_contact': '전 화: 031-988-9182   팩 스: 031-989-3927\n주 소: 경기도 김포시 통진읍 서암로 116(공영주차장 옆)\n홈페이지: www.nam-hyun.org',
        'church_offering': '헌금통장: 농협 241050-55-0036-86 (김포남현교회)',
        'church_mission': '• 선교사\n김상식, 이성진(필리핀) / 최인혁, 윤혜진(케냐)\n장성영, 박나미(태국) / 정하늘, 김소망(B국)\n허용구, 홍수정(인도네시아)\n• 국내 교회(기관)\n시흥남현교회/ 삼홍교회/ 하나백 교회/ 총회GMS\n두란노 아버지 학교/ 총신대학원/ 평안누리교회',
        'gospel_items': '● 죄 문제가 해결됩니다.|당신의 모든 죄는 용서받았습니다. 죄책감이 사라집니다.\n● 사랑하게 됩니다.|사람을 진정으로 사랑하며 살게 됩니다.\n● 지옥 안갑니다.|주님께서 이미 당신을 사망에서 생명으로 옮기셨습니다.\n● 하나님의 자녀가 됩니다.|자녀이면 상속자, 당신은 하나님의 상속자입니다.\n● 저주가 끊어집니다.|당신을 향해 흐르던 저주는 이제 끊어졌습니다.\n● 참 평안과 기쁨이 넘칩니다.|세상이 줄 수 없는 기쁨이 당신 안에 솟아납니다.\n● 만족을 누리며 삽니다.|소유와 환경을 넘어, 당신은 만족하며 인생을 삽니다.\n● 천국에서 영원히 삽니다.|당신은 천국에서 영생을 보장 받은 복된 사람입니다.',
    }
    for key, value in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)', (key, value))
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def form():
    return render_template('form.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    conn = get_db()
    if request.method == 'POST':
        for key in request.form:
            conn.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)',
                         (key, request.form[key]))
        conn.commit()
        conn.close()
        return render_template('settings.html', settings=_get_settings(), saved=True)
    conn.close()
    return render_template('settings.html', settings=_get_settings(), saved=False)


def _get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}


@app.route('/api/save', methods=['POST'])
def save_jubo():
    """임시저장 또는 완성본 저장"""
    payload = request.get_json()
    data_json = json.dumps(payload['data'], ensure_ascii=False)
    title = payload.get('title') or payload['data'].get('date') or '제목없음'
    is_draft = 1 if payload.get('is_draft') else 0
    now = datetime.now().isoformat()

    conn = get_db()
    # 같은 id가 있으면 업데이트
    jubo_id = payload.get('id')
    if jubo_id:
        conn.execute('UPDATE jubo SET title=?, data=?, is_draft=?, updated_at=? WHERE id=?',
                     (title, data_json, is_draft, now, jubo_id))
    else:
        cur = conn.execute('INSERT INTO jubo(title, date, is_draft, data, created_at, updated_at) VALUES(?,?,?,?,?,?)',
                           (title, payload['data'].get('date', ''), is_draft, data_json, now, now))
        jubo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': jubo_id, 'message': '저장되었습니다.'})


@app.route('/api/list')
def list_jubo():
    """저장된 주보 목록 반환"""
    filter_type = request.args.get('type', 'all')  # all, draft, published
    conn = get_db()
    if filter_type == 'draft':
        rows = conn.execute('SELECT id, title, date, is_draft, created_at, updated_at FROM jubo WHERE is_draft=1 ORDER BY updated_at DESC').fetchall()
    elif filter_type == 'published':
        rows = conn.execute('SELECT id, title, date, is_draft, created_at, updated_at FROM jubo WHERE is_draft=0 ORDER BY updated_at DESC').fetchall()
    else:
        rows = conn.execute('SELECT id, title, date, is_draft, created_at, updated_at FROM jubo ORDER BY updated_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/load/<int:jubo_id>')
def load_jubo(jubo_id):
    """특정 주보 데이터 불러오기"""
    conn = get_db()
    row = conn.execute('SELECT * FROM jubo WHERE id=?', (jubo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '찾을 수 없습니다.'}), 404
    result = dict(row)
    result['data'] = json.loads(result['data'])
    return jsonify(result)


@app.route('/api/delete/<int:jubo_id>', methods=['DELETE'])
def delete_jubo(jubo_id):
    """주보 삭제"""
    conn = get_db()
    conn.execute('DELETE FROM jubo WHERE id=?', (jubo_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '삭제되었습니다.'})


@app.route('/preview', methods=['POST'])
def preview():
    data = _parse_form(request)
    return render_template('jubo.html', **data)


@app.route('/generate', methods=['POST'])
def generate():
    data = _parse_form(request)
    html = render_template('jubo.html', **data)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        pdf = page.pdf(format='A4', print_background=True)
        browser.close()

    return send_file(io.BytesIO(pdf), download_name=f'주보_{data["date"]}.pdf', as_attachment=True)


def _parse_form(req):
    f = req.form
    # 새가족 사진 처리
    new_member_photo = ''
    if 'new_member_photo' in req.files:
        file = req.files['new_member_photo']
        if file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            new_member_photo = f'/static/uploads/{file.filename}'

    # 행사 사진 처리
    event_photo = ''
    if 'event_photo' in req.files:
        file = req.files['event_photo']
        if file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            event_photo = f'/static/uploads/{file.filename}'

    return {
        'date': f.get('date', ''),
        'volume': f.get('volume', ''),
        'issue': f.get('issue', ''),
        'year_theme': f.get('year_theme', ''),
        # 1면 - 설교 칼럼
        'sermon_title': f.get('sermon_title', ''),
        'sermon_author': f.get('sermon_author', ''),
        'sermon_body': f.get('sermon_body', ''),
        'new_member_name': f.get('new_member_name', ''),
        'new_member_photo': new_member_photo,
        # 2면 좌 - 예배순서
        'worship_morning': _parse_worship(f, 'morning'),
        'worship_afternoon': _parse_worship(f, 'afternoon'),
        'worship_wednesday': _parse_worship(f, 'wednesday'),
        'worship_morning_name': f.get('worship_morning_name', '주일 오전예배'),
        'worship_morning_time': f.get('worship_morning_time', 'I부7:30 Ⅱ부9:30 Ⅲ부 11:30'),
        'worship_afternoon_name': f.get('worship_afternoon_name', '오후 찬양예배'),
        'worship_afternoon_time': f.get('worship_afternoon_time', '오후2:30'),
        'worship_wednesday_name': f.get('worship_wednesday_name', '수요 목장 연합예배'),
        'dawn_name': f.get('dawn_name', '새벽기도회(월~금)'),
        'dawn_time': f.get('dawn_time', '새벽5:30'),
        'dawn_content': f.get('dawn_content', '사도행전 - 로마서'),
        'dawn_leader': f.get('dawn_leader', '담당 교역자'),
        'sermon_morning_title': f.get('sermon_morning_title', ''),
        'sermon_afternoon_title': f.get('sermon_afternoon_title', ''),
        'sermon_wednesday_title': f.get('sermon_wednesday_title', ''),
        # 2면 우 - 교회소식
        'announcements': [a for a in f.getlist('announcements') if a.strip()],
        'duty_rows': _parse_duty(f),
        'duty_offer_groups': _parse_duty_offer(f),
        'duty_lunch': _parse_duty_lunch(f),
        'duty_cleaning': f.get('duty_cleaning', ''),
        # 3면 좌 - 편지 칼럼
        'letter_title': f.get('letter_title', ''),
        'letter_body': f.get('letter_body', ''),
        'letter_author': f.get('letter_author', ''),
        # 4면
        'event_photo': event_photo,
        'event_caption': f.get('event_caption', ''),
        'bible_verses': f.get('bible_verses', ''),
        # 고정 문구 (settings)
        **_get_settings(),
    }


def _parse_worship(f, prefix):
    """예배순서 각 항목을 파싱"""
    items = []
    i = 0
    while True:
        label = f.get(f'{prefix}_label_{i}')
        value = f.get(f'{prefix}_value_{i}')
        if label is None:
            break
        items.append({'label': label, 'value': value or ''})
        i += 1
    return items


def _parse_duty(f):
    """봉사위원 표 파싱 (동적 주차)"""
    rows = []
    i = 0
    while True:
        date = f.get(f'duty_date_{i}')
        if date is None:
            break
        if date.strip():
            rows.append({
                'date': date,
                'pray1': f.get(f'duty_pray1_{i}', ''),
                'pray2': f.get(f'duty_pray2_{i}', ''),
                'pray3': f.get(f'duty_pray3_{i}', ''),
                'pm': f.get(f'duty_pm_{i}', ''),
            })
        i += 1
    return rows


def _parse_duty_offer(f):
    """안내/헌금 2주 단위 파싱"""
    return [
        {'offer2': f.get('duty_offer_group1_2bu', '').replace('\n', '<br>'),
         'offer3': f.get('duty_offer_group1_3bu', '').replace('\n', '<br>'),
         'etc': f.get('duty_offer_group1_etc', '').replace('\n', '<br>')},
        {'offer2': f.get('duty_offer_group2_2bu', '').replace('\n', '<br>'),
         'offer3': f.get('duty_offer_group2_3bu', '').replace('\n', '<br>'),
         'etc': f.get('duty_offer_group2_etc', '').replace('\n', '<br>')},
    ]


def _parse_duty_lunch(f):
    """중식 섬김이 주별 파싱 (날짜+이름+목장)"""
    items = []
    i = 0
    while True:
        name = f.get(f'duty_lunch_name_{i}')
        if name is None:
            break
        items.append({
            'date': f.get(f'duty_lunch_date_{i}', ''),
            'name': name,
            'group': f.get(f'duty_lunch_group_{i}', ''),
        })
        i += 1
    return items


if __name__ == '__main__':
    app.run(debug=True, port=5000)
