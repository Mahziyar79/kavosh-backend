# ad_auth.py
import os
from ldap3 import Server, Connection, ALL, NTLM, ALL_ATTRIBUTES, SUBTREE

AD_SERVER   = os.getenv("AD_SERVER") or os.getenv("ACTIVE_ADDRESS") or "ldap://addshqsrv-03.alborz.local:389"
AD_BASE_DN  = os.getenv("AD_BASE_DN") or os.getenv("ACTIVE_SEARCH_BASE") or "DC=alborz,DC=local"
AD_BIND_USER= os.getenv("AD_BIND_USER") or os.getenv("AD_USER") or "alborz\\ldap.user"
AD_BIND_PASS= os.getenv("AD_BIND_PASSWORD") or os.getenv("AD_PASSWORD") or "your-ad-password"

ALLOWED_TITLES = {t.strip().lower() for t in os.getenv("AD_ALLOWED_TITLES", "Manager").split(",") if t.strip()}
ALLOWED_GROUPS = [g.strip() for g in os.getenv("AD_ALLOWED_GROUP_DNS", "").split(",") if g.strip()]

def _mk_server():
    return Server(AD_SERVER, get_info=ALL)

def _service_bind():
    srv = _mk_server()
    conn = Connection(srv, user=AD_BIND_USER, password=AD_BIND_PASS, authentication=NTLM, auto_bind=True)
    return srv, conn

def _find_user_dn(conn: Connection, identifier: str) -> str | None:
    """
    identifier می‌تواند ایمیل، UPN یا sAMAccountName باشد.
    """
    userpart = identifier.split('@')[0]
    filt = f"(|(userPrincipalName={identifier})(mail={identifier})(sAMAccountName={userpart}))"
    conn.search(
        search_base=AD_BASE_DN,
        search_filter=filt,
        search_scope=SUBTREE,
        attributes=ALL_ATTRIBUTES,
        size_limit=1
    )
    if not conn.entries:
        return None
    return conn.entries[0].entry_dn

def authenticate_ad_user(email_or_username: str, password: str) -> dict | None:

    if not email_or_username or not password:
        return None

    srv, svc = _service_bind()

    dn = _find_user_dn(svc, email_or_username)
    if not dn:
        svc.unbind()
        return None

    uconn = Connection(srv, user=dn, password=password, auto_bind=False)
    if not uconn.bind():
        svc.unbind()
        return None

    uconn.search(
        search_base=dn,
        search_filter="(objectClass=person)",
        attributes=["mail", "userPrincipalName", "displayName", "sAMAccountName", "memberOf", "title"]
    )
    info = {"dn": dn, "mail": None, "upn": None, "displayName": None, "sAMAccountName": None, "memberOf": [], "title": None}
    if uconn.entries:
        e = uconn.entries[0]
        info["mail"] = str(e.mail.value) if "mail" in e else None
        info["upn"] = str(e.userPrincipalName.value) if "userPrincipalName" in e else None
        info["displayName"] = str(e.displayName.value) if "displayName" in e else None
        info["sAMAccountName"] = str(e.sAMAccountName.value) if "sAMAccountName" in e else None
        if "memberOf" in e and e.memberOf.values:
            info["memberOf"] = list(e.memberOf.values)
        info["title"] = str(e.title.value) if "title" in e else None

    uconn.unbind()
    svc.unbind()
    return info

def is_user_authorized(ad_info: dict) -> bool:
    title_ok = (ad_info.get("title") or "").strip().lower() in ALLOWED_TITLES if ad_info.get("title") else False
    if ALLOWED_GROUPS:
        user_groups = {g.lower() for g in ad_info.get("memberOf", [])}
        groups_ok = any(g.lower() in user_groups for g in ALLOWED_GROUPS)
    else:
        groups_ok = False
    return title_ok or groups_ok
