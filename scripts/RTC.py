from rtcclient.utils import setup_basic_logging
from rtcclient import RTCClient
import CONFIG
import CREDENTIALS

url = CREDENTIALS.RTC_URL
username = CREDENTIALS.RTC_USERNAME
password = CREDENTIALS.RTC_PASSWORD

rtcclient = RTCClient(url, username, password, ends_with_jazz=CONFIG.ends_with_jazz)

ISD_Project_Area = rtcclient.getProjectArea(projectarea_name=CREDENTIALS.RTC_projectarea_name)

print('RTC LOGIN COMPLETE')