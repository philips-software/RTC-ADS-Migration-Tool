from rtcclient.utils import setup_basic_logging
from rtcclient import RTCClient
import CONFIG

url = CONFIG.RTC_URL
username = CONFIG.RTC_USERNAME
password = CONFIG.RTC_PASSWORD

rtcclient = RTCClient(url, username, password, ends_with_jazz=CONFIG.ends_with_jazz)

ISD_Project_Area = rtcclient.getProjectArea(projectarea_name=CONFIG.RTC_projectarea_name)

print('RTC LOGIN COMPLETE')