"""Pure display decisions. A/B switching never changes analysis or camera."""
def visible_version(status,role,mode):
    if mode=='A+B':return True
    if status in ('SAME','RENAMED'):return True # One shared mesh for identical geometry.
    return role==mode

def opacity(status,role,mode,dim):
    if dim and status in ('SAME','RENAMED'):return .15
    if mode=='A+B' and role=='A' and status!='REMOVED':return .25
    return 1.
