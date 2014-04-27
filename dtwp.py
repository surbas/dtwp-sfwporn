import argparse
import ctypes
import datetime
import json
import logging
import logging.handlers
import os
import pprint
import re
import tempfile
import time
import urllib
import urllib2
import urlparse
import _winreg as winreg

logger = logging.getLogger(__name__)

#Consts
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 1
SPIF_SENDCHANGE = 2

SM_CXSCREEN = 0
SM_CYSCREEN = 1

def get_page(url, headers, get_params=None):

    if get_params is not None:
        data = urllib.urlencode(get_params)
        rurl = '{}?{}'.format(url, data)
    else:
        rurl = url
    
    req = urllib2.Request(rurl, None, headers)
    
    try:
        response = urllib2.urlopen(req)
    except URLError as e:
        logger.exception('Failed to reach the server.')
        logger.error('Reason: %s', e.reason)
    except HTTPError as e:
        logger.exception("The server was unable to fulfill the request.")
        logger.error('Error code: ', e.code)
    else:
        return response.read()

        
def get_desktop_size():
    return ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN), ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)
       
def set_wallpaper(file_path, style):
    """Modeled on http://code.msdn.microsoft.com/windowsdesktop/CSSetDesktopWallpaper-2107409c/sourcecode?fileId=21700&pathId=734742078"""
    
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

    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Control Panel\Desktop', 0, winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(k, 'TileWallpaper', 0, winreg.REG_SZ, tw)
    winreg.SetValueEx(k, 'WallpaperStyle', 0, winreg.REG_SZ, wps)
    winreg.CloseKey(k)
    
    #see http://msdn.microsoft.com/en-us/library/windows/desktop/ms724947%28v=vs.85%29.aspx
    rtn = ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, file_path,
                                                SPIF_UPDATEINIFILE + SPIF_SENDCHANGE)
                                                
    if not rtn:
        logger.debug("GetLastError: %s", ctypes.GetLastError()) 
        raise ctypes.WinError()
    logger.debug("rtn: %s", rtn)
    
def _parse_args():

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-s', action='store', default=['EarthPorn', 'SpacePorn'], type=str,
                        dest='subreddits',
                        nargs='+',
                        help='Subreddit to get images from.')

    parser.add_argument('-t', action='store', default='day', 
                        choices=['hour', 'day', 'week', 'month', 'year', 'all'], 
                        type=str,
                        dest='time_frame', 
                        help='Select the top scoring image over this time frame')

    parser.add_argument('-y', action='store', default='fit', 
                        choices=['center', 'tile', 'stretch', 'fill', 'fit'], 
                        type=str,
                        dest='style', help='The way the wallpaper should be displayed on desktop')
                        
    parser.add_argument('-ua', action='store', default='dtwp-sfwporn/0.2 by sarkybogmozg', 
                        type=str,
                        dest='user_agent', help='User-Agent to present when retriving links and images.')

    parser.add_argument('-r', action='store', default=None, 
                        type=int,
                        nargs=2,
                        dest='min_resolution', help='The minimum resolution to accept')
                        
    parser.add_argument('-a', action='store', default=None, const=-1,
                        type=float,
                        nargs='?',
                        dest='aspect_ratio', 
                        help="""Limits the image selected to an aspect ratio. If no argument follows, or if it is -1 
                                then it uses the current desktop's aspect ratio. \n\r
                                The tolerance (default 0) of the equality check can be set using "-o" followed by a float"""
                        )

    parser.add_argument('-o', action='store', default=0, const=0,
                        type=float,
                        nargs='?',
                        dest='aspect_ratio_tolerance', 
                        help="""Only used when is present -a is set". Sets the tolerance allowed when comparing the 
                        aspect ratio of the image to the aspect ratio specified by "-a" """
                        )
                        
    return parser.parse_args()
    
