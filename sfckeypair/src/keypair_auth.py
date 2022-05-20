import ldap, base64, boto3, json
import logging
import subprocess, sys, os

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def handler(event, context):
    effect = "Deny"
    LDAP_SERVER = 'ldap://10.220.132.141'
    base_dn = 'DC=ad1,DC=prod'
    AD_GROUP = "GPO-APP-4304-NonProdDev-Unix-RG"
    AD_GROUP_FILTER = '(&(objectClass=GROUP)(cn=%s))' % AD_GROUP
    try:
        #1 Validation of kerberos ticket
        kticket = event['headers']['kticket']
        username = event['headers']['username']
        kticket_file=f'/root/{username}.krb'
        with open(kticket_file, mode='wb') as file:
            file.write(base64.b64decode(kticket))
        
        command = f'klist -c {kticket_file}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        if process.returncode != 0:
            LOGGER.info(f'Ticket is not validated for user |{username}|')
            raise Exception(f'Ticket is not validated for user |{username}|')
        
        #2 Validating user whether it part of AD Group
        ldap_client = ldap.initialize(LDAP_SERVER)
        ldap_client.set_option(ldap.OPT_REFERRALS,0)
        members = ldap_client.search_s(base_dn, ldap.SCOPE_SUBTREE, AD_GROUP_FILTER)[0][1]['member']
        
        is_found = False
        for member in members:
            if is_found == True:
                break
            member_i = member.decode('utf-8').split(',')
            for item in member_i:
                item_s = item.split('=')
                if item_s[0] == 'CN':
                    if item_s[1].upper() == username.upper():
                        is_found = True
                        break
        if is_found == True:
            effect = "Allow"
            LOGGER.info(f"Request is succesfully authorized for user={username}")
        else:
            LOGGER.info(f"Request is NOT authorized for user={username}, Check whether user is part of AD Group={AD_GROUP}")
        ldap_client.unbind()
        
    except Exception as e:
        LOGGER.info(e)
    return {
        "principalId": "user",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": event['methodArn']
            }]
        }
    }
