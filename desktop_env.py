from __future__ import division

import logging
import sys
import ctypes
import _winreg as winreg 

logger = logging.getLogger(__name__)


class DesktopEnvironment(object):

    def __init__(self):
        self._ar = None
    
    @staticmethod
    def determin_desktop_env():
        if sys.platform == 'win32':
            return 'win32'
        else:
            return 'unknown'

    @staticmethod
    def get_current_desktop_env():
        dt_env = DesktopEnvironment.determin_desktop_env()
        
        if dt_env == 'win32':
            return WindowsDesktopEnviroment()
        
        
    def get_desktop_size(self):
        raise NotImplementedError('Please get a supported DesktopEnviroment class by calling get_current_desktop_env()')
        
    def get_desktop_aspect_ratio(self):
        raise NotImplementedError('Please get a supported DesktopEnviroment class by calling get_current_desktop_env()')
        
    def set_wallpaper(self, file_path, style):
        #going to want to translate styles to common name.
        return self._set_wallpaper(file_path, style)
        
        
class WindowsDesktopEnviroment(DesktopEnvironment):
    #Consts
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 1
    SPIF_SENDCHANGE = 2

    SM_CXSCREEN = 0
    SM_CYSCREEN = 1
    
    def __init__(self):
        return super(WindowsDesktopEnviroment, self).__init__()
    
    def get_desktop_size(self):
        return ctypes.windll.user32.GetSystemMetrics(self.SM_CXSCREEN), ctypes.windll.user32.GetSystemMetrics(self.SM_CYSCREEN)
        
    def get_desktop_aspect_ratio(self):
        if self._ar is None:
            size = self.get_desktop_size()
            self._ar = size[0]/size[1]
        
        return self._ar
       
    def _set_wallpaper(self, file_path, style):
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
        rtn = ctypes.windll.user32.SystemParametersInfoA(self.SPI_SETDESKWALLPAPER, 0, file_path,
                                                    self.SPIF_UPDATEINIFILE + self.SPIF_SENDCHANGE)
                                                    
        if not rtn:
            logger.debug("GetLastError: %s", ctypes.GetLastError()) 
            raise ctypes.WinError()
        logger.debug("rtn: %s", rtn)