from flask import Flask, render_template, request, send_file, jsonify
from playwright.sync_api import sync_playwright
import os, io, json, re, base64
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
JUBO_FILE = os.path.join(DATA_DIR, 'jubo_data.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

DEFAULT_SETTINGS = {
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


# === JSON 파일 유틸 ===
def _load_json(filepath, default=None):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def _save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_settings():
    settings = _load_json(SETTINGS_FILE, {})
    # 기본값 병합
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
    return settings


def _get_jubo_list():
    return _load_json(JUBO_FILE, [])


def _save_jubo_list(data):
    _save_json(JUBO_FILE, data)


# === 라우트 ===
@app.route('/')
def form():
    return render_template('form.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        settings = _get_settings()
        for key in request.form:
            settings[key] = request.form[key]
        _save_json(SETTINGS_FILE, settings)
        return render_template('settings.html', settings=settings, saved=True)
    return render_template('settings.html', settings=_get_settings(), saved=False)


@app.route('/api/save', methods=['POST'])
def save_jubo():
    payload = request.get_json()
    title = payload.get('title') or payload['data'].get('date') or '제목없음'
    is_draft = payload.get('is_draft', True)
    now = datetime.now().isoformat()

    jubo_list = _get_jubo_list()
    jubo_id = payload.get('id')

    if jubo_id:
        for item in jubo_list:
            if item['id'] == jubo_id:
                item['title'] = title
                item['data'] = payload['data']
                item['is_draft'] = is_draft
                item['updated_at'] = now
                break
    else:
        jubo_id = max([j['id'] for j in jubo_list], default=0) + 1
        jubo_list.append({
            'id': jubo_id,
            'title': title,
            'date': payload['data'].get('date', ''),
            'is_draft': is_draft,
            'data': payload['data'],
            'created_at': now,
            'updated_at': now,
        })

    _save_jubo_list(jubo_list)
    return jsonify({'id': jubo_id, 'message': '저장되었습니다.'})


@app.route('/api/list')
def list_jubo():
    filter_type = request.args.get('type', 'all')
    jubo_list = _get_jubo_list()
    if filter_type == 'draft':
        jubo_list = [j for j in jubo_list if j.get('is_draft')]
    elif filter_type == 'published':
        jubo_list = [j for j in jubo_list if not j.get('is_draft')]
    # 목록 반환 시 data 제외
    result = [{'id': j['id'], 'title': j['title'], 'date': j.get('date',''),
               'is_draft': j.get('is_draft', True), 'updated_at': j.get('updated_at','')}
              for j in sorted(jubo_list, key=lambda x: x.get('updated_at',''), reverse=True)]
    return jsonify(result)


@app.route('/api/load/<int:jubo_id>')
def load_jubo(jubo_id):
    jubo_list = _get_jubo_list()
    for item in jubo_list:
        if item['id'] == jubo_id:
            return jsonify(item)
    return jsonify({'error': '찾을 수 없습니다.'}), 404


@app.route('/api/delete/<int:jubo_id>', methods=['DELETE'])
def delete_jubo(jubo_id):
    jubo_list = _get_jubo_list()
    jubo_list = [j for j in jubo_list if j['id'] != jubo_id]
    _save_jubo_list(jubo_list)
    return jsonify({'message': '삭제되었습니다.'})


# === JSON 내보내기/불러오기 ===
@app.route('/api/export')
def export_json():
    """전체 데이터(주보+설정)를 JSON으로 다운로드"""
    export_data = {
        'settings': _get_settings(),
        'jubo_list': _get_jubo_list(),
        'exported_at': datetime.now().isoformat(),
    }
    buf = io.BytesIO(json.dumps(export_data, ensure_ascii=False, indent=2).encode('utf-8'))
    return send_file(buf, download_name='church_weekly_backup.json', as_attachment=True, mimetype='application/json')


@app.route('/api/import', methods=['POST'])
def import_json():
    """JSON 파일 업로드로 데이터 복원"""
    file = request.files.get('file')
    if not file:
        return jsonify({'error': '파일이 없습니다.'}), 400
    data = json.loads(file.read().decode('utf-8'))
    if 'settings' in data:
        _save_json(SETTINGS_FILE, data['settings'])
    if 'jubo_list' in data:
        _save_jubo_list(data['jubo_list'])
    return jsonify({'message': '불러오기 완료!'})


# === 미리보기 / PDF ===
@app.route('/preview', methods=['POST'])
def preview():
    data = _parse_form(request)
    return render_template('jubo.html', **data)


@app.route('/generate', methods=['POST'])
def generate():
    data = _parse_form(request)
    html = _prepare_html(data)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        pdf = page.pdf(format='A4', print_background=True)
        browser.close()

    return send_file(io.BytesIO(pdf), download_name=f'주보_{data["date"]}.pdf', as_attachment=True)


@app.route('/generate_images', methods=['POST'])
def generate_images():
    import zipfile
    data = _parse_form(request)
    html = _prepare_html(data)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page(viewport={'width': 794, 'height': 1123})
        page.set_content(html, wait_until='networkidle')
        pages = page.query_selector_all('.page')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for i, el in enumerate(pages):
                img = el.screenshot(type='png')
                zf.writestr(f'주보_{data["date"]}_{i+1}면.png', img)
        browser.close()

    buf.seek(0)
    return send_file(buf, download_name=f'주보_{data["date"]}_이미지.zip', as_attachment=True)


def _prepare_html(data):
    html = render_template('jubo.html', **data)
    css_path = os.path.join(app.static_folder, 'css', 'jubo.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    html = html.replace(
        '<link rel="stylesheet" href="/static/css/jubo.css">',
        f'<style>{css_content}</style>'
    )
    def replace_img(match):
        src = match.group(1)
        if src.startswith('/static/'):
            filepath = os.path.join(app.static_folder, src.replace('/static/', ''))
        else:
            return match.group(0)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as img_f:
                b64 = base64.b64encode(img_f.read()).decode()
            ext = os.path.splitext(filepath)[1].lstrip('.')
            if ext == 'jpg':
                ext = 'jpeg'
            return f'src="data:image/{ext};base64,{b64}"'
        return match.group(0)
    html = re.sub(r'src="([^"]+)"', replace_img, html)
    return html


# === 폼 파싱 ===
def _parse_form(req):
    f = req.form
    new_member_photo = ''
    if 'new_member_photo' in req.files:
        file = req.files['new_member_photo']
        if file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            new_member_photo = f'/static/uploads/{file.filename}'

    event_photo = ''
    if 'event_photo' in req.files:
        file = req.files['event_photo']
        if file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            event_photo = f'/static/uploads/{file.filename}'

    letter_photo = ''
    if 'letter_photo' in req.files:
        file = req.files['letter_photo']
        if file.filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            letter_photo = f'/static/uploads/{file.filename}'

    return {
        'date': f.get('date', ''),
        'volume': f.get('volume', ''),
        'issue': f.get('issue', ''),
        'year_theme': f.get('year_theme', ''),
        'sermon_title': f.get('sermon_title', ''),
        'sermon_author': f.get('sermon_author', ''),
        'sermon_body': f.get('sermon_body', ''),
        'new_member_name': f.get('new_member_name', ''),
        'new_member_photo': new_member_photo,
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
        'announcements': [a for a in f.getlist('announcements') if a.strip()],
        'duty_rows': _parse_duty(f),
        'duty_offer_groups': _parse_duty_offer(f),
        'duty_lunch': _parse_duty_lunch(f),
        'duty_cleaning': f.get('duty_cleaning', ''),
        'letter_title': f.get('letter_title', ''),
        'letter_body': f.get('letter_body', ''),
        'letter_author': f.get('letter_author', ''),
        'letter_photo_caption': f.get('letter_photo_caption', ''),
        'letter_photo': letter_photo,
        'event_photo': event_photo,
        'event_caption': f.get('event_caption', ''),
        'bible_verses': f.get('bible_verses', ''),
        **_get_settings(),
    }


def _parse_worship(f, prefix):
    items = []
    i = 0
    while True:
        label = f.get(f'{prefix}_label_{i}')
        if label is None:
            break
        items.append({'label': label, 'value': f.get(f'{prefix}_value_{i}', '')})
        i += 1
    return items


def _parse_duty(f):
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
    return [
        {'offer2': f.get('duty_offer_group1_2bu', '').replace('\n', '<br>'),
         'offer3': f.get('duty_offer_group1_3bu', '').replace('\n', '<br>'),
         'etc': f.get('duty_offer_group1_etc', '').replace('\n', '<br>')},
        {'offer2': f.get('duty_offer_group2_2bu', '').replace('\n', '<br>'),
         'offer3': f.get('duty_offer_group2_3bu', '').replace('\n', '<br>'),
         'etc': f.get('duty_offer_group2_etc', '').replace('\n', '<br>')},
    ]


def _parse_duty_lunch(f):
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