def setup_logging(log_file_dir, log_file_name, level=None):
    logger = logging.getLogger()
    
    if level is None:
        logger.setLevel(logging.WARN)
    else:
        logger.setLevel(level)

    try:
        os.makedirs(log_file_dir)
    except WindowsError:
        pass

    lp = os.path.splitext(log_file_name)
    dtlp = os.path.join(log_file_dir, "{}_T{:%Y%m%d_%H%M%S}{}".format(lp[0], datetime.datetime.now(), lp[1]))

    do_roll = os.path.isfile(dtlp)

    rfh = logging.handlers.RotatingFileHandler(dtlp, mode='a', maxBytes=1024*1024*5, backupCount=8)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(funcName)s: %(message)s")
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    if do_roll:
        rfh.doRollover()

    ch = logging.StreamHandler()
    formatter2 = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(funcName)s: %(message)s")
    ch.setFormatter(formatter2)
    logger.addHandler(ch)
    
    
def main(subreddits, time_frame, style, user_agent, min_resolution, aspect_ratio, aspect_ratio_tolerance):


    logger.info('Hello')
    
    #Be nice and set user-agent to something unique per:
    #https://github.com/reddit/reddit/wiki/API
    headers = {
        'User-Agent': user_agent
    }
    
    

    url_tempate = 'http://www.reddit.com/r/{}/top.json'
    get_params = {'t' : time_frame,
              'limit' : '5'}
    listings = []
    
    imgur_api_tempate = 'https://api.imgur.com/2/image/{}'
    imgur_type_re = re.compile(r'<type>(.+)</type>')
    imgur_orginal_re = re.compile(r'<original>(.+)</original>')
    
    
    for s in subreddits:
        reddit_page = get_page(url_tempate.format(s), headers, get_params)
        
        j = json.loads(reddit_page)
        
        #Only support jpegs for now.
        for i in j['data']['children']:
            l = i['data']
            url_parts = urlparse.urlsplit(l['url'])
            if url_parts.path.endswith('jpg'):
                l['good_url'] = l['url']
            elif url_parts.netloc == 'imgur.com' and '.' not in url_parts.path:
                logger.debug("Have to ask imgur %s", url_parts)
                id = url_parts.path.split('/')[-1]
                imgur_xml = get_page(imgur_api_tempate.format(id), headers)
                m = imgur_type_re.search(imgur_xml)
                if m is not None and m.groups()[0] == 'image/jpeg':
                    m = imgur_orginal_re.search(imgur_xml)
                    
                    if m is not None:
                        logger.debug("Good URL! imgur %s", m.groups()[0])
                        l['good_url'] =  m.groups()[0]
                    else:
                        logger.debug("No original? %s", imgur_xml)
                        
                else:
                    logger.debug("Not a jpg? imgur %s", imgur_xml)
            else:
                logger.debug("Not a jpg or not imgur.com %s", url_parts)
                continue
            
            listings.append(l)

        #play by the rules
        time.sleep(2)

    listings.sort(key=lambda i: i['score'], reverse=True)
    logger.debug('listings: %s', pprint.pformat([(l['score'], l['title'], l['good_url']) for l in listings]))
    logger.debug('Len %s', len(listings))
    
    #Parse the resolution from the title
    if min_resolution is not None:
        imgs = []
        r = re.compile(".*\[\s*(\d+)\s*[xX\*\xd7\-]?\s*(\d+)\s*\].*", re.UNICODE)
        for i in listings:
            m = r.match(i['title'])
            if m is not None:
                res_of_image = m.groups()
                logger.debug('res_of_image:', res_of_image)
                if int(res_of_image[0]) >= min_resolution[0] and int(res_of_image[1]) >= min_resolution[1]:
                    imgs.append(i)
                else:
                    logger.debug("Resolution is too low")
            else:
                logger.warn("Failed to parse resolution: %s", i)
    else:
        imgs = listings
        
    #Get highest scoring image for period
    if len(imgs):
        image = get_page(imgs[0]['good_url'], headers)
        
        #Logging
        td = tempfile.gettempdir()
        
        #temp file
        tf = os.path.join(td, 'dtwp-sfwporn.jpg')
        with open(tf, 'wb') as img_file:
            img_file.write(image)

        set_wallpaper(tf, style)

    else:
        logger.warn('No acceptable images found %s within the time frame "%s."', subreddit, time_frame)
        
    logger.info('Fin')



if __name__ == '__main__':
    setup_logging('logs', 'dtwp-sfwporn.log', logging.DEBUG)
    args = _parse_args()
    logger.debug(args)
    main(**vars(args))