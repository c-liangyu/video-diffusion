import argparse
import os

import numpy as np
import tensorflow as tf
from PIL import Image
from skimage.io import imsave
from tensorflow.python.platform import gfile

parser = argparse.ArgumentParser()
parser.add_argument('--data_dir', default='', help='base directory to save processed data')
opt = parser.parse_args()


def get_seq(dname):
    data_dir = '%s/softmotion30_44k/%s' % (opt.data_dir, dname)

    filenames = sorted(gfile.Glob(os.path.join(data_dir, '*')))
    if not filenames:
        raise RuntimeError('No data files found.')

    for f in filenames:
        k = 0
        for serialized_example in tf.compat.v1.io.tf_record_iterator(f):
            example = tf.train.Example()
            example.ParseFromString(serialized_example)
            image_seq = []
            for i in range(30):
                image_name = str(i) + '/image_aux1/encoded'
                byte_str = example.features.feature[image_name].bytes_list.value[0]
                # img = Image.open(io.BytesIO(byte_str))
                img = Image.frombytes('RGB', (64, 64), byte_str)
                arr = np.array(img.getdata()).reshape(img.size[1], img.size[0], 3)
                image_seq.append(arr.reshape(1, 64, 64, 3))
            image_seq = np.concatenate(image_seq, axis=0).astype("uint8")
            k = k + 1
            yield f, k, image_seq


def convert_data(dname):
    print(dname)
    seq_generator = get_seq(dname)
    n = 0
    while True:
        n += 1
        try:
            f, k, seq = next(seq_generator)
        except StopIteration:
            break
        f = f.split('/')[-1]
        dir = '%s/processed_data/%s/%s/%d/' % (opt.data_dir, dname, f[:-10], k)
        os.makedirs(dir, exist_ok=True)
        for i in range(len(seq)):
            imsave(os.path.join(dir, f"{i}.png"), seq[i])
        print('%s data: %s (%d)  (%d)' % (dname, f, k, n))


convert_data('test')
convert_data('train')