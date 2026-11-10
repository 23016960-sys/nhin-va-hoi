"""CPU person detection and transparent garment-region color estimates."""
from pathlib import Path
from collections import Counter
import base64,io,threading,time
import cv2
import numpy as np
from PIL import Image,ImageOps,UnidentifiedImageError

ROOT=Path(__file__).resolve().parent
cv2.setNumThreads(2)
COLOR_HEX={'đen':'#242832','trắng':'#eeeeea','xám':'#92969e','đỏ':'#d84a49',
    'cam':'#e68c3d','vàng':'#e0c445','xanh lá':'#4f975d','xanh dương':'#3f78bd',
    'tím':'#8560aa','hồng':'#dc85b0','nâu':'#88634a','be/kem':'#cfbea0'}

def read_image(payload):
    try:
        image=Image.open(io.BytesIO(payload))
        if image.width*image.height>24_000_000:
            raise ValueError('Ảnh quá lớn. Vui lòng chọn ảnh dưới 24 megapixel.')
        image=ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((1600,1600),Image.Resampling.LANCZOS)
        return np.asarray(image).copy()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError('Không đọc được ảnh. Hãy chọn file JPG, PNG hoặc WebP hợp lệ.') from exc

def data_url(rgb,max_size=None):
    image=Image.fromarray(rgb)
    if max_size:image.thumbnail(max_size,Image.Resampling.LANCZOS)
    stream=io.BytesIO();image.save(stream,format='JPEG',quality=88)
    return 'data:image/jpeg;base64,'+base64.b64encode(stream.getvalue()).decode('ascii')

def color_profile(rgb):
    if not rgb.size:return {'label':'chưa rõ','primary':None,'coverage':0,'colors':[]}
    pixels=cv2.resize(rgb,(96,96),interpolation=cv2.INTER_AREA)
    h,s,v=np.moveaxis(cv2.cvtColor(pixels,cv2.COLOR_RGB2HSV),-1,0)
    labels=np.full(h.shape,'xám',dtype='<U15')
    chroma=s>=35
    labels[chroma&(h<10)]='đỏ';labels[chroma&(h>=170)]='đỏ'
    labels[chroma&(h>=10)&(h<24)]='cam'
    labels[chroma&(h>=24)&(h<38)]='vàng'
    labels[chroma&(h>=38)&(h<90)]='xanh lá'
    labels[chroma&(h>=90)&(h<130)]='xanh dương'
    labels[chroma&(h>=130)&(h<155)]='tím'
    labels[chroma&(h>=155)&(h<170)]='hồng'
    labels[(h>=8)&(h<28)&(s>=75)&(v<165)]='nâu'
    labels[(h>=8)&(h<38)&(s>=25)&(s<100)&(v>=125)]='be/kem'
    labels[(s<38)&(v>=195)]='trắng'
    labels[(s<30)&(v>=48)&(v<195)]='xám'
    labels[v<48]='đen'
    labels[(h>=90)&(h<130)&(s>=85)&(v>=28)&(v<100)]='xanh dương'
    counts=Counter(labels.reshape(-1).tolist())
    top=counts.most_common(3);total=labels.size
    colors=[{'name':name,'share':round(count/total,4),'hex':COLOR_HEX[name]} for name,count in top]
    primary,coverage=colors[0]['name'],colors[0]['share']
    mixed=len(colors)>1 and colors[1]['share']>=0.22
    label=primary+' / '+colors[1]['name'] if mixed else primary
    if coverage<0.38:label='nhiều màu, chưa rõ màu chính'
    return {'label':label,'primary':primary if coverage>=0.38 else None,
            'coverage':coverage,'colors':colors,'mixed':mixed}

