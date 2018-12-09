import os
import datetime
import re
import csv
import pandas as pd
import numpy as np
from ruuvitag_sensor.ruuvi import RuuviTagSensor

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
DATA_PATH = os.path.join(STATIC_DIR, 'data.csv')
TAGS = {
  "FB:B7:8B:F3:32:53": {
        "name": "A: Camera da letto",
        "temp_offset": -0.065709},
  "F0:C9:25:26:3B:12": {
      "name": "B: Salotto",
      "temp_offset":  0.065785 },
  "FC:52:08:88:81:E1": {
      "name": "C: Balcone",
      "temp_offset": -0.000077}
}

COL_TAG_NAME = "tag_name"
COL_TAG_MAC = "mac"
COL_TEMP = "temp"
COL_HUMIDITY = "humidity"
COL_TIME = "time"

_FONTS_DIR = "/home/pi/Desktop/orsoserver/fonts/"
_font = ImageFont.truetype(os.path.join(_FONTS_DIR, 'Roboto-Regular.ttf'), size=100)

def read_tags():
  raw_tag_datas = RuuviTagSensor.get_data_for_sensors(TAGS.keys(), 5)
  tag_datas = []
  for mac, raw_tag_data in raw_tag_datas.items():
    tag = TAGS.get(mac)
    if not tag:
      continue
    tag_datas.append({
        COL_TAG_MAC: mac,
        COL_TEMP: raw_tag_data.get("temperature"),
        COL_HUMIDITY: raw_tag_data.get("humidity")})
  return tag_datas

def photo_relpath(time_str):
  return 'photo_%s.jpg' % time_str

def capture_photo(path):
  os.system('raspistill -n -q 10 -vf -hf -o %s' % path)

def label_photo(input_path, text, output_path):
  img = Image.open(input_path)
  draw = ImageDraw.Draw(img)
  draw.text((50, 30), text, (255, 255, 255), font=_font)
  img.save(output_path)

def make_video(glob, output_path):
  #ffmpeg -y -r 20 -pattern_type glob -i 'static/mod*.jpg' -c:v libx264  -pix_fmt yuv420p -s 800x600 -b:v 1M -bufsize 1M static/video2.mp4
  dirname, basename = os.path.split(output_path)
  tmp_path = os.path.join(dirname, 'tmp_' + basename)
  os.system(("ffmpeg -y -r 20 -pattern_type glob -i '{}' -c:v libx264 "
             "-pix_fmt yuv420p -s 800x600 -b:v 1M -bufsize 1M {}; "
             " mv -f {} {}").format(glob, tmp_path, tmp_path, output_path))

def read_data():
  try:
    with open(DATA_PATH) as csvfile:
      reader = csv.DictReader(csvfile)
      data = list(reader)
      if data:
        return reader.fieldnames, data
  except:
    pass
  return [], []

def read_dataframe():
  _, data = read_data()
  if not data:
    return None
  df = pd.DataFrame.from_records(data)
  df['datetime'] = [str_to_datetime(s) for s in df[COL_TIME]]
  df[COL_TEMP] = np.array(df[COL_TEMP], dtype=float)
  df[COL_HUMIDITY] = np.array(df[COL_HUMIDITY], dtype=float)
  df[COL_TAG_NAME] = "unknown tag"
  for mac, tag in TAGS.items():
    rows = df[COL_TAG_MAC] == mac
    if 'temp_offset' in tag:
      df.loc[rows, COL_TEMP] -= tag['temp_offset']
    if 'name' in tag:
      df.loc[rows, COL_TAG_NAME] = tag['name']
  return df

def add_to_data(rows):
  fields, data = read_data()
  for d in rows:
    for key in d.keys():
      if key not in fields:
        fields.append(key)
  with open(DATA_PATH, 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()
    for d in data:
      writer.writerow(d)
    for d in rows:
      writer.writerow(d)

def datetime_to_str(dt):
  return '%04d_%02d_%02d_%02d_%02d_%02d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def str_to_datetime(time_str):
  return datetime.datetime(*[int(tok) for tok in time_str.split('_')])

def run():
  dt = datetime.datetime.now()
  time_str = datetime_to_str(dt)
  tag_datas = read_tags()
  photo = photo_relpath(time_str)
  photo_path = os.path.join(STATIC_DIR, photo)
  capture_photo(photo_path)
  mod_photo_path = os.path.join(STATIC_DIR, 'mod_' + photo)
  label_photo(photo_path, dt.strftime("%Y-%m-%d %H:%M:%S"), mod_photo_path)
  make_video(os.path.join(STATIC_DIR, 'mod*.jpg'), os.path.join(STATIC_DIR,
                                                                'video.mp4'))
  for data in tag_datas:
    data[COL_TIME] = time_str
  add_to_data(tag_datas)

if __name__ == '__main__':
  run()
