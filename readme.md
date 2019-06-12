A DNS Load Balancer for Qumulo Core.

Summary
-------------------------
This project will:

    * Present as a DNS server at which you can delegate hostnames 
    
    * Communicate with a Qumulo cluster via API, and return floating IPs for
        node with the lowest connection count.

It will NOT currently:

    * Support IPv6 floating IPs
    
    * Cache any information from the Qumulo Cluster
    
    * Use any sort of API connection pooling. We'll make several API requests
        per client lookup. These are typically only done at mount/connect
        time, so you will get away with it to an undefined scale.


Docker
--------------------------

If you wish to use docker (This is the easiest way)

    * We require docker compose 1.6 or newer for this container.
    
    * Tested with docker 1.12.1 and docker compose 1.8.1.
    

Start by making a copy of template.docker-env to .env in the source directory.

Launch the configured server as a daemon with: 

    $ docker-compose up -d
    

You can view the output of the service with:

    $ docker-compose logs -f



DNS Delegation
----------------------------

For a simple example, if you will have clients mounting
qumulocluster.grumpquat.com, you will need a delegation and glue record. A
short example in bind zone format would be something like:

$ORIGIN grumpquat.com.

qumulocluster   IN  NS     qumulodns1

qumulodns1      IN  A      10.100.247.76


Multiple delegations may be made, but remember to add the additional names as
Service Principal Names if you are using SMB.


