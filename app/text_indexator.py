import logging
import os
import redis
import re
import json

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PASS = os.environ.get('REDIS_PASS')
REDIS_PORT = os.environ.get('REDIS_PORT')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def proces_txts(directory, extension, ignored_strings=[], regex_part=r".*/(?P<src_name>.+)-_-(?P<part>\d+)-_-of.*", part_size=60):
    logger.info(f'processing text files inside {directory}')
    extension = extension.lower()
    for dirpath, dirnames, files in os.walk(directory):
        for name in files:
            if extension and name.lower().endswith(extension):
                process_txt_file(os.path.join(dirpath, name),
                                 ignored_strings, regex_part, part_size)


def process_txt_file(file_name, ignored_strings, regex_part, part_size):
    logger.info(f'processing file {file_name}')
    re_pattern = re.compile(regex_part)
    re_match = re_pattern.match(file_name)
    part = re_match.group('part')
    original_file = re_match.group('src_name')
    t0 = (int(part) - 1) * part_size
    tf = int(part) * part_size
    file_key = original_file + "--" + str(t0) + "_" + str(tf)

    if not keyExists(file_key):
        words = collectWords(file_name, ignored_strings, original_file, t0, tf)
        persistWords(words)
        get_connection().set(file_key, 1)


def keyExists(key):
    r = get_connection()
    return None != r.get(key)


def persistWords(words):
    r = get_connection()
    for word in words:
        saved = r.get(word)
        toSave = [words[word]]
        if saved != None:
            savedDict = json.loads(saved)
            savedDict.append(words[word])
            toSave = savedDict
        r.set(word, json.dumps(toSave))


def collectWords(file_name, ignored_strings, original_file, t0, tf):
    words = {}
    with open(file_name, "r") as file:
        for line in file:
            for word in line.split():
                word = re.sub("\W", "", word)
                if word not in ignored_strings and len(word) > 2:
                    if word in words:
                        words[word]["n"] += 1
                    else:
                        words[word] = {
                            "n": 1,
                            "file_name": original_file,
                            "t0": t0,
                            "tf": tf
                        }

    return words


def get_connection():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASS
    )
