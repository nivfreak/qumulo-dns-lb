FROM python:2-onbuild

EXPOSE 53

CMD python qlb.py --ip ${IP} -u ${USER} -p ${PASSWORD} --dnsname ${DNSNAMES} --vlan-id ${VLANID}


