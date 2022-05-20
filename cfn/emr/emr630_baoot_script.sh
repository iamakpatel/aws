#!/bin/bash
#
# make some installs 
#
# sudo yum -y install amazon-efs-utils 
# sudo mkdir /mnt/appdata
# echo "172.23.40.243 fs-346364c1.efs.us-east-1.amazonaws.com" | sudo tee -a /etc/hosts
# sudo mount -t efs -o tls,iam fs-346364c1:/ /mnt/appdata
# sudo ln -s /mnt/appdata /data
# sudo ln -fs /data/app/oracle/*.jar /usr/lib/sqoop/lib
# sudo ln -fs /mnt/appdata/app /usr

#
# Next set of instructions
# sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config_bkp
# sudo sed -i '0,/PasswordAuthentication no/s//PasswordAuthentication yes/' /etc/ssh/sshd_config
# sudo service sshd restart

sudo mkdir -p /usr/app/build
#sudo chown -R hadoop /usr/app
sudo chmod -R 755 /usr/app/
echo "Folder for /usr/app/build created"

# Log4J Patch script
sudo mkdir -p /usr/app/build/log4j
sudo aws s3 cp s3://edo-np-hub-s3-edoce-artifacts/security/log4j/patch-log4j-emr-6.3.1-v1.sh /usr/app/build/log4j
sudo chmod -R 755 /usr/app/build/log4j
ls /usr/app/build/log4j
sudo /usr/app/build/log4j/patch-log4j-emr-6.3.1-v1.sh
echo "Log4j Patch applied"

# Additional Python packages for Snowflake connectivity - Git Ticket#184
# for Python 3.7
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install --upgrade wheel
sudo python3 -m pip install --upgrade snowflake-connector-python
sudo python3 -m pip install --upgrade openpyxl
sudo python3 -m pip install --upgrade pytz
sudo python3 -m pip install --upgrade pyyaml
sudo python3 -m pip install --upgrade boto3
sudo python3 -m pip install --upgrade cryptography
sudo python3 -m pip install --upgrade pandas
sudo python3 -m pip install --upgrade pandasql
sudo python3 -m pip install --upgrade azure-common==1.1.27
sudo python3 -m pip install --upgrade azure-core==1.19.0
sudo python3 -m pip install --upgrade azure-storage-blob==12.9.0
sudo rm -rf /usr/local/lib64/python3.7/site-packages/numpy-1.16.5-py3.7.egg-info
sudo rm -rf /usr/local/lib64/python3.7/site-packages/numpy
sudo python3 -m pip install --upgrade numpy==1.21.4

# Replace the correct anaconda_3 software and associated packages
AWS_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
env_type=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$AWS_INSTANCE_ID" "Name=key,Values=hig-environment-type" | jq -r '.Tags[0] | .Value')
echo $AWS_INSTANCE_ID
echo $env_type
if [ "$env_type" = "PROD" ]
then
  sudo aws s3 cp s3://edo-np-hub-s3-edoce-binaries/emr/installs/usrapp/prod/anaconda3610.tar.gz /usr/app/
  cd /usr/app
  sudo mv anaconda_3 anaconda_3_obsolete
  sudo tar -xzf anaconda3610.tar.gz
  sudo chmod 755 anaconda_3
  cd -
fi

#
# quantexa setup
#
# sudo adduser rs92906e
# sudo adduser bs96398e
# sudo adduser ac12882e
# echo 'rs92906e:transient#123' | sudo chpasswd 
# echo 'bs96398e:transient#123' | sudo chpasswd 
# echo 'ac12882e:transient#123' | sudo chpasswd 
# echo "rs92906e, bs96398e, ac12882e ALL=(ALL) ALL" >> /etc/sudoers

#RDS Maria DB connector Issues - fix Aws Support Case - 8397808661(np-bd)
# sudo rm -f /usr/share/java/mariadb-connector-java.jar
# sudo cp -f /etc/sqoop/conf/mariadb-java-client-2.2.6.jar /usr/share/java/
# sudo ln -s /usr/share/java/mariadb-java-client-2.2.6.jar /usr/share/java/mariadb-connector-java.jar
# sudo chmod 644 /usr/share/java/mariadb-java-client-2.2.6.jar
# sudo systemctl restart hive-hcatalog-server
# sudo ln -s /var/usr/lib/phoenix/bin/sqlline.py /usr/bin/phoenix-sqlline

#EMR Presto Issues Fix AWS Support Case - 8460182681(np-bd)
sudo sed -i -e 's/http-server.http.enabled = false/http-server.http.enabled = true/g' /etc/presto/conf/config.properties
sudo systemctl restart presto-server

#CFN Parameters
#AdditionalGPOs=${1}
#AnsibleEnvironment=${2}
#AutoSysFlag=${3}
#Envname=${4}

AdditionalGPOs="GPO-APP-4304-NonProdDev-Unix-Filter"
AnsibleEnvironment="qa"
AutoSysFlag="no"
Envname="NONPROD"

