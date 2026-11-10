"""Vietnamese intent classifier plus explicit, auditable referent extraction."""
import re,unicodedata
from pathlib import Path
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parent
TRAIN={
 'count':['Có bao nhiêu người trong ảnh','Trong hình có mấy người','Đếm số người xuất hiện',
 'Tổng cộng bao nhiêu người','Bạn đếm giúp số người','Có bao nhiêu người mặc áo đỏ',
 'Mấy người ở bên trái','Có bao nhiêu người mặc quần đen','Tấm hình này có mấy người',
 'Số lượng người trong bức ảnh là bao nhiêu'],
 'shirt_color':['Người này mặc áo màu gì','Áo người bên trái có màu gì','Màu áo người số hai là gì',
 'Người đầu tiên mặc áo màu nào','Cho biết màu chiếc áo','Áo khoác của người số 2 màu gì',
 'Trang phục phía trên có màu gì','Bạn nhìn giúp áo người này màu gì',
 'Cho tôi biết người bên phải mặc áo màu gì','Áo của tất cả mọi người màu gì'],
 'pants_color':['Người bên phải mặc quần màu gì','Màu quần của người số 1','Quần người này màu nào',
 'Cho biết màu chiếc quần','Người thứ hai có quần màu gì','Màu sắc quần của người bên trái',
 'Quần dài của người ở giữa màu gì','Trang phục phía dưới có màu gì',
 'Người số ba đang mặc quần màu nào','Tất cả mọi người mặc quần màu gì'],
 'location':['Người số 2 đứng ở đâu','Vị trí của người đầu tiên','Người áo đỏ ở chỗ nào',
 'Người mặc quần đen nằm ở đâu trong ảnh','Người bên trái đứng ở vị trí nào',
 'Người áo trắng ở phía nào','Hãy chỉ vị trí người số 3','Người thứ hai đứng chỗ nào',
 'Người mặc áo xanh dương ở đâu','Tìm vị trí người áo đen'],
 'find_color':['Tìm người mặc áo đỏ','Ai mặc áo trắng','Chỉ người áo đen',
 'Có ai mặc áo màu xanh lá','Hãy tìm người có quần màu đen','Ai đang mặc quần xanh dương',
 'Chỉ cho tôi người có áo vàng','Tôi muốn tìm người mặc áo xanh dương',
 'Người nào mặc áo màu xám','Chọn người có áo màu be'],
 'describe':['Mô tả người số 1','Cho biết thông tin người bên trái','Người thứ hai trông thế nào',
 'Hãy mô tả trang phục của người này','Tóm tắt người đứng ở giữa','Thông tin về người số 3',
 'Mô tả người đang chọn','Cho tôi biết đặc điểm trang phục người bên phải',
 'Người này đang mặc gì','Mô tả tất cả mọi người'],
 'list_people':['Liệt kê các người trong ảnh','Cho xem danh sách người','Mô tả tất cả người trong hình',
 'Kể những người đã phát hiện','Cho biết trang phục của mọi người','Danh sách mọi người trong ảnh',
 'Tóm tắt tất cả người','Có những người nào trong hình','Liệt kê thông tin người',
 'Xem thông tin của tất cả mọi người']}

def normalize(text):
    text=unicodedata.normalize('NFKD',text.lower().replace('đ','d'))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())

def train_intent_model():
    xs,ys=[],[]
    for label,examples in TRAIN.items():
        for x in examples:xs.append(normalize(x));ys.append(label)
    model=make_pipeline(TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),sublinear_tf=True),
                        LogisticRegression(C=5,max_iter=1500,class_weight='balanced',random_state=42))
    model.fit(xs,ys)
    return model