class PersonDetector:
    def __init__(self,backend='yolo',confidence=0.40):
        self.backend,self.confidence=backend,confidence
        self.lock=threading.Lock()
        if backend in ('yolo','nano'):
            import onnxruntime as ort
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            filename='yolov5n.onnx' if backend=='nano' else 'yolov5s.onnx'
            self.net=ort.InferenceSession(str(ROOT/'models'/filename),options,
                                         providers=['CPUExecutionProvider'])
            self.input_name=self.net.get_inputs()[0].name
            self.input_dtype=np.float16 if 'float16' in self.net.get_inputs()[0].type else np.float32
        else:
            # OpenCV's Windows path reader can fail on Vietnamese directory names.
            self.net=cv2.dnn.readNetFromCaffe(np.frombuffer((ROOT/'models/deploy.prototxt').read_bytes(),np.uint8),
                np.frombuffer((ROOT/'models/mobilenet_iter_73000.caffemodel').read_bytes(),np.uint8))

    def detect(self,rgb):
        height,width=rgb.shape[:2]
        with self.lock:
            if self.backend in ('yolo','nano'):
                scale=min(640/width,640/height)
                nw,nh=round(width*scale),round(height*scale)
                left,top=(640-nw)//2,(640-nh)//2
                canvas=np.full((640,640,3),114,np.uint8)
                canvas[top:top+nh,left:left+nw]=cv2.resize(rgb,(nw,nh))
                tensor=np.transpose(canvas.astype(np.float32)/255,(2,0,1))[None].astype(self.input_dtype)
                raw=self.net.run(None,{self.input_name:tensor})[0][0]
                boxes,scores=[],[]
                for row in raw:
                    score=float(row[4]*row[5])  # COCO class 0: person
                    if score<self.confidence:continue
                    cx,cy,bw,bh=map(float,row[:4])
                    x1=(cx-bw/2-left)/scale;y1=(cy-bh/2-top)/scale
                    boxes.append([x1,y1,bw/scale,bh/scale]);scores.append(score)
                keep=cv2.dnn.NMSBoxes(boxes,scores,self.confidence,0.45)
                detections=[(boxes[int(i)],scores[int(i)]) for i in np.asarray(keep).reshape(-1)]
            else:
                bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
                self.net.setInput(cv2.dnn.blobFromImage(bgr,1/127.5,(300,300),127.5))
                raw=self.net.forward()[0,0]
                detections=[]
                for row in raw:
                    if int(row[1])!=15 or row[2]<self.confidence:continue
                    x1,y1,x2,y2=row[3:7]*np.array([width,height,width,height])
                    detections.append(([x1,y1,x2-x1,y2-y1],float(row[2])))
        result=[]
        for (x,y,w,h),score in detections:
            x1,y1=max(0,round(x)),max(0,round(y));x2,y2=min(width,round(x+w)),min(height,round(y+h))
            if x2-x1>=12 and y2-y1>=30:result.append({'box':[x1,y1,x2,y2],'score':round(score,4)})
        result.sort(key=lambda p:(p['box'][0]+p['box'][2])/2)
        return result

def region_for(box,field,image_shape):
    x1,y1,x2,y2=box;w,h=x2-x1,y2-y1
    half_body=h/max(w,1)<1.5
    if field=='shirt':a,b=(0.40,0.78) if half_body else (0.23,0.49)
    else:a,b=0.58,0.84
    return [round(x1+w*0.25),round(y1+h*a),round(x1+w*0.75),round(y1+h*b)]

def analyze_image(rgb,detector):
    started=time.perf_counter();height,width=rgb.shape[:2]
    people=detector.detect(rgb)
    for i,p in enumerate(people,1):
        p['id']=i;x1,y1,x2,y2=p['box'];w,h=x2-x1,y2-y1
        center=(x1+x2)/(2*width)
        p['position']='bên trái' if center<1/3 else ('bên phải' if center>2/3 else 'ở giữa')
        p['center_x']=round(center,4)
        p['crop']=data_url(rgb[y1:y2,x1:x2],(160,240))
        clipped_sliver=(x1<=2 or x2>=width-2) and w/width<0.16
        for field in ['shirt','pants']:
            box=region_for(p['box'],field,rgb.shape);rx1,ry1,rx2,ry2=box
            side_cut=(x1<=2 or x2>=width-2) and w/max(h,1)<0.45
            uncertain=clipped_sliver or (field=='pants' and (h/max(w,1)<1.5 or y2>=height-2 or side_cut))
            profile=color_profile(rgb[ry1:ry2,rx1:rx2])
            profile['region']=box
            profile['crop']=data_url(rgb[ry1:ry2,rx1:rx2],(150,100))
            profile['available']=not uncertain and profile['primary'] is not None
            profile['reason']='Vùng trang phục bị cắt hoặc chưa đủ rõ.' if uncertain else ''
            if uncertain:profile.update(label='chưa đủ rõ',primary=None)
            p[field]=profile
    return {'width':width,'height':height,'image':data_url(rgb),'people':people,
            'elapsed_ms':round((time.perf_counter()-started)*1000,1),'detector':detector.backend}
