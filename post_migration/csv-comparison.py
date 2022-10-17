rtc_csv_file="csv_migration\\all_frups_8.24.2022.csv"
# save ADS csv file, open in notepad++, change encoding to UTF-16 LE, and save
ads_csv_file="csv_migration\\ADS migrated frups 8.26.2022.csv" 
json_maps_location="json_maps\\"

from csv import reader
import csv

# read in csv, convert to map organized by 'id' as index root parent value
def read_csv_as_map(csv_filename, id_format, encodingVar, delimiterVar):
    print('filename: '+csv_filename+', id_format: '+id_format+', encoding: '+encodingVar+', delimiterVar: '+delimiterVar)
    
    dict={}
    dict['filename']=csv_filename
    dict['rows']={}
    try:
        with open(csv_filename, 'r', encoding=encodingVar) as read_obj:
            csv_reader = reader(read_obj, delimiter=delimiterVar)
            csv_cols = None
            col_nums = 0
            for row in csv_reader:
                if csv_cols is None:
                    csv_cols = row 
                    #print('___found '+str(len(csv_cols))+" col headers ___")
                    col_nums=len(csv_cols)
                else:
                    #print('___found '+str(len(row))+" col values ___")
                    if len(row) != col_nums:
                        print('not matching')
                    else:
                        # for each col 
                        for col_name in csv_cols:
                            print("col_name="+str(col_name))
                            col_value = row[csv_cols.index(str(col_name))]
                            print("col_value="+str(col_value))
                        '''    
                        row_id_val = row[csv_cols.index(str(id_format))]
                        if dict['rows'].get(row_id_val) is None:
                            dict['rows'][row_id_val] = row
                        else:
                            print('duplicate id found')
                        '''

        return dict
    except Exception as e:
        print('err=',e)
        return {}

# read both ADS and RTC csv files and convert to dicts
rtc_dict = read_csv_as_map(csv_filename=rtc_csv_file, id_format='Id', encodingVar='utf-16', delimiterVar='\t')
ads_dict = read_csv_as_map(csv_filename=ads_csv_file, id_format='ID', encodingVar='utf-16', delimiterVar=',')

# for each item in rtc_dict['rows']
for rtc_id in rtc_dict['rows']:
    rtc_data=rtc_dict['rows'][rtc_id]
    print(str(rtc_id))

'''
# for each row in rtc_csv_file
with open(rtc_csv_file, 'r', encoding='utf-16') as read_obj:
    csv_reader = reader(read_obj, delimiter='\t')
    csv_cols = None
    rtc_csv_line=1
    for row in csv_reader:
        if csv_cols is None:
            csv_cols = row 
            print('csv_cols=',csv_cols)
        else:
            print('___found '+str(len(row))+" items ___")
            #print(row)
            # get rtc row common info
            rtc_id = row[csv_cols.index("Id")]
            rtc_type = row[csv_cols.index("Type")]
            print("looking at rtc csv row: "+str(rtc_csv_line)+", id="+str(rtc_id)+', type='+str(rtc_type))
            # for each col, get rtc col display name and rtc col value
            # find corresponding row inside ads_csv_file


            rtc_csv_line+=1
            print('________')
'''
