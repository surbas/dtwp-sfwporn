import argparse
import ctypes
import datetime
import json
import tempfile
import os
import re
import urllib
import urllib2
import _winreg as winreg

#Consts
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 1
SPIF_SENDCHANGE = 2

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
        print 'Failed to reach the server.'
        print 'Reason: ', e.reason
    except HTTPError as e:
        print "The server was unable to fulfill the request."
        print 'Error code: ', e.code
    else:
        return response.read()


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
    
def _parse_args():

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-s', action='store', default='EarthPorn', type=str,
                        dest='subreddit',
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
                        
                        
                        
    return parser.parse_args()
    
    
def main(subreddit, time_frame, style, user_agent, min_resolution=None):
    
    
    #Be nice and set user-agent to something unique per:
    #https://github.com/reddit/reddit/wiki/API
    headers = {
        'User-Agent': user_agent
    }

    url_tempate = 'http://www.reddit.com/r/{}/top.json'
    get_params = {'t' : time_frame,
              'limit' : '10'}
              
    reddit_page = get_page(url_tempate.format(subreddit), headers, get_params)
        
    j = json.loads(reddit_page)
    
    #only support jpegs for now
    ppimgs = [(i['data']['url'], i['data']['title']) 
               for i in j['data']['children'] if i['data']['url'].endswith('.jpg')]
    
    #Parse the resolution from the title
    if min_resolution is not None:
        imgs = []
        r = re.compile(".*\[\s*(\d+)\s*[xX\*\xd7\-]?\s*(\d+)\s*\].*", re.UNICODE)
        for url, n in ppimgs:
            m = r.match(n)
            if m is not None:
                res_of_image = m.groups()
                print res_of_image
                if int(res_of_image[0]) >= min_resolution[0] and int(res_of_image[1]) >= min_resolution[1]:
                    imgs.append((url, n))
                else:
                    print "Too low:", res_of_image
            else:
                print "Warning failed to parse resolution: ", url, n
    else:
        imgs = ppimgs
        
    #Get best image for period
    if len(imgs):
        image = get_page(imgs[0][0], headers)
        
        #temp file
        td = tempfile.gettempdir()
        tf = os.path.join(td, 'dtwp-sfwporn.jpg')
        with open(tf, 'wb') as img_file:
            img_file.write(image)

        set_wallpaper(tf, style)

    else:
        print 'No acceptable images found @ %s within the time frame "%s."' % (subreddit, time_frame)



if __name__ == '__main__':
    args = _parse_args()
    main(**vars(args))