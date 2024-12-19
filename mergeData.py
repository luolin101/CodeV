import argparse
import json
def merge(file1_path,file2_path):
    with open(file1_path,'r',encoding='utf-8') as file1, open(file2_path,'r',encoding='utf-8') as file2:
        data1 = json.load(file1)
        data2 = json.load(file2)
    data1.extend(data2)
    with open("data.json",'w',encoding='utf-8') as file:
        json.dump(data1, file, ensure_ascii=False, indent=4)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script configuration")
    parser.add_argument("--file1", type=str)
    parser.add_argument("--file2", type=str)
    args = parser.parse_args()
    merge(args.file1,args.file2)