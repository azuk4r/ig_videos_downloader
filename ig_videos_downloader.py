from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome, ChromeOptions
from os import makedirs, remove, rmdir, listdir
from selenium.webdriver.common.by import By
from ffmpeg import input, probe, output
from os.path import join, exists
from datetime import datetime
from json import load, loads
from time import sleep

def load_cookies(driver, cookies_file):
	with open(cookies_file,'r')as file:
		cookies=load(file)
	for cookie in cookies:
		if 'sameSite'in cookie and cookie['sameSite']not in['Strict','Lax','None']:
			del cookie['sameSite']
		driver.add_cookie(cookie)

def login(post_url):
	options=ChromeOptions()
	options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
	options.add_experimental_option('excludeSwitches',['enable-automation'])
	options.add_experimental_option('useAutomationExtension',False)
	options.add_argument('--disable-cache')
	options.set_capability('goog:loggingPrefs',{'performance':'ALL'})
	driver=Chrome(service=Service(ChromeDriverManager().install()),options=options)
	driver.get('https://www.instagram.com')
	sleep(5)
	load_cookies(driver,'cookies.json')
	driver.get(post_url)
	sleep(5)
	return driver

def get_video_description(driver):
	try:
		description_element = driver.find_element(By.XPATH, "//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli')]")
		description = description_element.text
		return description
	except Exception:
		return 'output_name'

def scraper(post_url):
	driver=login(post_url)
	output_name=get_video_description(driver)
	current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	output_name = f'{output_name}_{current_time}'
	logs=driver.get_log('performance')
	mp4_urls=[]
	for log in logs:
		message=loads(log['message'])['message']
		if 'Network.responseReceived'in message['method']:
			if 'response'in message['params']:
				response=message['params']['response']
				if 'url'in response:
					url=response['url']
					if '.mp4'in url:
						mp4_urls.append(url)
	return mp4_urls, output_name

def clean_url(url):
	if '?'in url:
		base_url,params=url.split('?',1)
		params='&'.join([p for p in params.split('&')if not p.startswith('bytestart')and not p.startswith('byteend')])
		return f'{base_url}?{params}'
	return url

def download_temp(url,output_file):
	referer='https://www.instagram.com/'
	stream=input(url,headers=f'Referer: {referer}')
	output_path=join('temp',output_file)
	output(stream,output_path,vcodec='copy',acodec='copy').run(overwrite_output=True)
	return output_path

def is_audio_or_video(file_path):
	info=probe(file_path)
	for stream in info['streams']:
		if stream['codec_type']=='video':
			return 'video'
		elif stream['codec_type']=='audio':
			return 'audio'
	return None

def download_and_merge(mp4_urls, output_name):
	if not exists('temp'):
		makedirs('temp')
	index=-2
	while True:
		audio_url=clean_url(mp4_urls[index])
		video_url=clean_url(mp4_urls[index+1])
		audio_file=download_temp(audio_url,'audio_temp.mp4')
		video_file=download_temp(video_url,'video_temp.mp4')
		audio_type=is_audio_or_video(audio_file)
		video_type=is_audio_or_video(video_file)
		if audio_type=='audio'and video_type=='video':
			break
		elif audio_type=='audio'and video_type=='audio':
			remove(audio_file)
			index-=1
		elif audio_type=='video'and video_type=='video':
			remove(video_file)
			index-=1
	output_file=f'{output_name}.mp4'
	final_path=join('results',output_file)
	output(input(video_file),input(audio_file),final_path,vcodec='copy',acodec='aac',strict='experimental').run()

def cleanup_temp():
	for file in listdir('temp'):
		remove(join('temp',file))
	rmdir('temp')

if __name__=='__main__':
	if not exists('results'):
		makedirs('results')
	mp4_urls, output_name=scraper('IG VIDEO URL HERE') # ensure to edit this and cookies.json file
	download_and_merge(mp4_urls, output_name)
	cleanup_temp()