import os
import sys
import glob
import shutil
import math
import shlex
import subprocess
from optparse import OptionParser
import speech_recognition as sr
import logging
from text_indexator import proces_txts
import schedule
import time
import datetime

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger()

INPUT_DIR_ARG = "--input-dir="
OUTPUT_DIR_ARG = "--output-dir="
CHUNK_SIZE = 60
WAV_CHUNKS_DIRECTORY = "chunks/"
TEMP_DIRECTORY = "/tmp/video_processing"


def readArguments(INPUT_DIR_ARG, OUTPUT_DIR_ARG):
    input_dir = "/input"
    output_dir = "/output"
    if(len(sys.argv) > 1):
        for i in range(1, len(sys.argv)):
            arg = sys.argv[i]
            if(arg.startswith(INPUT_DIR_ARG) == True):
                input_dir = arg[len(INPUT_DIR_ARG):]
            elif(arg.startswith(OUTPUT_DIR_ARG) == True):
                output_dir = arg[len(OUTPUT_DIR_ARG):]

    return input_dir, output_dir


def processFile(input_dir, output_dir, source_file):
    logger.debug("processFile")
    mp4_name = source_file[len(input_dir)+1:-4]
    logger.debug(mp4_name)
    output_file_dir = output_dir + "/" + mp4_name
    logger.debug("output_file_dir = " + output_file_dir)
    if os.path.isdir(output_file_dir) == False:
        os.mkdir(output_file_dir)
    convert_to_wav(source_file=source_file,
                   output_file_dir=output_file_dir, chunk_size=CHUNK_SIZE)
    wav_to_txt(output_file_dir)


def convert_to_wav(source_file, output_file_dir, chunk_size):
    logger.info('convert_to_wav source file %s output dir %s',
                source_file, output_file_dir)
    video_length = get_video_length(source_file)
    logger.debug(f'{source_file} size {video_length}')
    file_size = os.stat(source_file).st_size
    logger.debug(f'{source_file} size {file_size}')
    split_by_seconds(video_length=video_length, output_file_dir=output_file_dir,
                     split_length=chunk_size, filename=source_file)
    mp4_file_names = glob.glob(output_file_dir + "/*.mp4")
    for mp4Chunk in mp4_file_names:
        mp4ChunkName = mp4Chunk[0:-4]
        logger.info(f'{mp4Chunk} to {mp4ChunkName} mp3 y wav')
        os.system(f'ffmpeg -i {mp4Chunk} {mp4ChunkName}.mp3')
        os.system(f'ffmpeg -i {mp4ChunkName}.mp3 {mp4ChunkName}.wav')
    os.system(f'rm -f {output_file_dir}/*.mp*')


def wav_to_txt(output_file_dir):
    logger.info('wav_to_txt output dir %s', output_file_dir)
    wav_names = glob.glob(output_file_dir + "/*.wav")
    for wavFile in wav_names:
        r = sr.Recognizer()
        txt_file = wavFile[0:-4] + ".txt"
        with sr.AudioFile(wavFile) as source:
            logger.info(f'audio file {wavFile}')
           # r.adjust_for_ambient_noise(source)
            audio = r.record(source)
            transcipt = r.recognize_google(
                audio, language="es-ES", show_all=True)
            f = open(txt_file, "w")
            if len(transcipt) > 0 and len(transcipt['alternative']) > 0:
                f.write(transcipt['alternative'][0]['transcript'])
            f.close()
            print(transcipt)
    os.system(f'rm -f {output_file_dir}/*.wav')


def get_video_length(filename):
    output = subprocess.check_output(("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                      "default=noprint_wrappers=1:nokey=1", filename)).strip()
    video_length = int(float(output))
    logger.debug(f'{filename} size {video_length}S')

    return video_length


def ceildiv(a, b):
    return int(math.ceil(a / float(b)))


def split_by_seconds(filename, split_length, output_file_dir=".", input_file_dir=".", vcodec="copy", acodec="copy",
                     extra="", video_length=None, **kwargs):
    if split_length and split_length <= 0:
        logger.debug("Split length can't be 0")
        raise SystemExit

    if not video_length:
        video_length = get_video_length(filename)
    split_count = ceildiv(video_length, split_length)
    if split_count == 1:
        print("Video length is less then the target split length.")
        return

    split_cmd = ["ffmpeg", "-i", filename, "-vcodec",
                 vcodec, "-acodec", acodec] + shlex.split(extra)
    try:
        filebase = ".".join(filename.split(".")[:-1])
        fileext = filename.split(".")[-1]
    except IndexError as e:
        raise IndexError("No . in filename. Error: " + str(e))
    for n in range(0, split_count):
        split_args = []
        if n == 0:
            split_start = 0
        else:
            split_start = split_length * n
        newFile = output_file_dir + filebase[len(input_dir):]
        logger.debug(f'filebase = {filebase}')
        split_args += ["-ss", str(split_start), "-t", str(split_length),
                       newFile + "-_-" + str(n + 1) + "-_-of-" +
                       str(split_count) + "." + fileext]
        print("About to run: " + " ".join(split_cmd + split_args))
        subprocess.check_output(split_cmd + split_args)


def process_input_directory(output_dir, input_dir):
    file_names = glob.glob(input_dir + "/*.mp4")
    for mp4_source_file in file_names:
        logger.info(f'processing {input_dir}')
        processFile(input_dir, TEMP_DIRECTORY, mp4_source_file)
        proces_txts(TEMP_DIRECTORY, ".txt")
        os.system(f'rm -rf {TEMP_DIRECTORY}/**/*.txt')
        time_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.system(f'mkdir {output_dir}/{time_stamp}')
        os.system(f'mv {mp4_source_file} {output_dir}/{time_stamp}')


logger.info('processing ')
if os.path.isdir(TEMP_DIRECTORY) == False:
    os.mkdir(TEMP_DIRECTORY)

input_dir, output_dir = readArguments(
    INPUT_DIR_ARG, OUTPUT_DIR_ARG)

schedule.every(15).seconds.do(process_input_directory, output_dir, input_dir)

while True:
    schedule.run_pending()
    time.sleep(1)
