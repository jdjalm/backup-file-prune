# backup-file-prune.py

This script is used for pruning away redundant configuration backup files.

# Overview

If you have a process to backup configuration files from devices on a daily basis (ASCII based, single-file backups, eg. .xml, .txt, etc), you can use this custom script to prune away needless, redundant copies by removing (or relocating) the ones in which the configuration did not change from one save file to the next.

This script was borne from the need to keep track of network device configurations free of redundancy and to provide a straighforward way to audit when configuration changes have taken place historically. There are other alternatives that offer somewhat similar, albeit less flexible, functionality such as SolarWinds NCM and [pyATS Genie](https://developer.cisco.com/codeexchange/github/repo/hpreston/genie-config-diff).

# Details

This script will search for all files in the provided directory, or in the current working directory if none is specified. It will attempt to identify the device hostname of the configuration file by reading all characters **_before the first underscore_** and will create a list of all files for each device in order of file creation. Example filename formats that work:

```
hq-edgefirewall_config_07-04-2022T23:50:00.xml
ca-corerouter-01.netmgmt.mydomain.tld_backup_03-22-2023T23:50:00.txt
ny-accessrouter-02.mydomain.tld
```

For each device, the oldest file in the list is never pruned and is considered the starting configuration. Each file older than that is compared against the one that came before and pruned if no changes were made.

It is assumed that configuration files are UTF-8 encoded and that's how they're read and processed. There's no need to have any specific extension in the filename ending but encoding is important as some comparisons require ignoring certain portions of the configuration contents (eg. NX-OS backups).

The NX-OS devices produce a configuration file that contains the date and time the file was generated. This can cause each new file to appear different than the last and thus, no files would ever be pruned. This has been accounted for in the script and lines beginning with an exclamation mark are ignored.

There is plenty of error checking in built into the script including argument sanitization, directory and file validation and access, etc.

The script is very flexible and has several parameters that can be tuned. It's designed to run only on Linux machines with Python3 installed. The script is currently in its beta stage and has been thoroughly tested during development.

### pyATS Genie

This is one option to achieve a similar outcome to that offered by this script but I've never explored it and I'm not sure how flexible it is comparatively. This script can be applied to any UTF-8 encoded configuration backup files, spanning back months and without the need to specify any 'gold' config -- it simply tracks changes from one save file to the next, even within the same day.

This means that if you are in the unlikely scenario of having to manage many devices that undergo constant changes and have the need to back them up several times per day, this script can be useful. Additionally, if you already have daily backups automated, this script can be implemented with minimal disruption or changes.

# Parameters

| Name | Flag | Sample Usage | Description |
| --- | --- | --- | --- |
help | -h | python3 backup-file-prune.py -h | Displays the help context for each optional flag.
searchpath | -s | python3 backup-file-prune.py -s /var/backups/firewalls/ | Absolute or relative directory path where configuration files reside. If omitted, the current working directory is used.
days | -d | python3 backup-file-prune.py -s /var/backups/switches/ -d 40 | Specifies how many days back to search for configuration backup files. Range is between 0 (same-day) and 90 days. Default is 7 days.
execute | -x | python3 backup-file-prune.py -s /var/backups/switches/ -d 40 -x -p /var/backups/pruned/ | This option must be specified to execute the script action of pruning the configuration files; otherwise, script will only run as a check and take no action. If this option is specified, it must be done alongside the option to either prune (move) or remove (delete) the redundant files.
prunepath | -p | python3 backup-file-prune.py -s /var/backups/switches/ -p /var/backups/pruned/ -x | Absolute or relative directory path where pruned configuration files will be moved into. If this option is specified, it must be accompanied by the execute option/flag. If the execute flag is omitted or the prune path is invalid/inaccessible, then the script will run in check-only mode.
remove | -r | python3 backup-file-prune.py -s /var/backups/firewalls/ -r -x | Configures the script to delete the redundant files. No further prompt is given. It's recommended to run the script in check-only mode first. If this option is specified, it must be accompanied by the execute option/flag or the script will run in check-only mode.
verbose | -v | python3 backup-file-prune.py -s /var/backups/firewalls/ -p /var/backups/pruned/ -x -v | Increase script verbosity. Default is false.

# Issues

If you found this useful but have bugs to report or feature requests you'd like to see added, feel free to submit an issue.
