import numpy as np


def write_data(log_dir, data, filename, head=False, extension=".csv", list_2D=False):
    f = open("%s%s" % (log_dir, filename) + extension, "a+")  # file_name.csv 파일 뒤에 이어쓰기. 없으면 만들기
    if head:
        f.write("%s\n" % head)
    if type(data) == list:
        f = write_list_data(f, data, list_2D)
    elif type(data) == dict:
        f = write_dict_data(f, data)
    else:
        print("Can't write data")
    f.close()


def write_list_data(f, data, list_2D=False):
    if list_2D:
        for i in range(len(data)):
            for j in range(len(data[i])):
                f.write("%s," % data[i][j])
            f.write("\n")
    else:
        f = np.array(f)
        dims = len(f.shape)
        index_list = []
        write_content(f, data, dims, index_list)
    return f


def write_content(f, data, dims, index_list):
    dims -= 1
    for dim in range(len(data)):
        index_list.append(dim)
        if dims == 0:
            for index in index_list:
                f.write("%d, " % index)
            f.write("%s," % str(data[dim]))
            f.write("\n")
        else:
            write_content(f, data[dim], dims, index_list)
        del (index_list[-1])


def write_dict_data(f, data):
    for i in data.keys():
        f.write("%s, %s\n" % (i, data[i]))
    return f