class QuestionParser:
    def __init__(self):
        self.model=train_intent_model()

    def parse(self,question):
        text=normalize(question)
        probabilities=self.model.predict_proba([text])[0]
        classifier_intent=str(self.model.classes_[probabilities.argmax()])
        plan={'intent':classifier_intent,'classifier_intent':classifier_intent,
              'classifier_score':round(float(probabilities.max()),4),
              'id':None,'position':None,'color':None,'color_field':'shirt','all':False}
        number=re.search(r'(?:nguoi|so|thu)\s*(?:so|thu)?\s*(\d+)',text)
        number_words={'mot':1,'hai':2,'ba':3,'bon':4,'tu':4,'nam':5,'sau':6,'bay':7,'tam':8,'chin':9,'muoi':10}
        spelled=re.search(r'nguoi\s+(?:so|thu)\s+(mot|hai|ba|bon|tu|nam|sau|bay|tam|chin|muoi)\b',text)
        if number:plan['id']=int(number.group(1))
        elif spelled:plan['id']=number_words[spelled.group(1)]
        elif 'dau tien' in text:plan['id']=1
        for key,words in [('left',['ben trai','phia trai','ngoai cung trai']),
                          ('right',['ben phai','phia phai','ngoai cung phai']),
                          ('center',['o giua','chinh giua','trung tam'])]:
            if any(w in text for w in words):plan['position']=key
        plan['all']=any(w in text for w in ['tat ca','moi nguoi','toan bo','cac nguoi'])
        aliases=[('xanh duong',['xanh duong','xanh lam','xanh nuoc bien','blue']),
                 ('xanh la',['xanh la','xanh luc','green']),('be/kem',['mau be','ao be','mau kem','ao kem']),
                 ('do',['mau do','ao do','quan do']),('den',['mau den','ao den','quan den']),
                 ('trang',['mau trang','ao trang','quan trang']),('xam',['mau xam','ao xam','quan xam']),
                 ('hong',['mau hong','ao hong','quan hong']),('tim',['mau tim','ao tim','quan tim']),
                 ('vang',['mau vang','ao vang','quan vang']),('cam',['mau cam','ao cam','quan cam']),
                 ('nau',['mau nau','ao nau','quan nau'])]
        color_names={'xanh duong':'xanh dương','xanh la':'xanh lá','do':'đỏ','den':'đen','trang':'trắng',
                     'xam':'xám','hong':'hồng','tim':'tím','vang':'vàng','cam':'cam','nau':'nâu','be/kem':'be/kem'}
        for key,words in aliases:
            if any(re.search(r'\b'+re.escape(w)+r'\b',text) for w in words):
                plan['color']=color_names[key];break
        if 'xanh' in text and plan['color'] is None:plan['color']='ambiguous_green_blue'
        if plan['color'] and re.search(r'quan.{0,12}(?:mau )?(?:den|trang|do|xanh|xam|vang|nau|tim|hong|cam)',text):
            plan['color_field']='pants'
        # Explicit phrases take precedence; classifier handles paraphrases in the same domain.
        if any(w in text for w in ['bao nhieu nguoi','may nguoi','dem so nguoi','so luong nguoi','tong cong']):
            plan['intent']='count'
        elif any(w in text for w in ['o dau','cho nao','vi tri','phia nao']):plan['intent']='location'
        elif plan['color'] and (any(w in text for w in ['tim','ai ','nguoi nao','chi ','chon'])
                               or not any(w in text for w in ['mau gi','mau nao'])):
            plan['intent']='find_color'
        elif re.search(r'(ao|quan)[^?]{0,35}mau (?:gi|nao)',text):
            # The last garment before the requested color is the answer field;
            # another garment may only identify the person (black pants, for example).
            requested=re.findall(r'(ao|quan)(?:(?!ao|quan).){0,35}mau (?:gi|nao)',text)
            if requested:plan['intent']='pants_color' if requested[-1]=='quan' else 'shirt_color'
        elif 'quan' in text and any(w in text for w in ['mau','phia duoi']):plan['intent']='pants_color'
        elif ('ao' in text or 'phia tren' in text) and any(w in text for w in ['mau','mac gi']):
            plan['intent']='shirt_color'
        elif any(w in text for w in ['liet ke','danh sach','tat ca','moi nguoi','toan bo']):plan['intent']='list_people'
        elif any(w in text for w in ['mo ta','thong tin','trang phuc','mac gi']):plan['intent']='describe'
        else:
            domain=any(w in text for w in ['nguoi','ao','quan','trang phuc'])
            if not domain or plan['classifier_score']<0.38:plan['intent']='unsupported'
        # Questions outside supported visible attributes should never be forced into a clothing answer.
        if any(w in text for w in ['ten gi','la ai','tuoi','gioi tinh','nghe nghiep','dia chi','noi dung chu']):
            plan['intent']='unsupported'
        return plan
