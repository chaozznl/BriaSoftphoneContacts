import sqlite3
from xml.dom.minidom import Element
import xmltodict
import requests
import os
import sys
from sqlite3 import Error
#from xml.dom import minidom
from datetime import datetime

# OPEN LOG FILE
tempfolder = os.getenv('TEMP')
logfilename = "{}\\briaimportlog.txt".format(tempfolder)
logfile = open(logfilename, "w")
    
# GET CURRENT DATE
now = datetime.now()
date_time = "["+now.strftime("%m/%d/%Y %H:%M:%S")+"] "

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logfile.writelines([date_time, "Connection to db succeeded","\n"])

    except Error as e:
        print(e)
        logfile.writelines([date_time, "Connection to db failed","\n"])

    return conn

def importxml(conn, url):
    response = requests.get(url)
    directorydata = xmltodict.parse(response.content)
    numlen = len(directorydata['CiscoIPPhoneDirectory']['DirectoryEntry'])
    logfile.writelines([date_time, "Number of entries in XML:" +str(numlen),"\n"])

    """
    entity_id = INSERT INTO Entity (type, is_favourite, is_readonly) VALUES (1, 1, 0)

    INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('firstname', 'Kabouter', entity_id, 16, 0, 0)
    INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('lastname', 'Wesley', entity_id, 16, 0, 0)
    INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('name', 'Kabouter Wesley', entity_id, 144, 0, 0)
    INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('work', '0612345678', entity_id, 1289, 0, 0)
    INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('avatar', '', entity_id, 192, 0, 0)
    """

    # before we import our custom contacts, lets delete our custom contacts from a previous run
    cur = conn.cursor()
    cur.execute('SELECT * FROM EntityParents WHERE parent_entity = 1')
    records = cur.fetchall()
    count = 0
    for row in records:
        parententity_id = int(row[0])
        # now we have the parententity_id we can delete all records
        # the order in which we delete the records matters because of FOREIGN KEY restraints
        # delete records in table fields where is_readonly = 1
        cur2 = conn.cursor()
        cur2.execute('DELETE FROM Field WHERE is_readonly = 1')
        conn.commit()
        # delete entityparents records part 1
        sqlquery = "DELETE FROM EntityParents WHERE entity_id = ?"
        sqlvalues = (parententity_id,)
        cur2 = conn.cursor()
        cur2.execute(sqlquery, sqlvalues)
        conn.commit()
        # delete entityparents records part 2
        sqlquery = "DELETE FROM EntityParents WHERE parent_entity = ?"
        sqlvalues = (parententity_id,)
        cur2 = conn.cursor()
        cur2.execute(sqlquery, sqlvalues)
        conn.commit()
        # delete records in table Entity where is_readonly = 1
        cur2 = conn.cursor()
        cur2.execute('DELETE FROM Entity WHERE is_readonly = 1')
        conn.commit()
        count += 1
        
    # log action             
    logfile.writelines([date_time, "Cleared "+str(count)+" old entries\n"])             


    for x in range(numlen):
        dirdat_name = directorydata['CiscoIPPhoneDirectory']['DirectoryEntry'][x]['Name']
        dirdat_number = directorydata['CiscoIPPhoneDirectory']['DirectoryEntry'][x]['Telephone']
        dirdat_favourite = directorydata['CiscoIPPhoneDirectory']['DirectoryEntry'][x]['Favourite']
        
        # SPLIT NAME IN FIRST AND LASTNAME IF IT HAS A SPACE IN IT, ELSE LASTNAME IS BLANK
        if ' ' in dirdat_name:
            x = dirdat_name.split()
            dirdat_firstname = x[0]
            dirdat_lastname = x[1]
        
        else:
            dirdat_firstname = dirdat_name
            dirdat_lastname = ''
        
        """
        #
        # FIRST CHECK IF THE ENTITY EXISTS (no longer needed since this version first deletes all old imports)
        #
        sqlquery = "SELECT * FROM Field WHERE name = 'work' AND value = ?"
        sqlvalues = (dirdat_number,)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        
        numrows = len(cur.fetchall()) 
        conn.commit()
        
        #
        # IT EXISTS, SO SKIP THIS RECORD
        #
        if numrows > 0:
            logfile.writelines([date_time, "Skipped: "+dirdat_name,"\n"])
            continue
        """
        logfile.writelines([date_time, "Added: "+dirdat_name,"\n"])
        
        #
        # EVERY CONTACT IS PRECEDED BY A PARENT ENTITY OF TYPE 3
        #
        sqlquery = "INSERT INTO Entity (type, is_favourite, is_readonly) VALUES (?,?,?)"
        sqlvalues = (3, 0, 1)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()
        parententity_id = cur.lastrowid

        #
        # EMPTY FIELD FOR THIS PARENT ENTITY
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('firstname', '', ?, 16, 0, 1)"
        sqlvalues = (parententity_id,)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        # NOW WE CAN ADD A CONTACT

        #
        # CREATE THE ENTITY, TYPE 1 = CHILDENTITY
        #
        sqlquery = "INSERT INTO Entity (type, is_favourite, is_readonly) VALUES (?,?,?)"
        sqlvalues = (1, dirdat_favourite, 1)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()
        entity_id = cur.lastrowid
        
        #
        # CREATE ENTITY PARENT RECORDS. PARENT IS CHILD OF 1, NEW ENTITY IS CHILD OF PARENT
        #
        sqlquery = "INSERT INTO EntityParents (entity_id, parent_entity) VALUES (?,?)"
        sqlvalues = (parententity_id, 1)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        sqlquery = "INSERT INTO EntityParents (entity_id, parent_entity) VALUES (?,?)"
        sqlvalues = (entity_id, parententity_id)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()
    
        # CREATE THE FIELDS FOR THIS ENTITY
    
        #
        # FIRSTNAME
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('firstname', ?, ?, 16, 0, 1)"
        sqlvalues = (dirdat_firstname, entity_id)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        #
        # LASTNAME
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('lastname', ?, ?, 16, 0, 1)"
        sqlvalues = (dirdat_lastname, entity_id)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        #
        # NAME
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('name', ?, ?, 144, 0, 1)"
        sqlvalues = (dirdat_name, entity_id)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        #
        # NUMBER  
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('work', ?, ?, 1289, 0, 1)"
        sqlvalues = (dirdat_number, entity_id)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()

        #
        # AVATAR  
        #
        sqlquery = "INSERT INTO Field (name, value, entity_id, type, is_default, is_readonly) VALUES ('avatar', '', ?, 192, 0, 1)"
        sqlvalues = (entity_id,)
        cur = conn.cursor()
        cur.execute(sqlquery, sqlvalues)
        conn.commit()


