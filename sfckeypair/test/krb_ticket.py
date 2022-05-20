import base64, subprocess, sys, os

command = "klist | grep Ticket"
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
process.wait()

if process.returncode != 0:
    print("Ticket Not Found")
    sys.exit()
out, err = process.communicate()
ticket_file=out.decode("utf-8").split(':')[2].strip()
#fileName='/tmp/krb5cc_0'
with open(ticket_file, mode='rb') as file: # b is important -> binary
    fileContent = file.read()

ticket_enc=base64.b64encode(fileContent)
temp_file="/root/CO26853.krb"

with open(temp_file, mode='wb') as file:
    file.write(base64.b64decode(ticket_enc))
command = f'klist -c {temp_file}'
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
process.wait()
if process.returncode != 0:
    print("Ticket Validation Failed")
    sys.exit()

if os.path.exists(temp_file):
    os.remove(temp_file)

print("Kerberos Ticket Validated Successfully...")
