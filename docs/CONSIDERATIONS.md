# Considerations for a Production Installation
This software stack works great in a workshop environment, where it just needs to be stood up quickly on one machine. What are the additional steps to getting this ready for a production environment?

## Security
There needs to be much more done to make this a secure software product. Some items:
1. No plaintexting passwords! In the workshop, the admin username AND password is set inside the `docker-compose.yaml` file. This should be passed in through the environment, through a vault or secrets service, or passed through a container orchestration system.
2. Multiple database accounts inside InfluxDB. Ideally, there should be:
  - one admin account with full access, to be used for troubleshooting or data restores
  - one write-only account, that Telegraf knows so it can insert metrics into the database
  - one or more read-only accounts, to show data in Grafana or share data with other tools
3. Network access limits - ACLs and iptables rules.

## High Availability
This works great for now, but what if containers need to be upgraded? Or, what if the host OS needs to be restarted?

### HA for Ingestion
While more than one Telegraf instance can be stood up, a consideration of scalability is device support. On IOS-XR and JUNOS, multiple destinations are easy to configure on the network. However, for IOS-XE, adding a second Telegraf instance or server IP doubles the configuration lines and GRPC sessions on the router. A simple load balanced IP can work, but keep in mind that telemetry may be interrupted during failover since TCP sessions get restarted.

### HA for Database
InfluxDB Enterprise supports seamless clustering for on-prem installations, or a Cloud platform everyone else. However, if you're looking stay with a free or 100% open source solution, you'll have to manage your own cluster - that includes data reconciliation and backup/restores. Fortunately, Telegraf sends its data to InfluxDB over HTTP POST queries, so an `nginx` load balancer can be easy stood up in front of your databases. Another nice feature is that metrics can be inserted multiple times, without creating duplicate data or waste in storage use. Because of this, something as simple as copying all writes from Telegraf to each InfluxDB instance is feasable.

### HA for Grafana
Like InfluxDB, Grafana has a Cloud offering as well as an Enterprise edition. Grafana supports using external databases for its dashboard and user configurations (MySQL, Postgres, etc.), and in our experience multiple instances play nicely with each other. Of course, for your users' sake a load balancer is a must for high availability.
