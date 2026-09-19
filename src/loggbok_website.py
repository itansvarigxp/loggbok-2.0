from ftplib import FTP
from member import *
def update_loggbok_website():
    host = 'ftp.x-p.nu'
    port = 21 
    user = 'x-p.nu'
    passwd = 'xpgillarfras1944'
    
    LOCAL_FILE = "local_checked_in.txt"
    REMOTE_FILE = "/customers/0/3/1/x-p.nu/httpd.www/någon-i-verkstan/checked_in.txt"

    # new_values = {
    #     "members": str(len(Member.checked_in_members)),
    #     "board": str(len(Member.checked_in_styret))
    # }

    # if len(Member.checked_in_members) == None:
    #     new_values["last_member"] = "0"
    # if len(Member.checked_in_styret) == None:
    #     new_values["last_board"] = "0"
    
    new_values = {
        'members': str(len(Member.checked_in_members)),
        'board': str(len(Member.checked_in_styret)),
    }

    #Skapar en instans av klassen FTP med parametrarna host, port, user och passwd
    ftp = FTP(host=host, user=user, passwd=passwd)

    #Ansluter till servern och loggar in
    try:
        ftp.connect(host=host, port=port)
        ftp.login(user=user, passwd=passwd)
        print(ftp.getwelcome())
    except Exception as e:
        print("Kunde inte ansluta till servern. Felmeddelande: ", e)
        ftp.quit()

    #Funktion för att lista filer i en mapp EV ta bort
    # try:
    #     filer = ftp.dir('/customers/0/3/1/x-p.nu/httpd.www/någon-i-verkstan')
    #     # print(filer)
    # except Exception as e:
    #     print("Kunde inte lista filer. Felmeddelande: ", e)
    #     ftp.quit()

    #Läser in checked_in.txt och sparar ned den lokalt
    try:
        # Download the file
        with open(LOCAL_FILE, "wb") as f:
            ftp.retrbinary(f"RETR {REMOTE_FILE}", f.write)
        print(f"Downloaded {REMOTE_FILE} to {LOCAL_FILE}")
        #Read the file and update
        with open(LOCAL_FILE, "r") as f:
            lines = f.readlines()
        


        with open(LOCAL_FILE, "w") as f:
            for line in lines:
                key, value = line.strip().split("=", 1)
                if key in new_values:
                    value = new_values[key]
                f.write(f"{key}={value}\n")
        print(f"Updated {LOCAL_FILE} with new values")

        # Step 4: Upload the updated file back to the server
        with open(LOCAL_FILE, "rb") as f:
            ftp.storbinary(f"STOR {REMOTE_FILE}", f)
        print(f"Uploaded updated {LOCAL_FILE} back to the server as {REMOTE_FILE}")
            


    except Exception as e:
        print("Kunde inte hämta filen. Felmeddelande: ", e)
        ftp.quit()

    #Stänger anslutningen till servern
    ftp.quit()
    print('Anslutningen till servern är stängd')

