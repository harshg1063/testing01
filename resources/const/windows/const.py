class NONE_THIRD_PARTY_APP():
    APP_LIST = ["DESKTOP", "JWEB", "HPAI", "JWEB_DATA_COLLECTION", "GOTHAM", "HPX", "JWEB_SERVICE_ROUTING", "JWEB_VALUE_STORE", "JWEB_DOC_PROVIDER", "JWEB_EVENT_SERVICE", "JWEB_AUTH", "JWEB_STORAGE_MANAGER"]


class APP_NAME():
    DESKTOP = "Root"
    JWEB = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj!App"
    JWEB_STORAGE_MANAGER = "18350e35-fc46-4385-8bb0-2f9f283b3389_bw7dk9vfm82wj!App"
    JWEB_DATA_COLLECTION = "35eefeaa-69ad-4590-8d08-0ffd92d54f5e_bw7dk9vfm82wj!App"
    JWEB_SERVICE_ROUTING = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj!App"
    JWEB_EVENT_SERVICE = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj!App"
    JWEB_AUTH = "28bccee1-2b93-4cca-8e56-4e3db0828093_bw7dk9vfm82wj!App"
    JWEB_VALUE_STORE =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f_bw7dk9vfm82wj!App"
    JWEB_DOC_PROVIDER =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f_bw7dk9vfm82wj!App"
    GOTHAM = "AD2F1837.HPPrinterControl_v10z8vjag6ke6!AD2F1837.HPPrinterControl"
    HPX = "AD2F1837.myHP_v10z8vjag6ke6!App"
    HPAI = "AD2F1837.HPAIExperienceCenter_v10z8vjag6ke6!App"
    

class PACKAGE_NAME():
    GOTHAM = "AD2F1837.HPPrinterControl_v10z8vjag6ke6"
    JWEB = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj"
    JWEB_STORAGE_MANAGER = "18350e35-fc46-4385-8bb0-2f9f283b3389_bw7dk9vfm82wj!App"
    JWEB_DATA_COLLECTION = "35eefeaa-69ad-4590-8d08-0ffd92d54f5e_bw7dk9vfm82wj"
    JWEB_SERVICE_ROUTING = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj"
    JWEB_EVENT_SERVICE = "1132d5c8-e05c-4b46-87cd-e31dad772e89_bw7dk9vfm82wj"
    JWEB_AUTH = "28bccee1-2b93-4cca-8e56-4e3db0828093_bw7dk9vfm82wj!App"
    JWEB_VALUE_STORE =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f_bw7dk9vfm82wj"
    JWEB_DOC_PROVIDER =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f_bw7dk9vfm82wj"
    HPX = "AD2F1837.myHP_v10z8vjag6ke6"
    HPAI = "AD2F1837.HPAIExperienceCenter"

class PROCESS_NAME():
    GOTHAM = "*hpprintercontrol*"
    JWEB = "1132d5c8-e05c-4b46-87cd*"
    JWEB_STORAGE_MANAGER = "HP.Jarvis.Storage*"
    JWEB_DATA_COLLECTION = "35eefeaa-69ad-4590-8d08-0ffd92d54f5e"
    JWEB_SERVICE_ROUTING = "HP.Jarvis.ServiceRouting*"
    JWEB_EVENT_SERVICE = "HP.Jarvis.EventService*"
    JWEB_AUTH = "HP.Jarvis.Auth*"
    JWEB_VALUE_STORE =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f"
    JWEB_DOC_PROVIDER =  "8a158fa1-dcc2-4ca6-aef0-d37d1152a20f"
    HPX = "*myHP*"
    HPAI = "*HPAI*"

class EXTRA_INSTALLER_PATH():
    #I can't use full path because version number
    #These are substrings
    #Currently no solution for more than 1 level down
    #Unless we do wild card regex match for all sub folders
    JWEB = "HP.Jarvis.WebView.Reference"
    JWEB_STORAGE_MANAGER = "HP.Jarvis.Storage.Plugin.Reference"
    JWEB_DATA_COLLECTION = "HP.Jarvis.DataCollection.Reference"
    JWEB_SERVICE_ROUTING = "HP.Jarvis.ServiceRouting.Reference"
    JWEB_EVENT_SERVICE = "HP.Jarvis.EventService.Reference"
    JWEB_AUTH = "HP.Jarvis.Auth.Harness"
    JWEB_VALUE_STORE = "HP.Jarvis.ValueStore.Reference"
    JWEB_DOC_PROVIDER = "HP.Jarvis.DocProvider.Reference"
    HPX = "HP.HPX"
    HPAI = "_Test"

