import numpy

import cPickle as pkl
import gzip


def fopen(filename, mode='r'):
    if filename.endswith('.gz'):
        return gzip.open(filename, mode)
    return open(filename, mode)


class TextIterator:
    """a general text iterator."""

    def __init__(self,
                 dataset,
                 dicts,
                 voc_sizes,
                 batch_size=128,
                 maxlen=100):

        self.datasets  = [fopen(data, 'r') for data in dataset]
        self.dicts     = [pkl.load(open(dic, 'rb')) for dic in dicts]
        self.voc_sizes = voc_sizes
        self.buffers   = [[] for _ in self.datasets]

        self.batch_size = batch_size
        self.maxlen = maxlen
        self.nums = len(self.datasets)
        self.k = batch_size * 20  # cache=20
        self.end_of_data = False

    def __iter__(self):
        return self

    def reset(self):
        for i in range(self.nums):
            self.datasets[i].seek(0)

    def next(self):
        if self.end_of_data:
            self.end_of_data = False
            self.reset()
            raise StopIteration

        datasets = [[] for _ in self.datasets]

        # fill buffer, if it's empty
        assert len(self.buffers[0]) == len(self.buffers[1]), 'Buffer size mismatch!'

        if len(self.buffers[0]) == 0:
            for k_ in xrange(self.k):

                lines = [self.datasets[i].readline() for i in range(self.nums)]

                flag  = False
                for line in lines:
                    if line == "":
                        flag = True
                if flag:
                    break

                for ia in range(self.nums):
                    self.buffers[ia].append(lines[ia].strip().split())

            # sort by target buffer --- dafult setting:  source, target, tm-source, tm-target
            tidx = numpy.array([len(t) for t in self.buffers[1]]).argsort()
            for ib in range(self.nums):
                self.buffers[ib] = [self.buffers[ib][j] for j in tidx]

        flag2 = False
        for ic in range(self.nums):
            if len(self.buffers[ic]) == 0:
                flag2 = True

        if flag2:
            self.end_of_data = False
            self.reset()
            raise StopIteration

        try:

            # actual work here
            _samples = 0
            while True:

                # read from dataset file and map to word index
                # print _samples
                _lines = []
                for id in range(self.nums):
                    try:
                        line = self.buffers[id].pop()
                    except IndexError:
                        break

                    line = [self.dicts[id][w] if w in self.dicts[id] else 1 for w in line]
                    if self.voc_sizes[id] > 0:
                        line = [w if w < self.voc_sizes[id] else 1 for w in line]
                    _lines.append(line)

                flag3 = True
                for line in _lines:
                    if len(line) <= self.maxlen:
                        flag3 *= False

                if flag3:
                    continue

                for ie in range(self.nums):
                    datasets[ie].append(_lines[ie])
                _samples += 1

                if _samples >= self.batch_size:
                    break

        except IOError:
            self.end_of_data = True

        flag4 = False
        for ig in range(self.nums):
            if len(datasets[ig]) <= 0:
                flag4 = True

        if flag4:
            self.end_of_data = False
            self.reset()
            raise StopIteration

        return datasets
