"""Download public model artifacts at setup/build time, never during inference."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
ASSETS={
    'models/yolov5n.onnx':'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx',
    'models/yolov5s.onnx':'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.onnx',
    'models/LICENSE-YOLOv5.txt':'https://raw.githubusercontent.com/ultralytics/yolov5/v7.0/LICENSE',
    'models/deploy.prototxt':'https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt',
    'models/mobilenet_iter_73000.caffemodel':'https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/mobilenet_iter_73000.caffemodel',
    'models/LICENSE-MobileNet-SSD.txt':'https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/LICENSE',
    'samples/bus.jpg':'https://raw.githubusercontent.com/ultralytics/assets/main/im/bus.jpg',
    'samples/LICENSE-Ultralytics.txt':'https://raw.githubusercontent.com/ultralytics/assets/main/LICENSE',
}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render',action='store_true',help='Only the production YOLOv5s model, demo image and licenses')
    args=parser.parse_args()
    manifest={}
    for relative,url in ASSETS.items():
        if args.render and relative not in {'models/yolov5s.onnx','models/LICENSE-YOLOv5.txt',
                                           'samples/bus.jpg','samples/LICENSE-Ultralytics.txt'}:
            continue
        path=ROOT/relative;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            print('Downloading',relative,flush=True)
            request=urllib.request.Request(url,headers={'User-Agent':'PersonImageQA-Educational/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:
                payload=response.read()
            path.write_bytes(payload)
        manifest[relative]={'source':url,'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Assets ready.')

if __name__=='__main__':main()
