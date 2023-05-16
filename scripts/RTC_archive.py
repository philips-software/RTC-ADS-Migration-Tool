import CONFIG
import UTILS
import sys 
from csv import reader
import csv
import logging
import time
import json
import glob
import os
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate
from azure.devops.v5_1.work_item_tracking.models import Wiql
import CREDENTIALS

# Initialize RTC client connection
try:
    rtc_client, rtc_query_client = UTILS.init_rtc_connection()
except Exception as err:
    UTILS.print_and_log("Error logging into Azure, check your credentials inside CONFIG.py: "+str(err),error=True)
    sys.exit(1)

# Initialize ADS client connection
try:
    ads_core_client, ads_wit_client, ads_wit_5_1_client, ads_project = UTILS.init_ads_connection()
except Exception as err:
    UTILS.print_and_log("Error logging into RTC, check your credentials inside CONFIG.py: "+str(err),error=True)
    sys.exit(1)

# Init logging/work_items/json_maps dirs, and create log file
UTILS.init_log_file(CONFIG.logging_filepath +'\\'+CONFIG.logging_filename)  
UTILS.init_dir(CONFIG.work_item_filepath, delete=False)
UTILS.init_dir(CONFIG.json_maps_filepath, delete=False)

print("begin archive")

###############################
#
# For each work item, get attachments, comments, parent/child links
#
###############################
# Migrate each work item in csv 
if CONFIG.rtc_archive is True:
    try:
        # open csv file 
        csv_row_count=0
        created_ads_item_count=0
        skip=True
        with open(CONFIG.rtc_archive_csv_input, 'r', encoding='utf-16') as read_obj:
            # pass the file object to reader() to get the reader object
            csv_reader = reader(read_obj, delimiter='\t')
            # Iterate over each row in the csv using reader object
            csv_cols = None
            for row in csv_reader:
                # row variable is a list that represents a row in csv
                if csv_cols is None:
                    csv_cols = row 
                    UTILS.print_and_log('csv_cols=',csv_cols)
                    continue 
                else:
                    UTILS.print_and_log('\n___found '+str(len(row))+" items ___")
                    UTILS.print_and_log(row)
                    # get rtc row common info
                    rtc_id = row[csv_cols.index("Id")]
                    rtc_type = row[csv_cols.index("Type")]
                    
                    UTILS.print_and_log("rtc_id="+str(rtc_id))

                    skip=False
                    if skip is not True:

                        filed_against = str(row[csv_cols.index("Filed Against")])
                        team=filed_against.rsplit('/', 1)[1]
                        # query rtc for work item info
                        myquerystr = 'dc:id="'+str(rtc_id)+'"'
                        returned_prop = "rtc_cm:modifiedBy,rtc_cm:ownedBy,dc:subject,rtc_cm:plannedFor,rtc_cm:filedAgainst,dc:created,dc:creator,dc:type"
                        queried_wis = rtc_query_client.queryWorkitems(query_str=myquerystr, projectarea_name=CREDENTIALS.RTC_projectarea_name, returned_properties=returned_prop)
                        rtc_workitem = queried_wis[0]   
                        # get attachments
                        attachments = rtc_workitem.getAttachments()
                        work_item_location = CONFIG.work_item_filepath +'\\'+ team + '\\' + rtc_type + '\\' + str(rtc_id)
                        work_item_location=work_item_location.replace(' ', '_')

                        if attachments is not None:
                            os.makedirs(work_item_location)
                            UTILS.print_and_log(str(len(attachments))+" attachments found ")
                            for i in attachments:
                                UTILS.print_and_log("downloading attachment "+str(i))
                                if '\\' in i.description:
                                    filename=(i.description)[(i.description).rindex("\\")+1:]
                                else:
                                    filename=i.description

                                filepath = work_item_location +'\\'+ filename
                                UTILS.print_and_log("Saving attachment: "+str(filepath))
                                try:
                                    UTILS.download_rtc_attachment(
                                        i.url,
                                        rtc_client,
                                        filepath
                                    )
                                except Exception as e:
                                    UTILS.print_and_log("Error downloading attachment: "+str(e)+'\n')
                                    logging.error("Error downloading attachment: "+str(e)+'\n')
                      


    except Exception as err:
        UTILS.print_and_log(str(err),error=True)