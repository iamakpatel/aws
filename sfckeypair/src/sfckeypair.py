#!/usr/bin/env python
#
#------------------------------------------------------------------------#
# This program will generate keypair for snowflake keypair authentication
# for users.
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
#
# Author: Ashish Patel
# Created on: 28/04/2021
# Version: 1.1
# Ownership: For changes contact Snowflake Admins
#------------------------------------------------------------------------#

import os,sys,json, base64
import requests
import socket,getpass,subprocess

API_ENDPOINT = "https://ddhtok8wla.execute-api.us-east-1.amazonaws.com/np"

homedir=os.environ['HOME']
userid=os.environ['USER']
hostname=socket.gethostname()
#client_key=os.getenv('SFC_KEYPAIR_CLIENT_KEY', None)

keyfile="rsa_snow.p8"
pubfile="rsa_snow.pub"

headers = {
    "content-type": "application/json"
}
def upd_key(**key):
  if sys.version_info[0] < 3:
      raise Exception("** Need Python Version 3 or higher to run this utility ***")

  snowenv = key['snowenv']
  pphrase = key['pphrase']
  kticket = key['kticket']
  account_type = key['account_type']

  snowdir = homedir + "/.snowflake/"
  confdir = snowdir + snowenv + "/"
  keyfilepath = confdir + keyfile
  pubfilepath = confdir + pubfile

  try:
    #if client_key == None:
    #    raise Exception("Client key is not valid or not setup\nPlease contact Snowflake Admin[SnowflakeSupport@thehartford.com]")
    print("Creating Keypair!! Please wait...")
    headers['username'] = userid
    headers['kticket'] = kticket
    headers['account_type'] = account_type
    #headers['x-api-key'] = base64.b64decode(client_key.encode('utf-8')).decode('utf-8')
    payload=f'"dbenv": "{snowenv}", "userid": "{userid}", "hostname": "{hostname}", "pphrase":"{pphrase}","account_type":"{account_type}"'
    response = requests.post(url = API_ENDPOINT + "/keypair", data = "{" +payload+ "}", headers=headers)
    response_json = json.loads(response.text)
    if response.status_code != 200:
        raise Exception(response_json['message'])
    body = json.loads(response_json["body"])
    if body['message'] != "SUCCESS":
        raise Exception(body['message'])
    if not os.path.exists(confdir):
      os.makedirs(confdir, 0o750)
    public_key = body['public_key']
    private_key = body['private_key']

    file_out = open(keyfilepath, "wb")
    file_out.write(private_key.encode('utf-8'))

    file_out = open(pubfilepath, "wb")
    file_out.write(public_key.encode('utf-8'))

    print(f"Keypair is created in path->|{homedir}/.snowflake/{snowenv}|")
  except Exception as e:
    print("FAILED!!")
    print(e)

def main():
  arg_len = len(sys.argv)
  if arg_len == 1:
      #password = base64.b64encode(getpass.getpass(f'Enter password for {userid}:').encode('utf-8'))
      command = "klist | grep Ticket"
      process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      process.wait()
      if process.returncode != 0:
        print("No kerberos setup available")
        sys.exit()
      out, err = process.communicate()
      ticket_file=out.decode("utf-8").split(':')[2].strip()
      with open(ticket_file, mode='rb') as file: # b is important -> binary
        fileContent = file.read()
      ticket_enc=base64.b64encode(fileContent)
      print("\n !Enterprise Data Office!")
      print ("##++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++##")
      print ("# Please choose the environment you wish you register your key #")
      print ("# ------------------------------------------------------------ #")
      print ("#                                                              #")
      print ("#    Choose \"1\" for Snowflake Lab Account                      #")
      print ("#           \"2\" for Snowflake Non-Prod Account                 #")
      print ("#           \"3\" for Snowflake Prod Account                     #")
      print ("#                                                              #")
      print ("##+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#")
      dbenv = int(input ("\n\nEnter 1 or 2 or 3 for your environment: "))
      if dbenv == 1:
        print ("\nConnecting to Snowflake - Lab Account")
        snowenv="lab"
      elif dbenv == 2:
        print ("\nConnecting to Snowflake - Non Prod Account")
        snowenv="nonprod"
      elif dbenv == 3:
        print ("\nConnecting to Snowflake - Prod Account")
        snowenv="prod"
      else:
        print ("\nIncorrect choice of environment. Please try again")
        quit()
      pphrase = getpass.getpass('\nEnter Passphrase for your snowflake keypair:')
      run = upd_key(snowenv=snowenv, kticket=ticket_enc, pphrase=pphrase, account_type="Users-E")
  elif arg_len == 3:
    dbenv = int(sys.argv[1])
    pphrase = sys.argv[2]
    if dbenv == 1:
      print ("\nConnecting to Snowflake - Lab Account")
      snowenv="lab"
    elif dbenv == 2:
      print ("\nConnecting to Snowflake - Non Prod Account")
      snowenv="nonprod"
    elif dbenv == 3:
      print ("\nConnecting to Snowflake - Prod Account")
      snowenv="prod"
    else:
      print ("\nIncorrect choice of environment. Please try again")
      quit()
    try:
        keytab="/etc/security/keytabs/%s.keytab" % userid
        with open(keytab, mode='rb') as file:
            file_content = base64.b64encode(file.read())
        run = upd_key(snowenv=snowenv, password=file_content, pphrase=pphrase, account_type="Service-Accounts")
    except subprocess.CalledProcessError as e:
        print(e)
  else:
    print("ERROR: Either provide 2 arguments(dbenv, pphrase) or None")

if __name__ == "__main__":
    main()
