#!/usr/bin/env python3

import requests
import threading
import json
import time

import alexa_audio

class AlexaDevice:
	def __init__(self, alexa_config):
		self.alexa_audio_instance = alexa_audio.AlexaAudio(alexa_config['threshold'], self.send_audio)
		self.refresh_token = alexa_config['refresh_token']
		self.client_id = alexa_config['Client_ID']
		self.client_secret = alexa_config['Client_Secret']
		self.access_token = None
		self.access_token_time = 0

	def get_access_token(self):
		current_time = time.mktime(time.gmtime())
		if self.access_token is None or current_time - self.access_token_time > 3500:
			body = {
				'client_id': self.client_id,
				'client_secret': self.client_secret,
				'refresh_token': self.refresh_token,
				'grant_type': 'refresh_token'
				}
			r = requests.post('https://api.amazon.com/auth/o2/token', data=body)
			resp = json.loads(r.text)
			self.access_token = resp['access_token']
			self.access_token_time = current_time
		return self.access_token

	def send_audio(self):
		raw_audio = self.alexa_audio_instance.get_audio()
		if raw_audio is None:
			return
		headers = {'Authorization': 'Bearer ' + self.get_access_token()}
		metadata = {
				'messageHeader': {},
				'messageBody': {
					'profile': 'alexa-close-talk',
					'locale': 'en-us',
					'format': 'audio/L16; rate=16000; channels=1'
				}
			}
		files = [
				('metadata', (None, json.dumps(metadata).encode('utf8'), 'application/json; charset=UTF-8')),
				('audio', (None, raw_audio, 'audio/L16; rate=16000; channels=1'))
			]
		url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
		r = requests.post(url, headers=headers, files=files)
		if r.status_code != requests.codes.ok:
			print("Audio response faile with " + str(r.status_code) + " code: " + r.text)
			self.alexa_audio_instance.beep_failed()
			return
		content = r.content
		mpegpos = content.find(b'audio/mpeg')
		if mpegpos < 0:
			print("No audio found in response: " + r.text)
			self.alexa_audio_instance.beep_failed()
			return
		rawmpegpos = content.find(b'\r\n\r\n', mpegpos);
		if rawmpegpos < 0:
			print("No raw audio data found: " + r.text)
			self.alexa_audio_instance.beep_failed()
			return
		data = content[rawmpegpos + 4:]
		print("Alexa got response")
		self.alexa_audio_instance.play_mp3(data)

	def close(self):
		self.alexa_audio_instance.close()
