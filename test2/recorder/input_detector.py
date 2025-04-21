import re

# Keywords to identify fields by placeholder/name/id/etc.
FIELD_PATTERNS = {
    "email": re.compile(r"(email)", re.I),
    "password": re.compile(r"(pass|password)", re.I),
    "username": re.compile(r"(user(name)?|login)", re.I),
}

def detect_field_type(attributes):
    for key in FIELD_PATTERNS:
        for attr in attributes:
            if attr and FIELD_PATTERNS[key].search(attr):
                return key
    return None
