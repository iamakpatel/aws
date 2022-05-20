import json, boto3
import time
import logging
import snowflake.connector
from Crypto.PublicKey import RSA
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def handler(event, context):
    dbenv=event["dbenv"]
    userid=event["userid"]
    pphrase=event["pphrase"]
    hostname=event["hostname"]

    status_code=200
    body={        
        "message": "SUCCESS"
    }
    try:        #Make Passphrase mandatory
        if pphrase == None or pphrase == "":
            raise Exception("Passphrase is mandatory")
        #Generate Keypair
        key = RSA.generate(2048)
        private_key = key.export_key(format='PEM', passphrase=pphrase, pkcs=8, protection='PBKDF2WithHMAC-SHA1AndAES256-CBC').decode("utf-8")
        public_key = key.publickey().export_key().decode("utf-8")

        LOGGER.info(f'Keypair Created Successfully! Updating New Key in Snowflake Database.')

        #Get secret from secret manager
        secret = get_secret(dbenv)
        if secret == None:
            raise Exception(f"db-credentials are not setup in secret manager for {dbenv}")

        #Initiate Snowflake connection
        ctx = snowflake.connector.connect(
           user=secret['user'],
           password=secret['password'],
           account=secret['account'],
           warehouse=secret['warehouse'],
           database=secret['database'],
           schema=secret['schema'],
           role=secret['role']
           )

        LOGGER.info(f"Connection was successfull!")

        #Prepare for Audit
        pubkey = ""
        for line in public_key.split("\n"):
            if line == "-----BEGIN PUBLIC KEY-----" or line == "-----END PUBLIC KEY-----":
                continue
            pubkey = pubkey + line

        if pubkey == None or pubkey == "":
            raise Exception(f"Public key is not create due to some technical issue. Please contact Snowflake Support.")

        #Start Audit
        #TODO: KeyRotation is to be implemented
        if userid[len(userid) -1] == 'e':
            logonid = userid[:-1]
        else:
            logonid = userid
        cs = ctx.cursor()
        str1 = "select KEY_ORIGIN_SERVER,RSA_PUBLIC_KEY_SET_TIME from SFC_KEYPAIR_STATUS where USERID=upper('" + userid + "')"
        row = cs.execute(str1).fetchone()
        if row != None:
            col1, col2 = cs.execute(str1).fetchone()
            LOGGER.info(f"Previous Key generated for the user={logonid} is from {col1}, on {col2}")
        str2 = "Alter user " + logonid + " set rsa_public_key='" + pubkey + "'"
        cs.execute(str2)
        LOGGER.info(f"New key is added and session is active={logonid}")
        str3 = "merge into SFC_KEYPAIR_STATUS as tgt_tbl using dual on tgt_tbl.login_name= upper('" + logonid + "') when matched then update set RSA_PUBLIC_KEY_SET_TIME=current_timestamp(), RSA_PUBLIC_KEY_EXPIRE_TIME=DATEADD(day ,1, current_timestamp()),KEY_STATUS='ACTIVE' when not matched then insert values (upper('" + logonid + "'),upper('" + userid + "'),'USER',upper('" + hostname + "'),current_timestamp(),DATEADD(day ,1, current_timestamp()) ,'ACTIVE',CURRENT_TIMESTAMP())"
        cs.execute(str3)
        str4 = "insert into SFC_KEYPAIR_LOG(LOGIN_NAME,USERID,ACCOUNT_TYPE,KEY_ORIGIN_SERVER,RSA_PUBLIC_KEY_SET_TIME,RSA_PUBLIC_KEY_EXPIRE_TIME,KEY_STATUS,LAST_ACCESSED) values (upper('" + logonid + "'),upper('" + userid + "'),'USER',upper('" + hostname + "'),current_timestamp(),DATEADD(day ,1, current_timestamp()) ,'ACTIVE',CURRENT_TIMESTAMP())"
        cs.execute(str4)
        LOGGER.info(f"Audit is completed")
        body['public_key'] = public_key
        body['private_key'] = private_key
        cs.close()
        ctx.close()
    except Exception as e:
        LOGGER.info(e)
        status_code=400
        body["message"]=str(e)
        LOGGER.info(f'ERROR-> {body["message"]}')
    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body)
    }

def get_secret(dbenv):
    secret_name = "hig/edo/secure/snowflake/"+dbenv+"/db-credentials"
    region_name = "us-east-1"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    secret = None
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        LOGGER.info(e)
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
    if secret == None:
        return None
    else:
        return json.loads(secret)
