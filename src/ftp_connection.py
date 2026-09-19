from member import Member
from ftplib import FTP

nbr_checked_in_members = len(Member.checked_in_members)
nbr_checked_in_styret = len(Member.checked_in_styret)

host = ''
port = ''
user = ''
password = ''

ftp = FTP(host=host, port=port, user=user, passwd=password)

