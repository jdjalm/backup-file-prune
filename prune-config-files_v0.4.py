"""
Author: jdjalm
Date: 3/22/2023
Version 0.4
Purpose: This script will search a directory and attempt to identify redundant configuration backup files and prune them.
Details: https://github.com/jdjalm

Notes:

*Configuration backup files must be named so that the identifying hostname comes first and has an underscore immediately following the device name if any date or time data is included as well. For example:

co-access-switch-02
hq-edgefirewall_config_07-04-2022T23:50:00.xml
ca-corerouter-01.netmgmt.mydomain.tld_backup_02-01-2023T23:50:00.txt
ny-dist-sw-02.mydomain.tld_03-22-2023T23:59:00

"""

#Import libraries
import sys
import os
import datetime
import argparse
import hashlib
import shutil
from pathlib import Path

#Parse arguments
parser = argparse.ArgumentParser(description = "This script is a WIP. It is meant to prune redundant configuration files from the provided directory.", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-s", "--searchpath", help = "Absolute or relative directory path where configuration files reside. If omitted, the current working directory is used.")
parser.add_argument("-x", "--execute", action = "store_true", help = "This option must be specified to execute the script action of pruning the configuration files; otherwise, script will only run as a check and take no action. If this option is specified, it must be done alongside the option to either prune (move) or remove (delete) the redundant files.")
parser.add_argument("-p", "--prunepath", help = "Absolute or relative directory path where pruned configuration files will be moved into. If this option is specified, it must be accompanied by the execute option/flag. If the execute flag is omitted or the prune path is invalid/inaccessible, then the script will run in check-only mode.")
parser.add_argument("-r", "--remove", action = "store_true", help = "Configures the script to delete the redundant files. No further prompt is given. It's recommended to run the script in check-only mode first. If this option is specified, it must be accompanied by the execute option/flag or the script will run in check-only mode.")
parser.add_argument("-d", "--days", help = "Specifies how many days back to search for configuration backup files. Range is between 0 (same-day) and 90 days. Default is 7 days.")
parser.add_argument("-v", "--verbose", action = "store_true", help = "Increase script verbosity. Default is false.")
args = vars(parser.parse_args())

#Path to configuration files
if args["searchpath"]:
    if Path(args["searchpath"]).is_dir():
        path_backups = args["searchpath"]
    else:
        print("\nERROR: Search path argument is not a directory or insufficient permissions! Exiting...\n")
        exit()
else:
    path_backups = os.getcwd()

#Determine action to be taken based on options
check_only = True
if args["execute"]:
    check_only = False
    if not args["remove"]:
        if args["prunepath"]:
            #Sanitize
            path_pruned = args["prunepath"]
            if not path_pruned[-1:] == "/": path_pruned = path_pruned + "/"
            #Verify
            if not Path(path_pruned).is_dir():
                print("\nWARNING: Prune path argument [" + path_pruned +"] is not a directory or insufficient permissions! Running script in check-only mode...")
                check_only = True
        else:
            print("\nWARNING: If the execute option is enabled, then either the remove option must be enabled or a prune path must be provided. Running script in check-only mode...")
            check_only = True

#History timeframe
if args["days"]:
    try:
        hdays = int(args["days"])
        if not (int(hdays) >= 0 and int(hdays) < 91):
            print("\nWARNING: History days to search is not between 0 and 90; using default of 7 days.")
            hdays = 7
    except:
        print("\nWARNING: History days to search is not a digit; using default of 7 days.")
        hdays = 7
else:
    hdays = 7

#Buffer byte size for reading files as binary in chunks, best practice although we're likely dealing with tiny files
buffer_size = 65536

#Time objects
today = datetime.date.today()
history_day = today - datetime.timedelta(hdays)

#Verbose output print method
def printv(msg):
    if args["verbose"]:
        print(str(msg))

#Returns the simple creation date for a file object
def cDate(cfile):
    return datetime.date.fromtimestamp(cfile.stat().st_mtime)

#Returns the simple creation datetime for a file object
def cDatetime(cfile):
    return datetime.datetime.fromtimestamp(cfile.stat().st_mtime)

#Returns the device name extracted from the absolute file path
def getDeviceName(file):
    return str(file).split('_')[0].split('/')[-1]

#Returns the full file name extracted from the absolute file path
def getFileName(file):
    return str(file).split('/')[-1]

#Yields files created within the history days period and up until today
def getFiles(path):
    for file in Path(path).glob("*"):
        #Check for possible PermissionError or non-file objects
        try:
            is_file = file.is_file()
        except PermissionError:
            printv("\tSkipping. No permissions to access file: " + str(file))
            continue
        #ADDITION: need to add a check for accepted filename endings, eg. .txt, .xml, etc
        if not is_file:
            printv("\tSkipping. Object is not a file: " + str(file))
            continue
        #Calculate day of month
        fcdate = cDate(file)
        #If file is from within the history days range, yield it
        if is_file and (fcdate >= history_day):
            printv("\tYielding file for device [" + getDeviceName(file) + "] from [" + str(fcdate) + "]: " + str(file))
            yield file

#Compute the SHA256 hash and return the digest as a string; reads entire contents as binary
def fileDigest(path):
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(buffer_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

#Compute the SHA256 hash and return the digest as a string; assumes files are ASCII and will ignore any lines starting with ! as those are considered comments
def fileDigestSansComments(path):
    sha256 = hashlib.sha256()
    with open(path, 'r') as f:
        for line in f:
            if line[:1] == "!":
                continue
            else:
                sha256.update(line.encode("utf-8"))
    return sha256.hexdigest()

#Main logic
print("\nStarting...")

#Find files
print("\nFinding all files from the past [" + str(hdays) + "] days in directory: " + path_backups)
printv("")

#List of unique devices for which files were found
backup_devices = []
#List of list objects, each list object is all the files found for a particular device
backup_files = []
#Iterate
for bfile in getFiles(path_backups):
    dname = getDeviceName(bfile)
    if dname in backup_devices:
        idx = backup_devices.index(dname)
        printv("\t\tDevice found in device list at index: [" + str(idx) + "]")
        newest = True
        for i, f in enumerate(backup_files[idx]):
            if cDatetime(bfile) > cDatetime(f):
                continue
            else:
                printv("\t\tFile is not newest one in file list, inserted at index: [" + str(i) + "]")
                backup_files[idx].insert(i, bfile)
                newest = False
                break
        if newest:
            printv("\t\tFile is newest one in file list, appending it...")
            backup_files[idx].append(bfile)
    else:
        printv("\t\tDevice not found in device list, appending device and file to index: [" + str(len(backup_devices)) + "]")
        backup_devices.append(dname)
        backup_files.append([bfile])

#Done searching
print("\nDone searching for files.")

#Output results of files found
tf = 0
for i in backup_files: tf += len(i)
print("\nFound [" + str(tf) + "] files in total for [" + str(len(backup_devices)) + "] unique devices...")
if args["verbose"]:
    print("\nFiles found:\n")
    for idx, iterx in enumerate(backup_devices):
        print("\t[" + str(idx + 1) + "] - " + str(iterx))
        for idl, itery in enumerate(backup_files[idx]):
            print("\t\t[" + str(idl + 1) + "] - " + str(itery))

#Compare and delete
print("\nComparing files for pruning...")
#List of list objects, each list object is all the files for a particular device that are set to be deleted
prune_files = []
#Iterate over 2D array/list
for idp, iterp in enumerate(backup_files):
    printv("\n\tDevice [" + str(idp + 1) + "][" + str(backup_devices[idp]) + "] has " + str(len(iterp)) + " files in total:")
    #Index 0 has oldest file which will never be deleted
    for idz, iterz in enumerate(iterp):
        #If there's only one file in list, nothing will be deleted, break
        if len(iterp) > 1 :
            if (idz + 1) < len(iterp):
                printv("\t\tComparing files... ")
                iterz_digest = fileDigestSansComments(str(iterz))
                iterz_next_digest = fileDigestSansComments(str(iterp[idz + 1]))
                #Hex digest is hexadecimal encoding (4 byte) of the 256 bit hash, hence 64 chars, print only last 32 for brevity
                printv("\t\t\t[" + str(idz + 1) + "] - " + str(getFileName(iterz)) + " - Second half of hash: ..." + iterz_digest[-32:])
                printv("\t\t\t[" + str(idz + 2) + "] - " + str(getFileName(iterp[idz + 1])) + " - Second half of hash: ..." + iterz_next_digest[-32:])
                #Compare files
                if iterz_digest == iterz_next_digest:
                    #Next file is the same, add this one to prune list
                    printv("\t\t\tSAME! Adding [" + str(idz + 2) + "] - " + str(getFileName(iterp[idz + 1])) + " to prune list!")
                    prune_files.append(iterp[idz + 1])
                else:
                    #Diff, keep
                    printv("\t\t\tDIFFERENT! Keeping file and moving on...")
        else:
            printv("\t\t\tSKIPPING! Single file found for this device...")
            break

#Show results of prune list
print("\nFound [" + str(len(prune_files)) + "] files that need pruning...")
if args["verbose"] and (len(prune_files) > 0):
    print("\nPrune file list:\n")
    for idr, r in enumerate(prune_files):
        print("\t[" + str(idr + 1) + "] - " + str(r))

#Actions taken
if check_only:
    print("\nScript ran in check-only mode - no actions were taken.")
else:
    if args["remove"]:
        print("\nDeleting redundant files...")
        #Delete all redundant files
        deleted = 0
        for rm in prune_files:
            os.remove(rm)
            deleted += 1
        print("\nDeleted [" + str(deleted) + "] redundant files...")
    else:
        print("\nMoving redundant files to prune directory: " + path_pruned)
        moved = 0
        for mv in prune_files:
            #Move all redundant files
            shutil.move(mv, path_pruned + str(getFileName(mv)))
            moved += 1
        print("\nMoved [" + str(moved) + "] redundant files...")

#Exit notify
print("\nDone, exiting...\n")