#echo "AdditionalGPOs=${1}"
#echo "AnsibleEnvironment=${2}"
#echo "AutoSysFlag=${3}"
#echo "Envname=${4}"

#
#ansible instructions
#
AWS_AVAIL_ZONE=$(curl http://169.254.169.254/latest/meta-data/placement/availability-zone)
AWS_REGION="`echo \"$AWS_AVAIL_ZONE\" | sed 's/[a-z]$//'`"
AWS_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
AWS_HOST_NAME=$(curl http://169.254.169.254/latest/meta-data/hostname)
export REGION=${AWS::Region}
export HOSTNAME=${AWS_HOST_NAME}
export DOMAIN=thehartford.com
export FQDN=$HOSTNAME.$DOMAIN
export clusterid=`cat /mnt/var/lib/info/job-flow.json | jq -r ".jobFlowId"`

###
# Restart SSM agent
###
#sudo systemctl start amazon-ssm-agent
###
# Get the oauth token
###
#export key=`aws --region us-east-1 secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:622325239849:secret:ansible_dev-isCOX3 --query SecretString --output text| jq -r '.[]'`

retval=$?
###
# if the previous step fails, send a signal to fail the stack
###
if [ $retval -ne 0 ]; then
  /opt/aws/bin/cfn-signal -e $? --stack  ${AWS::StackName} --resource Ec2Instance --region ${AWS::Region}
  exit 
fi
AWS_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
echo $AWS_INSTANCE_ID
AWS_HOST_NAME=$(curl http://169.254.169.254/latest/meta-data/hostname)
APP_ID=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$AWS_INSTANCE_ID" "Name=key,Values=hig-billing" --query "Tags[*].{Value:Value}" --output text)
APP_NAME=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$AWS_INSTANCE_ID" "Name=key,Values=EDO-Appl-Nm" --query "Tags[*].{Value:Value}" --output text)
MASTER_INSTANCE_NAME="EMR-Master-"$APP_ID"-"$APP_NAME
CORE_INSTANCE_NAME="EMR-Core-"$APP_ID"-"$APP_NAME
echo $AWS_HOST_NAME
MasterNode=$(hostname -i)
export DOMAIN=thehartford.com
export FQDN=$HOSTNAME.$DOMAIN
echo $FQDN
vMaster=$(cat /var/aws/emr/userData.json | jq -r .isMaster)
if  [ "$vMaster" = "true" ] ; then
	export ip_address=`curl http://169.254.169.254/latest/meta-data/local-ipv4`
  if [ "$ip_address" = "" ]; then
    export ip_address="edonpbdemr213"
  fi
  StackName=`echo edo$ip_address | sed 's/\.//g'`
  # aws ssm start-automation-execution --document-name arn:aws:ssm:us-east-1:622325239849:document/SSMLinuxPostBuild-Test-SSMGoldLinuxBuild-FTG5WMWST74U --parameters "AutomationAssumeRole=arn:aws:iam::357555245473:role/AutomationServiceRole,InstanceId=$AWS_INSTANCE_ID,AdditionalGPOs=${AdditionalGPOs},AnsibleEnvironment=${AnsibleEnvironment},AutoSysFlag=${AutoSysFlag},Envname=${Envname},Inventory=85,OsType=linux,Snappid=APP-4304-${Envname},Region=us-east-1,StackName=${StackName},TagHIGAccountParameter=357555245473,WorkflowId=1031"
  aws ec2 create-tags --resources $AWS_INSTANCE_ID --tags Key=Hostname,Value=$StackName
  aws ec2 create-tags --resources $AWS_INSTANCE_ID --tags Key=Name,Value=$MASTER_INSTANCE_NAME
else
  aws ec2 create-tags --resources $AWS_INSTANCE_ID --tags Key=Name,Value=$CORE_INSTANCE_NAME
fi
exit 0
###
# call ansible to install Dynamic Sumo Install
###
#python3 /opt/hig/python_ec2.py -a ansibledev.thehartford.com -t install_sumo_dynamic -o $key -f lad1anshd2005.thehartford.com -j job_templates -n fqdn=$ip_address -n vm_unique_id=$clusterid

################# Pepperdata Install ################################

# Bob M  1:34 PM Thursday, February 24, 2022

getclustername() {
CLUSTERID=$(grep jobFlowId /var/lib/info/extraInstanceData.json|cut -d "\"" -f 4)
CLUSTERNAME=$(aws emr describe-cluster --cluster-id $CLUSTERID | grep -o '"Name": "[^"]*' | grep -o '[^"]*$'|head -1)
}

getclustername

S3_LOCATION=s3://edo-np-bd-emr-admin-001/hadoop-exports/pepperdata

aws s3 cp $S3_LOCATION/config/my-cluster/ $S3_LOCATION/config/thehartford-${CLUSTERNAME}/ --recursive
aws s3 cp $S3_LOCATION/install-packages/supervisor-6.5.25-H30_YARN3/emr/bootstrap .

chmod 755 bootstrap

./bootstrap -u thehartford-${CLUSTERNAME} -b $S3_LOCATION
