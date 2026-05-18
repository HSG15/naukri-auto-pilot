
import re


#=====================================================================URLs=========================================================


LOGIN_URL = "https://www.naukri.com/central-login-services/v1/login"
OTP_VERIFY_URL = "https://www.naukri.com/central-login-services/v0/otp-login"
OTP_SEND_URL = "https://www.naukri.com/central-login-services/v1/otp"
PROFILE_URL = "https://www.naukri.com/mnjuser/profile"
FILE_VALIDATION_URL = "https://filevalidation.naukri.com/file"
DASHBOARD_URL = "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard"
PROFILE_UPDATE_URL= "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v1/users/self/fullprofiles"
RESUME_UPDATE_URL_TEMPLATE = "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume"
JOB_SEARCH_URL = "https://www.naukri.com/jobapi/v3/search"
RECOMMENDED_JOBS_URL = "https://www.naukri.com/jobapi/v2/search/recom-jobs"
APPLY_JOB_URL = "https://www.naukri.com/cloudgateway-workflow/workflow-services/apply-workflow/v1/apply"
HISTORY_URL = "https://www.naukri.com/cloudgateway-apply/whtma-services/v0/applyapi/v5/history"


 #===================================================================================================================================

#=======================================RSA public key===============================

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALrlQ+djR0RjJwBF1xuisHmdFv334MIm
K6LgzJhmLhN7B5yuEyaKoasgXQk3+OQglsOaBxEJ0j5PcTL3nbOvt80CAwEAAQ==
-----END PUBLIC KEY-----"""
#==================================================================================

FORM_KEY_PATTERNS = [
    re.compile(r'formKey\s*[:=]\s*["\']([A-Za-z0-9]{8,})["\']'),
    re.compile(r'"formKey"\s*:\s*"([A-Za-z0-9]{8,})"'),
]

APP_JS_PATTERN = re.compile(r'<script[^>]+src="([^"]*app_v\d+\.min\.js[^"]*)"')
