# Add RTC/ADS Credentials inside 'CREDENTIALS.py'

# Default Azure DevOps Tags (separated by ';' character)
tags = 'migration-tag-10.14-2'

# used tags:
# 'migration-tag-10.12-1'

###################################
# Migration options
# Note: you can only migrate children of children if migrate_children=True (cant have migrate_children_of_children=True and migrate_children=False)
###################################
migrate_parent = True 
migrate_children = True 
migrate_children_of_children = True 

###################################
# Local folder names
###################################
# local filepath var for saving work item attachments
work_item_filepath='work_items'
# local filepathvar for saving log files / json data
logging_filepath='logs'
logging_filename='migration.log'
# local filepath for saving work item json map data
json_maps_filepath='json_maps'

###################################
#  RTC->ADS Work Item Type Map
#  By default, work item will map to itself (ex: feature:feature, epic:epic)
#  All Work Item Types are formatted as all lowercase with no spaces
###################################
rtc_ads_type_map={
    'technicalspikestory':'story',
    'sitstory':'story',
    'defectstory':'story',
    'enhancementstory':'story',
    'specificationstory':'story',
    "assessmentstory":"story",
    "aststory":"story",
    "itpstory":"story",

    "specificationtask":'task'
}

###################################
# Input Method (only one can be true at a time)
###################################
csv_input = False 
csv_filepath = "csv_input\\frups ex.csv"
rtc_query_url_input = True 

###################################
# RTC Query URL Input
###################################
rtc_query_urls = {
    
    'epic':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_MrfzQEpiEe2fXugFmTmyJA'],
    'feature':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_UG4mwEpiEe2fXugFmTmyJA'],
    'story':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_f5aZoEpiEe2fXugFmTmyJA'],
    'aststory':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_9I0IgEphEe2fXugFmTmyJA'],
    'enhancementstory':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_KkYVwEpiEe2fXugFmTmyJA'],
    'defectstory':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_IimrQEpiEe2fXugFmTmyJA'],
    'sitstory':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.runSavedQuery&id=_ZGy2UEpiEe2fXugFmTmyJA'],
    'technicalspike':['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_iYUsEEpiEe2fXugFmTmyJA'],
    "specificationstory":['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_bK6qMEpiEe2fXugFmTmyJA'],
    "assessmentstory":['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_2HPjMEphEe2fXugFmTmyJA'],

    #"specificationtask":['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_d5vn8EpiEe2fXugFmTmyJA'],
    
    "itpstory":['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=_XB60gEpiEe2fXugFmTmyJA'],
    "csd":['https://rtcus1.ta.philips.com/ccm/web/projects/ULT#action=com.ibm.team.workitem.editQuery&id=__3YAgEphEe2fXugFmTmyJA']
}

###################################
# RTC Property to ADS Attribute mapping
###################################

# Default RTC properties to include in Work Item Queries
default_rtc_properties=['dc:type', 'rtc_cm:plannedFor']

