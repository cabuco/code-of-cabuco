Why is this needed?
Offboarding will transfer ownership of GDrive after 90 days.
If a manager wants access before then, we only want them to be able to make a copy.
Before, we would provide view only access and tell them to make copies of individual files they need.
This is problematic should the manager want to make copies in bulk as view does not allow copies of folders.
To remedy this, we will instead make copies of the offboarded user's GDrive, place them into one folder, and then transfer recursive ownership of that folder to the manager.
The manager will then have a complete copy of the offboarded user's GDrive accessible in one folder
This allows for the data to remain intact when the GDrive data for the offboarded user is utlimately transferred to IT's service account for permanent original storage.
It also solves for the annoyance of having to explain to a manager how to access view files via a drive search that will be useless should the manager have multiple reports 
offboarded as the search query relies upon searching for the offboarded user's username, which would become the service account and be difficult to differentiate.

Identify your source Google Account
Identify your destination Google Account

Start by creating a new folder in the source's GDrive and retrive the TRANSFER_ID using this GAM command

gam user source@domain.com create drivefile drivefilename "source-mydrive" mimetype gfolder

Output will look something like: 

Full Fidelity Recursive copy of source's MyDrive

gam user source@domain.com copy drivefile "root" recursive parentid "TRANSFER_ID"

Add the destination/newOwner as editor to all files within the transfer folder:

gam user source@domain.com add drivefileacl "TRANSFER_ID" user target@domain.com role writer

Create the sheet that contains GDrive file ID info for all flies in the Transfer Folder named: "source-mydrive"

gam user source@domain.com print filetree select TRANSFER_ID fields id,mimetype,parents todrive

You should have headers in this order A-G: User, index, name, id, mimeType, parents in the sheet. In H2, paste the formula below to transfer ownership of all the files/folders in the transfer folder.

= "gam user source@domain.com add drivefileacl """ & E2 & """ user target@domain.com role owner"

Now that the transfer is complete, we need to make the transfer folder visible in the destination's MyDrive. Run the following command:

Identify the parent folder with this command:

gam user target@domain.com info drivefile "TRANSFER_ID"

Then make target@domain.com the new owner of that top level folder "transfer"

gam user source@domain.com add drivefileacl "TRANSFER_ID" user target@domain.com role owner

Then move it to the target's mydrive

gam user target@domain.com update drivefile "TRANSFER_ID" addparent root

