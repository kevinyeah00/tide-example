from PIL import Image
import time
import argparse
import json
import os
import sys

from concurrent.futures import ThreadPoolExecutor


from loguru import logger

from facenet import Facenet

from tide import tide

cpu_num = 2 # 这里设置成你想运行的CPU个数
os.environ['OMP_NUM_THREADS'] = str(cpu_num)
os.environ['OPENBLAS_NUM_THREADS'] = str(cpu_num)
os.environ['MKL_NUM_THREADS'] = str(cpu_num)
os.environ['VECLIB_MAXIMUM_THREADS'] = str(cpu_num)
os.environ['NUMEXPR_NUM_THREADS'] = str(cpu_num)


def sink_serializer(msg):
    record = msg.record
    ns = record['extra'].pop('ns') if 'ns' in record['extra'] else None
    obj = {
        'time': ns if ns is not None else int(record['time'].timestamp()*1e9),
        'msg': record['message'],
        'level': record['level'].name,
    }
    obj.update(record['extra'])
    s = json.dumps(obj)
    print(s, file=sys.stderr)

logger.remove()
logger.add(sink_serializer, level='DEBUG')
logger = logger.opt(lazy=True)

model = None

FPS = 10
TOTAL_NUM = 100


@tide.fn()
def proce_img(img1, img2):
    global model
    assert model is not None
    
    # speed_test()
    print("---begin offload!---")
    logger.bind(ns=time.time_ns()).debug('App: ready to compute')

    probability = model.detect_image(img1, img2)

    logger.bind(ns=time.time_ns()).debug('App: compute complete')


    print("---offload result:", probability)
    return probability

def offload(img1, img2):
    rtn = tide.offload(proce_img, img1, img2)
    ret = tide.get(rtn)
    print(ret)



@tide.init()
def init():
    # print("---test!---")
    global model
    model = Facenet()
    print("model init complete!")

@tide.main()
def main():
    thr_pool = ThreadPoolExecutor(max_workers=1000)

    try:
        image_1 = Image.open('/app/facenet/img/1_001.jpg')
    except:
        print('Image_1 Open Error! Try again!')

    try:
        image_2 = Image.open('/app/facenet/img/1_002.jpg')
    except:
        print('Image_2 Open Error! Try again!')

    for _ in range(TOTAL_NUM):
        time.sleep(1./FPS)
        thr_pool.submit(offload, image_1, image_2)

    thr_pool.shutdown(wait=True)

    # rtns = []
    # for i in range(80):
    #     print('start offloading,', i)
    #     rtn = tide.offload(proce_img, image_1, image_2)
    #     rtns.append(rtn)
    #     time.sleep(0.3)
    

    # print('---ready to get!---')
    # # time.sleep(5)
    # for rtn in rtns:
    #     print('---begin to get!---')
    #     ret = tide.get(rtn)
    #     print('---get a result!---')
    #     print(ret)



if __name__ == "__main__":
    parser = argparse.ArgumentParser("Facenet Application")
    parser.add_argument("--fps", type=int, default=FPS, help="fps")
    parser.add_argument("--total", type=int, default=TOTAL_NUM, help="total")
    args = parser.parse_args()
    FPS = args.fps
    TOTAL_NUM = args.total
    logger.bind(FPS=args.fps, TOTAL_NUM=args.total).info("TideCtr: start the application")
    tide.run()
    print("facenet app ends")

