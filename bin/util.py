import os
import sys
import json


aws_cache = os.environ['HOME'] + "/.aws-cache"


def get_config():
    if not os.path.exists(f"{aws_cache}/config.txt") or ("--reset_cache" in sys.argv):
        os.system(f"mkdir -p {aws_cache}")
        my_dict = {}
        my_dict.update({'region': input("What AWS region to use?\n")})
        my_dict.update({'username': input("Composer will attempt to create an AWS s3 bucket to store your data in."
                                          " Provide an identifying username: ")})
        f = open(f"{aws_cache}/config.txt", 'w')
        f.write(json.dumps(my_dict))
        f.close()

    with open(f"{aws_cache}/config.txt") as f:
        d = json.load(f)
        return d


def append_to_file(dst, src):
    if not os.path.exists(dst) or not os.path.exists(src):
        print("Weak warning: No constraints found. Not appending")
        return
    a = open(dst, "a")
    with open(src, 'r') as f:
        for ln in f.readlines():
            a.write(ln)
