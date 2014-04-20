import _winreg as winreg
import urllib
import urllib2
import json
import ctypes
import tempfile
import datetime


#Consts
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 1
SPIF_SENDCHANGE = 2

def get_page(url, get_params=None):

	#Be nice and set user-agent to something unique per:
	#https://github.com/reddit/reddit/wiki/API
	headers = {
		'User-Agent': 'desktopit/0.1 by sarkybogmozg',
	}
	
	if get_params is not None:
		data = urllib.urlencode(get_params)
		rurl = '{}?{}'.format(url, data)
	else:
		rurl = url
	
	req = urllib2.Request(rurl, None, headers)
	
	try:
		response = urllib2.urlopen(req)
	except URLError as e:
		print 'Failed to reach a server.'
		print 'Reason: ', e.reason
	except HTTPError as e:
		print "The server was unable to fulfill the request."
		print 'Error code: ', e.code
	else:
		return response.read()


def set_wallpaper(file_path, style):
	"""Modaled on http://code.msdn.microsoft.com/windowsdesktop/CSSetDesktopWallpaper-2107409c/sourcecode?fileId=21700&pathId=734742078"""
	
	if style == 'center':
		tw = '0'
		wps = '0'
	elif style == 'tile':
		tw = '1'
		wps = '0'
	elif style == 'stretch':
		tw = '0'
		wps = '2'
	elif style == 'fill':
		tw = '0'
		wps = '6'
	elif style == 'fit':
		tw = '0'
		wps = '10'
	else:
		raise ArgumentError('{} is not supported!'.format(style))

	k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Control Panel\Desktop', 0, _winreg.KEY_ALL_ACCESS)
	winreg.SetValueEx(k, 'TileWallpaper', 0, _winreg.REG_SZ, tw)
	winreg.SetValueEx(k, 'WallpaperStyle', 0, _winreg.REG_SZ, wps)
	k.close()
	
	#see http://msdn.microsoft.com/en-us/library/windows/desktop/ms724947%28v=vs.85%29.aspx
	ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, r"C:\Users\Shon\Desktop\desktopit0jnxokq.jpg" , SPIF_UPDATEINIFILE + SPIF_SENDCHANGE)
	

def main():
	subreddit = 'EarthPorn'
	time_frame = 'daily'
	style = 'fill'

	url_tempate = 'http://www.reddit.com/r/{}/top.json'
	get_params = {'t' : time_frame,
			  'limit' : '10'}
			  
	reddit_page = get_page(url_tempate.format(subreddit), get_params)
		
	j = json.loads(reddit_page)
	
	#only support jpegs for now
	img_urls = [i['data']['url'] for i in j['data']['children'] if i['data']['url'].endswith('.jpg')]
	
	#Get best image for period
	image = get_page(img_urls[0])

	#temp directory
	td = tempfile.gettempdir()
	tf = os.path.join(td, 'desktopbg-{:%Y%d%m_%h%m%s}.jpg'.format(datetime.now()))
	set_wallpaper(tf, style)
	
	