###################################
# RTC Property -> ADS Attribute Map for rtc_query_url_input
###################################
work_items_property_map={

    'common':{
        # RTC PlannedFor -> ADS Iteration (plannedFor value also used for tags)
        "rtc_cm:plannedFor":{
            'path':"/fields/System.IterationPath",
            'formatting':[ 
                'format_ads_iteration_path' 
            ]
        },

        # ADS Area 
        "rtc_cm:filedAgainst":{
            'path':"/fields/System.AreaPath",
            'formatting':[ 
                'format_ads_area_path' 
            ]
        },

        # Story Point / Work Item Size / Progress
        "rtc_cm:progressTracking":{
            'path':'/fields/Microsoft.VSTS.Scheduling.Effort',
            'formatting':[ 
                'format_ads_size' 
            ]
        },


        # RTC Subject + PlannedFor -> ADS Tags
        "dc:subject":{
            'path':'/fields/System.Tags',
            'formatting':[ 
                'format_ads_tags' 
            ]
        },

        # RTC Title -> ADS Title
        "dc:title":{
            # AWS Work Item Title
            'path':'/fields/title',
            'formatting':[ 
                'format_title',
                'char_limit_255'
            ]
        },

        # RTC Description -> ADS Description
        "dc:description":{
            # ADS Work Item Description
            'path':'/fields/System.Description',
            # Formatting to add header info to ADS description
            'formatting':[ 
                'format_description_header' 
            ]
        },

        # RTC ID
        "dc:identifier":{
            # ADS Work Item
            'path':'/fields/Custom.RTCID'
        },

        # RTC work item owner
        "rtc_cm:ownedBy":{
            # ADS Assigned To field
            'path':"/fields/System.AssignedTo",
            # Format RTC user info for ADS
            'formatting':[ 
                'format_ads_user' 
            ]
        },
        
        # ADS ChangedBy
        "rtc_cm:modifiedBy":{
            'path':"/fields/System.ChangedBy",
            'formatting':[ 
                'format_ads_user' 
            ]
        },

        # ADS State
        "rtc_cm:state":{
            'path':"/fields/System.State",
            'formatting':[ 
                'format_ads_state' 
            ]
        },

        # Targeted Release
        "rtc_cm:targeted_release":{
            'path':"/fields/Philips.Planning.Release",
        },

        # Priority
        "oslc_cm:priority":{
            'path':"/fields/Microsoft.VSTS.Common.Priority",
            'formatting':[ 
                'format_ads_priority' 
            ]
        }
       
    },
    
    'epic':{},

    'feature':{

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Planned for Implemented
        'rtc_cm:plannedFor':{
            'path':"/fields/Custom.PlannedforImplemented",
            'formatting':[ 
                'format_string' 
            ]
        },

        # Planned for Implemented RPM
        #'rtc_cm:Planned.for.at.RPM':{
        #    'path':'/fields/Custom.PlannedforImplementedRPM',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},

        # Planned for Done
        #'rtc_cm:Planned.for.Done.Philips':{
        #    'path':'/fields/Custom.PlannedforDone',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},

        # Planned for Done RPM
        #'rtc_cm:Planned.for.Done.at.RPM.Philips':{
        #    'path':'/fields/Custom.PlannedforDoneRPM',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},
    },

    'story':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    'defectstory':{

        # Story Type
        "dc:type":{
            # ADS attribute path
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                # additional value inputting for ADS
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Defect Type
        "rtc_cm:defect":{
            'path':'/fields/Custom.DefectType'
        },

        # Team Track
        "rtc_cm:TTboolean.philips":{
            'path':'/fields/Custom.TeamTrack'
        },

        

    },
    
    'documentationstory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

    },
    
    'enhancementstory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    'specificationstory':{
        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },
    
    'sitstory':{
        # Software
        "rtc_cm:SoftwareAtt":{
            'path':'/fields/Custom.Software',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Sub-Product 
        'rtc_cm:Sub-productAtt':{
            'path':'/fields/Custom.Subproduct',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Issues Found
        "rtc_cm:issues_found":{
            'path':'/fields/Custom.IssuesFound',
            'formatting':[ 
                'format_string',
                'format_char_limit' 
            ]
        },

        # Number of New Issues Found
        'rtc_cm:Number_of_New_Issues_Found':{
            'path':'/fields/Custom.NumberofNewIssuesFound',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # System Serial number
        'rtc_cm:SystemSerialNumber':{
            'path':'/fields/Custom.SystemSerialNumber',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # System Test Area
        'rtc_cm:system_test_area':{
            'path':'/fields/Custom.SystemTestArea',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Cart
        'rtc_cm:cart_type':{
            'path':'/fields/Custom.Cart',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },
    },
    
    'technicalspikestory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    
    },

    'frups':{
        # 12NC
        "rtc_cm:PartNumber12NC":{
            'path':"/fields/Custom.12NC"
        }
    },

    "assessmentstory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    "aststory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    "itpstory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    "specificationstory":{},

    "specificationtask":{},

    "csd":{},

}

###################################
# csv column Property -> ADS Property map for csv_input
###################################
csv_attribute_mappings={
    "common":{
        # rtc id -> RTCID
        "Id":{
            'path':"/fields/Custom.RTCID"
        },
        # rtc created by -> ads created by
        "Created By":{
            'ads_field_name':"",
            'path':"/fields/System.CreatedBy",
            'formatting':[ 
                'format_ads_created_by' 
            ]
        },

        # rtc Creation Date -> ads Creation Date
        "Creation Date":{
            'ads_field_name':"Created Date",
            'path':"/fields/System.CreatedDate"
        },

        # rtc filed against -> ads area path
        "Filed Against":{
            'ads_field_name':"Area Path",
            'path':"/fields/System.AreaPath",
            'formatting':[ 
                'format_ads_area_path' 
            ]
        },
        # rtc filedAgainst -> ads Business Unit
        "Filed Against":{
            'ads_field_name':"Business Unit",
            'path':"/fields/Custom.BusinessUnit"
        },
        # rtc summary -> ads title
        "Summary":{
            'ads_field_name':"Title",
            'path':'/fields/title',
            'formatting':[ 
                'format_title',
                'char_limit_255'
            ]
        },

        # rtc owned by -> ads assigned to
        "Owned By":{
            'ads_field_name':"Assigned To",
            'path':"/fields/System.AssignedTo",
            'formatting':[ 
                'format_ads_assigned_to' 
            ]
        },

        # rtc modified by -> ads ChangedBy
        "Modified By":{
            'ads_field_name':"Changed By",
            'path':"/fields/System.ChangedBy",
            'formatting':[ 
                'format_ads_changed_by' 
            ]
        },

        # rtc Status -> ads state
        "Status":{
            'ads_field_name':"State",
            'path':"/fields/System.State",
            'formatting':[ 
                'format_ads_state' 
            ]
        },

        # tags
        "Tags":{
            'ads_field_name':"Tags",
            'path':'/fields/System.Tags',
            'formatting':[ 
                'format_ads_tags' 
            ]
        },
    },
    "Task":{
        "Planned Completion Date":{
            'ads_field_name':"Planned Completion Date",
            'path':'/fields/Custom.PlannedCompletionDate'
        },
        # RTC Description -> ADS Description
        "Description":{
            # ADS Work Item Description
            'ads_field_name':"Description",
            'path':'/fields/System.Description',
            # Formatting to add header info to ADS description
            'formatting':[ 
                'format_description_header' 
            ]
        }, 

    },
    "Story":{
        # RTC Description -> ADS Description
        "Description":{
            # ADS Work Item Description
            'ads_field_name':"Description",
            'path':'/fields/System.Description',
            # Formatting to add header info to ADS description
            'formatting':[ 
                'format_description_header' 
            ]
        },  
    },
    "FRUPS":{
        # RTC Description -> ADS Description
        "Description":{
            # ADS Work Item Description
            'ads_field_name':"Description",
            'path':'/fields/Custom.Description_WhatHowWhyandWhen',
            # Formatting to add header info to ADS description
            'formatting':[ 
                'format_description_header' 
            ]
        },

        # rtc 12NC -> ads 12NC
        "12NC":{
            # ads property path
            'ads_field_name':"12NC",
            'path':"/fields/Custom.12NC"
            # (optional) additional ads formatting function
        },

        # rtc resolution date -> resolution date
        "Resolution Date":{
            'ads_field_name':"Resolution Date",
            'path':"/fields/Custom.ResolutionDate"
        },

        # rtc PartDescription2 -> PartDescription
        "Part Description":{
            'ads_field_name':"Part Description",
            'path':"/fields/Custom.PartDescription"
        },

        # rtc System Usage -> ads Affected Product Families
        "System Usage":{
            'ads_field_name':"Affected Product Families",
            'path':"/fields/Custom.AffectedProductFamilies",
            'formatting':[ 
                'format_char_limit' 
            ]
            
        },

        # rtc design authority -> ads design authority
         "Design Authority":{
            'ads_field_name':"Design Authority",
            'path':"/fields/Custom.DesignAuthority"
        },

        #System Classification
        "System Classification":{
            'ads_field_name':"System Classification",
            'path':"/fields/Custom.SystemClassification"
        },

        #Number of Parts
        "Number of Parts":{
            'ads_field_name':"Number of Parts",
            'path':"/fields/Custom.NumberofParts"
        },

        #Demand Per Year
        "Demand Per Year":{
            'ads_field_name':"Demand Per Year",
            'path':"/fields/Custom.DemandPerYear"
        },

        #EOS (year)
        "EOS (year)":{
            'ads_field_name':"EOS year",
            'path':"/fields/Custom.EOSyear"
        },

        #SPS Planner
        "SPS Planner":{
            'ads_field_name':"SPS Planner",
            'path':"/fields/Custom.SPSPlanner"
        },

        # rtc Current Work Phase -> ads current work phase
        "Work Phase":{
            'ads_field_name':"Current Work Phase",
            'path':"/fields/Custom.CurrentWorkPhase"
        },

        #FRU Queue Date
        "FRU Queue Date":{
            'ads_field_name':"FRU Queue Date",
            'path':"/fields/Custom.FRUQueueDate"
        },

        #Eng Start Date
        "Eng Start Date":{
            'ads_field_name':"Eng Start Date",
            'path':"/fields/Custom.EngStartDate"
        },

        #Customer Impact Date
        "Customer Impact Date":{
            'ads_field_name':"Customer Impact Date",
            'path':"/fields/Custom.CustomerImpactDate"
        },

        # Daily Management Sequence
        "Daily Management Sequence":{
            'ads_field_name':"Daily Management Sequence",
            'path':"/fields/Custom.DailyManagementSequence"
        },
#########################################################################################
        #Drawing Error Unavailable
        "Drawing Error/Unavailable":{
            'ads_field_name':"Drawing Error Unavailable",
            'path':"/fields/Custom.DrawingErrorUnavailable"
        },

         #Out of Stock No Supplier
        "Out of Stock/No Supplier":{
            'ads_field_name':"Out Of Stock No supplier",
            'path':"/fields/Custom.OutOfStockNosupplier"
        },

        #Risk Category Not Defined
        "Risk Category Not Defined":{
            'ads_field_name':"Risk Category Not Defined",
            'path':"/fields/Custom.RiskCategoryNotDefined"
        },

        #Current Risk Category
        "RISK":{
            'ads_field_name':"Current Risk Category",
            'path':"/fields/Custom.CurrentRiskCategory"
        },

        #Supplier Phase Out
        "Supplier Phase Out":{
            'ads_field_name':"Supllier Phase Out",
            'path':"/fields/Custom.SupllierPhaseOut"
        },

        #Poor Quality
        "Poor Quality":{
            'ads_field_name':"Poor Quality",
            'path':"/fields/Custom.PoorQuality"
        },

        #Supplier on Probation_Disqualified
        "Supplier on Probation/Disqualified":{
            'ads_field_name':"Supplier on Probation_Disqualified",
            'path':"/fields/Custom.SupplieronProbation_Disqualified"
        },

        #Obsolescence End Of Life
        "Obsolescence/End Of Life":{
            'ads_field_name':"Obsolescence End Of Life",
            'path':"/fields/Custom.ObsolescenceEndOfLife"
        },

        #Make To Buy
        "Make-To-Buy":{
            'ads_field_name':"Make to Buy",
            'path':"/fields/Custom.MaketoBuy"
        },

        #SCR Received
        "SCR Received":{
            'ads_field_name':"SCR received",
            'path':"/fields/Custom.SCRreceived"
        },

        #Problem Statement
        "Problem Statement":{
            'ads_field_name':"Problem Statement",
            'path':"/fields/Custom.ProblemStatement",
            'formatting':[ 
                'format_char_limit' 
            ]
            
        },

        #Back Order
        "Back Order":{
            'ads_field_name':"Back Order",
            'path':"/fields/Custom.BackOrder"
        },

        #Back Order Identified On
        "Back Order Identified On":{
            'ads_field_name':"Back Order Identified On",
            'path':"/fields/Custom.BackOrderIdentifiedOn"
        },

        #Current Stock
        "Current Stock":{
            'ads_field_name':"Current Stock",
            'path':"/fields/Custom.CurrentStock",
        },

        #Current Stock Identified On
        "Current Stock Identified On":{
            'ads_field_name':"Current Stock Identified On",
            'path':"/fields/Custom.CurrentStockIdentifiedOn"
        },
    }
}

###################################
# rtcclient python package query variables
###################################
validate_only = False
bypass_rules = True
suppress_notifications = True
ends_with_jazz = False