class TEST_DATA():
    GOTHAM_APP_LOG_PATH = r"C:\Users\exec\AppData\Local\Packages\AD2F1837.HPPrinterControl_v10z8vjag6ke6\LocalState"
    DESKTOP_APP_LOG_PATH = r"C:\Users\exec\AppData\Local\Packages\AD2F1837.HPPrinterControl_v10z8vjag6ke6\LocalState"
    HPX_APP_LOG_PATH = r"C:\Users\exec\AppData\Local\Packages\AD2F1837.myHP_v10z8vjag6ke6\LocalState"
    HPX_SHARED_JSON_PATH = r"C:\Users\exec\AppData\Local\Publishers\v10z8vjag6ke6\HPX"
    COLOR_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\color.pdf"
    GREEN_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\green_automation.pdf"
    PASSWORD_PROTECTED_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\password_protected.pdf"
    CORRUPTED_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\corrupted.pdf"
    TEST_50PAGES_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\test_50pages.pdf"
    PASSWORD_PROTECTED_1_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\abc_1234.pdf"
    TEST_30KB_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\non_embedded_cjk.pdf"
    TEST_260KB_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\more_than_50pages.pdf"
    TEST_1MB_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\1page_1mb.pdf"
    TEST_3MB_PDF = r"C:\Users\exec\Documents\test_data\documents\pdf\1page_3mb.pdf"
    ONE_PAGE_DOC = r"C:\Users\exec\Documents\test_data\documents\doc\1page.doc"
    WOMAN_BMP = r"C:\Users\exec\Documents\test_data\images\bmp\woman.bmp"
    INVERTED_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\inverted_text_image.jpg"
    AUTUMN_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\autumn.jpg"
    PLANT_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\plant.jpg"
    MAP_18MB_JPEG = r"C:\Users\exec\Documents\test_data\images\jpeg\jpeg_oversized\map_18MB.jpeg"
    HANDWRITTEN_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\Handwritten.jpg"
    BUSINESSCARD_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\BusinessCard.jpg"
    Document_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\document.jpg"
    RECEIPT_PNG = r"C:\Users\exec\Documents\test_data\images\png\Receipt.png"
    FISH_PNG = r"C:\Users\exec\Documents\test_data\images\png\fish.png"
    WORM_JPEG = r"C:\Users\exec\Documents\test_data\images\jpeg\worm_jpeg.jpeg"
    CORRUPTED_JPEG = r"C:\Users\exec\Documents\test_data\images\jpeg\jpeg_corrupted\corrupted.jpeg"
    LARGE_JPG = r"C:\Users\exec\Documents\test_data\images\jpg\large_image.jpg"
    PACKAGES_PATH = r'C:\Users\exec\AppData\Local\Packages'
    PICTURE_FOLDER_PATH = r"C:\Users\exec\Pictures"
    DOCUMENTS_FOLDER_PATH = r"C:\Users\exec\Documents"
    SUPPORT_RESOURCES_PATH = r"C:\Program Files (x86)\HP\HPX Support\Resources"
    PLATFORM_FILE = r"C:\Users\exec\platform.txt"
    DISPLAY_CONTROL_SERVIVE = r"C:\Program Files\Portrait Displays\HP Display Control Service"
    HPDC_SERVICE = r"C:\ProgramData\Portrait Displays\Display Tune\2.0\HPDC"
    LOGGINGDATA_XML_PATH = "resources/test_data/smart/windows/LoggingData.xml"
    TEST_50PAGES_PDF_PATH = "resources/test_data/documents/pdf/test_50pages.pdf"
    PASSWORD_PROTECTED_1_PDF_PATH = "resources/test_data/documents/pdf/abc_1234.pdf"
    RECEIPT_PNG_PATH = "resources/test_data/images/png/Receipt.png"
    INVERTED_JPG_PATH = "resources/test_data/images/jpg/inverted_text_image.jpg"
    AUTUMN_JPG_PATH = "resources/test_data/images/jpg/autumn.jpg"
    BUSINESSCARD_JPG_PATH = "resources/test_data/images/jpg/BusinessCard.jpg"
    HANDWRITTEN_JPG_PATH = "resources/test_data/images/jpg/Handwritten.jpg"
    Document_JPG_PATH = "resources/test_data/images/jpg/document.jpg"
    HP_SMART_LOG_PATH = "C:\\Users\\exec\\AppData\\Local\\Packages\\AD2F1837.HPPrinterControl_v10z8vjag6ke6\\LocalState\\Logs\\HPSmart.log"
    IMAGE_PATH = "resources/test_data/golden_images_sets/windows/smart/"
    HPX_SCREENSHOT_PATH = "/resources/test_data/hpx_rebranding/screenshot/"
    HPX_SUPPORT_TEST_STACK = "/resources/test_data/hpsa/stack_info.json"
    HPX_SUPPORT_SIMU_PATH = "resources/test_data/hpsa/simulate/"
    REPLACE_PROPERTIES_PATH = "/resources/test_data/hpx_rebranding/action_file/properties.json"
    PDSMQ_DATA_PATH = "C:\\Users\\exec\\AppData\\Local\\Packages\\AD2F1837.HPPrinterControl_v10z8vjag6ke6\\TempState\\HP\\PDSMQ\\Pdsmq.Data.txt"
    CHROME_CACHE_PATH = '"C:\\Users\\exec\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache\\*"'
    WINDOWS_APP_PATH = "C:\\Program Files\\WindowsApps"
    SMS_PATH = "resources/test_data/documents/xlsx/"
    STATUS_IMAGE = "resources/test_data/printer_status/"
    HPX_SUPPORT_TEST_STACK = "/resources/test_data/hpsa/stack_info.json"
    HPX_SUPPORT_SIMU_PATH = "resources/test_data/hpsa/simulate/"
    GMAIL_TOKEN_PATH = "/qama/framework/data/gmail.token"
    GMAI_ACCOUNT = "/resources/test_data/email/account.json"


