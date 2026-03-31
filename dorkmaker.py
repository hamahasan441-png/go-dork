"""Advanced dork query builder with operators and preset templates."""

# Google dork operators and descriptions
OPERATORS = {
    "site": {
        "description": "Restrict results to a specific site or domain",
        "example": "site:example.com",
        "placeholder": "example.com",
    },
    "inurl": {
        "description": "Find pages with a word in the URL",
        "example": 'inurl:"/admin"',
        "placeholder": "/admin",
    },
    "intitle": {
        "description": "Find pages with a word in the title",
        "example": 'intitle:"login"',
        "placeholder": "login",
    },
    "intext": {
        "description": "Find pages containing specific text in the body",
        "example": 'intext:"password"',
        "placeholder": "password",
    },
    "filetype": {
        "description": "Search for specific file types",
        "example": "filetype:pdf",
        "placeholder": "pdf",
    },
    "ext": {
        "description": "Search for specific file extensions",
        "example": "ext:sql",
        "placeholder": "sql",
    },
    "cache": {
        "description": "View Google's cached version of a page",
        "example": "cache:example.com",
        "placeholder": "example.com",
    },
    "link": {
        "description": "Find pages linking to a URL",
        "example": "link:example.com",
        "placeholder": "example.com",
    },
    "related": {
        "description": "Find sites related to a given site",
        "example": "related:example.com",
        "placeholder": "example.com",
    },
    "allintitle": {
        "description": "All words must appear in the title",
        "example": 'allintitle:"admin panel"',
        "placeholder": "admin panel",
    },
    "allinurl": {
        "description": "All words must appear in the URL",
        "example": "allinurl:admin login",
        "placeholder": "admin login",
    },
    "allintext": {
        "description": "All words must appear in the page text",
        "example": "allintext:username password",
        "placeholder": "username password",
    },
}

# Preset dork templates by category
TEMPLATES = {
    "Admin Panels": [
        'intitle:"admin panel" inurl:admin',
        'inurl:"/admin/login"',
        'intitle:"dashboard" inurl:admin',
        'inurl:"admin.php" | inurl:"admin.asp"',
        'inurl:"/wp-admin"',
        'intitle:"control panel" inurl:cpanel',
        'inurl:"/administrator" intitle:"login"',
        'inurl:"/admin" intitle:"sign in"',
    ],
    "Login Pages": [
        'intitle:"login" inurl:login',
        'inurl:"/signin" | inurl:"/sign-in"',
        'intitle:"log in" "username" "password"',
        'inurl:"user/login" | inurl:"account/login"',
        'intitle:"member login"',
        'inurl:"/auth/login"',
    ],
    "Exposed Files": [
        'intitle:"index of" "parent directory"',
        'intitle:"index of" ".env"',
        'intitle:"index of" "wp-config.php"',
        'filetype:sql "INSERT INTO"',
        'filetype:log "password"',
        'filetype:env "DB_PASSWORD"',
        'filetype:xml "password"',
        'intitle:"index of" ".git"',
    ],
    "Database Exposure": [
        'inurl:"/phpmyadmin/" intitle:"phpMyAdmin"',
        'intitle:"Adminer" inurl:adminer',
        'inurl:"/pgadmin" intitle:"pgAdmin"',
        'filetype:sql "CREATE TABLE" "password"',
        'inurl:"db" filetype:sql',
        '"MySQL dump" filetype:sql',
    ],
    "Sensitive Information": [
        'filetype:pdf "confidential"',
        'filetype:xlsx "password"',
        'filetype:doc "internal use only"',
        '"API_KEY" | "api_secret" filetype:env',
        '"BEGIN RSA PRIVATE KEY" filetype:key',
        'filetype:cfg "password"',
    ],
    "Vulnerable Servers": [
        'intitle:"Apache Status" "Apache Server Status"',
        'intitle:"PHP Version" "PHP Credits"',
        '"powered by" inurl:"/wp-content/"',
        'inurl:"/server-status" intitle:"Apache"',
        'inurl:"/server-info" intitle:"Apache"',
        '"Welcome to nginx" intitle:"Welcome to nginx"',
    ],
    "Error Messages": [
        '"SQL syntax" "mysql" site:',
        '"Warning: mysql_" | "Warning: pg_"',
        '"Fatal error: " "on line" filetype:php',
        '"ORA-" "error" site:',
        '"ODBC" "error" site:',
        '"syntax error" "unexpected" filetype:php',
    ],
    "IoT & Cameras": [
        'intitle:"webcamXP 5" | intitle:"webcam 7"',
        'inurl:"/view.shtml" "Network Camera"',
        'intitle:"Live View / - AXIS"',
        'inurl:"lvappl" intitle:"Live View"',
    ],
}


def build_query(parts: list[dict]) -> str:
    """
    Build a dork query from a list of operator parts.

    Each part is a dict with keys:
        - operator: str (e.g. "inurl", "site", "intitle")
        - value: str (the value for that operator)
        - negate: bool (optional, prepend '-' to negate)

    Returns:
        A combined dork query string.
    """
    fragments = []
    for part in parts:
        op = part.get("operator", "").strip()
        value = part.get("value", "").strip()
        negate = part.get("negate", False)

        if not value:
            continue

        if op and op in OPERATORS:
            # Quote value if it contains spaces and isn't already quoted
            if " " in value and not (value.startswith('"') and value.endswith('"')):
                value = f'"{value}"'
            fragment = f"{op}:{value}"
        else:
            # Plain keyword
            if " " in value and not (value.startswith('"') and value.endswith('"')):
                value = f'"{value}"'
            fragment = value

        if negate:
            fragment = f"-{fragment}"

        fragments.append(fragment)

    return " ".join(fragments)