def changesettings(settingsfile):
    import xml.etree.ElementTree as ET
 
    tree = ET.parse(settingsfile)
    root = tree.getroot()
 
    for setting in root.findall("./userSettings/Kudu.Properties.Settings/setting[@name='ContactPanelShowGroups']/value"):
        setting.text = "False"
        
    for setting in root.findall("./userSettings/Kudu.Properties.Settings/setting[@name='ContactPanelSortByPresence']/value"):
        setting.text = "False"
        
    for setting in root.findall("./userSettings/Kudu.Properties.Settings/setting[@name='LoginRememberDetails']/value"):
        setting.text = "True"

    tree.write(settingsfile)
    logfile.writelines([date_time, "Settings changed in "+settingsfile,"\n"])

def main():
    # READ XML URL
    if (len(sys.argv) != 2):
        print ("You need to supply an XML URL as parameter.")
        sys.exit()
        
    url = str(sys.argv[1])

    # FIND APPDATA ROAMING
    appdata = os.getenv('APPDATA')
    # SET BRIA CONTACS FOLDER
    briacontactsfolder = "{}\\CounterPath Corporation\\Bria\\6.0".format(appdata)
    # FIND USER FOLDER (email address of bria account)
    subfolders = [ f.path for f in os.scandir(briacontactsfolder) if f.is_dir() ]
    
    # LOOP THROUGH SUBFOLDERS BUT IGNORE DEFAULT_USER
    for x in range(len(subfolders)):
        if subfolders[x][-12:] != "default_user":
            briacontactsfolder = subfolders[x]
 
    logfile.writelines([date_time, "Contact folder: "+briacontactsfolder,"\n"])

    # CONNECT TO SQLLITE DB    
    database = r"{}\contacts.db".format(briacontactsfolder)
    logfile.writelines([date_time, "Database: "+database,"\n"])
    conn = create_connection(database)
    
    # IMPORT XML INTO DB
    importxml(conn, url)

    
    # SET BRIA SETTINGS FOLDER
    briasettingsfolder = "{}\\CounterPath".format(appdata)

    # FIND SETTINGS FOLDER (two subfolders deep in appadata counterpath)
    subfolders = [ f.path for f in os.scandir(briasettingsfolder) if f.is_dir() ]
    
    for x in range(len(subfolders)):
        briasettingsfolder = subfolders[x]
    
    # FIND SECOND SUBFOLDER
    subfolders = [ f.path for f in os.scandir(briasettingsfolder) if f.is_dir() ]

    for x in range(len(subfolders)):
        briasettingsfolder = subfolders[x]
    
    settingsfile = "{}\\user.config".format(briasettingsfolder)
    logfile.writelines([date_time, "Settings folder: "+briasettingsfolder,"\n"])

    changesettings(settingsfile)    
    
    logfile.close()

if __name__ == "__main__":
    main()