class ORIENTATION():
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

class OUTPUT_QUALITY():
    FAST = "fast"
    NORMAL = "normal"
    HIGHQUALITY = "highquality"
    
class TEST_TEXT():
    TEST_TEXT_00 = "gotham_test"
    TEST_TEXT_01 = "gotham_test_01"
    TEST_TEXT_02 = "gotham_test_02"
    WARNING_MSG_VALUE = "No results for "
    INVALID_IP = "192.168.1.1"

class LAUNCH_ACTIVITY():
    GOTHAM_DESKTOP = "hp-smart:AD2F1837.HPPrinterControl*"
    # HPX_DESKTOP="ms-settings:system"  
    HPX_DESKTOP="myHP:AD2F1837.myHP*"

class CLOSE_ACTIVITY():
    GOTHAM_DESKTOP = "*HP.Smart*"
    HPX_DESKTOP="*HP.myHP*"
   
class COPTOR():
    COPTOR_URL = "https://oauth-auth-coptor.stg.oc.hp.com/oauth2/v1/auth?client_id=6caa342b-d286-458e-b53e-ce4a2066c555&response_type=code&scope=openid&state=2-d5ed-479b-a82d&redirect_uri=https://content-itg.methone.hpcloud.hp.net/profile/IndexX.html&config_id=59f93866-d28f-4aee-b150-947045966bdc"

class PRINTER_INFO():
    POSTAL_CODE = 92127

class SUPPLY_VALIDATION():
    ERROR_MESSAGE = "resources/test_data/printer_status/error_message.json"
    WARNING_MESSAGE = "resources/test_data/printer_status/warning_message.json"
    INFORM_MESSAGE = "resources/test_data/printer_status/inform_message.json"

class HPX_ACCOUNT():
    account_details_path = "resources/test_data/hpx_rebranding/account.json"
