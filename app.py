from pathlib import Path
from collections import OrderedDict
import threading,time,uuid,os
from flask import Flask,request,jsonify,render_template
from werkzeug.exceptions import RequestEntityTooLarge
from vision import read_image,analyze_image,PersonDetector
from nlu import QuestionParser
from reasoning import answer_question

ROOT=Path(__file__).resolve().parent

def create_app():
    app=Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=8*1024*1024,JSON_AS_ASCII=False)
    app.json.ensure_ascii=False
    app.config['PUBLIC_DEPLOYMENT']=os.environ.get('PUBLIC_DEPLOYMENT','0')=='1'
    max_sessions=max(1,int(os.environ.get('MAX_SESSIONS','10')))
    sessions=OrderedDict();session_lock=threading.Lock()
    parser=QuestionParser();detector=None;init_lock=threading.Lock()

    def get_detector():
        nonlocal detector
        with init_lock:
            if detector is None:detector=PersonDetector()
        return detector

    def purge():
        now=time.time()
        expired=[sid for sid,(created,data) in sessions.items() if now-created>20*60]
        for sid in expired:sessions.pop(sid,None)
        while len(sessions)>max_sessions:sessions.popitem(last=False)

    def process(payload):
        rgb=read_image(payload);analysis=analyze_image(rgb,get_detector())
        sid=uuid.uuid4().hex
        with session_lock:
            sessions[sid]=(time.time(),analysis);purge()
        return jsonify({'image_id':sid,**analysis})

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        if request.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def index():return render_template('index.html',public_deployment=app.config['PUBLIC_DEPLOYMENT'])

    @app.get('/healthz')
    def health():
        ready=(ROOT/'models/yolov5s.onnx').is_file()
        return jsonify(ok=ready),200 if ready else 503

    @app.get('/api/status')
    def status():
        return jsonify({'ready':(ROOT/'models/yolov5s.onnx').exists(),
                        'max_upload_mb':8,'session_minutes':20,
                        'public_deployment':app.config['PUBLIC_DEPLOYMENT']})

    @app.post('/api/analyze')
    def analyze():
        file=request.files.get('image')
        if file is None:return jsonify(error='Bạn chưa chọn ảnh.'),400
        try:return process(file.read())
        except ValueError as exc:return jsonify(error=str(exc)),400
        except FileNotFoundError:return jsonify(error='Thiếu trọng số. Chạy python download_assets.py rồi thử lại.'),503

    @app.post('/api/demo')
    def demo():
        return process((ROOT/'samples/bus.jpg').read_bytes())

    @app.post('/api/ask')
    def ask():
        body=request.get_json(silent=True)
        if not isinstance(body,dict):return jsonify(error='Yêu cầu không hợp lệ.'),400
        question=body.get('question','')
        if not isinstance(question,str) or not 1<=len(question.strip())<=500:
            return jsonify(error='Câu hỏi cần từ 1 đến 500 ký tự.'),400
        sid=body.get('image_id')
        if not isinstance(sid,str):return jsonify(error='Bạn cần tải ảnh trước.'),400
        with session_lock:
            purge();session=sessions.get(sid)
        if session is None:return jsonify(error='Ảnh đã hết phiên hoặc không còn trong bộ nhớ. Bạn tải lại ảnh nhé.'),404
        selected=body.get('selected_person')
        if selected is not None and (type(selected) is not int or selected<1):
            return jsonify(error='Số người được chọn không hợp lệ.'),400
        started=time.perf_counter();plan=parser.parse(question)
        result=answer_question(session[1],plan,selected)
        result['elapsed_ms']=round((time.perf_counter()-started)*1000,1)
        return jsonify(result)

    @app.delete('/api/image/<sid>')
    def clear(sid):
        with session_lock:sessions.pop(sid,None)
        return jsonify(ok=True)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(exc):return jsonify(error='Ảnh vượt quá 8 MB. Bạn chọn ảnh nhỏ hơn nhé.'),413

    return app

if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.environ.get('APP_PORT','7861')),debug=False,threaded=True)
