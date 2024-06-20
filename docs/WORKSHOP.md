# Running the Workshop

## Running on the provided resource

In case you don't have a Docker-ready machine available, a machine with SSH is made available.

Prerequisites on your computer:
- Wifi card
- SSH client
- Web browser - any modern one will do

### Connecting to the machine
1. Connect to the access point (please note you will not have internet access through this):
```
SSID: STWorkshop
Passphrase: grpcgrpc
```
2. SSH into `10.10.x.10`, where 'x' is your demo number. Use your demo username, for example demo user #8 will log in with:
```
ssh demo8@10.10.8.10
```
Your password will be the same as your username (insecure, I know!)

3. Enter the project directory:
```
cd techsummit-streaming-telemetry
```

## Running on your own machine

Feel free to run this project on your own device!
Please make sure you have the following installed:
- Web browser - any modern one will do
- [Docker](https://www.docker.com/get-started/) - this should also include Docker Compose
- [Python 3](https://www.python.org/downloads/) - this should also include pip

## Setting up & Starting the workshop

### 1. Download the project (Own machine only)

Clone the repository with git, and enter the project directory:
```
git clone https://github.com/danialre/techsummit-streaming-telemetry && cd techsummit-streaming-telemetry
```

### 1a. Install metrics generator requirements (Own machine only)

(Skip this step if you're using the provided server)
```
pip3 install -r generator/requirements.txt
```

### 1b. Change `docker-compose.yaml` (Own machine only)

(Skip this step if you're using the provided server)

Copy `docker-compose.self.yaml` to `docker-compose.yaml`, overwriting the existing file. This is because the default `docker-compose.yaml` uses an IP address tied to demo usernames.

### 2. Edit `docker-compose.yaml`

Before we start anything, there are a few variables that need to be set inside `docker-compose.yaml` in the main directory of this project.
In particular, make sure you set:
- `INFLUXDB_ADMIN_USER` (line 9) - "admin" is okay, this sets your InfluxDB administrator username.
- `INFLUXDB_ADMIN_PASSWORD` (line 10) - change this to another string. This is the password to access your InfluxDB database and all tables.

### 3. Start the Telemetry stack

Run `docker-compose up -d`. This should show some messages about pulling images, and then starting containers.

If everything worked, you can run `docker-compose ps` and you should see something similar to this:
```
      Name                  Command           State                         Ports
--------------------------------------------------------------------------------------------------------
demo10_grafana_1    /run.sh                   Up      10.10.10.10:3000->3000/tcp
demo10_influxdb_1   /entrypoint.sh influxd    Up      8086/tcp
demo10_telegraf_1   /entrypoint.sh telegraf   Up      10.10.10.10:57500->57000/tcp, 8092/udp, 8094/tcp,
                                                      8125/udp
```
This output is from demo user #10 in the above example, note the container names & IPs.

### 3a. Check logs

Run `docker-compose logs` to view container logs. To look at logs for a specific container or service, add the name to the end of the command.

For example, to watch Telegraf logs (to see if any network devices are connecting to the streaming telemetry system), run:
```
docker-compose logs -f telegraf
```
The `-f` parameter follows the output, so any new events show up immediately.

### 4. Log in to the web interface

Time to log into Grafana! If you remember step #3, the output of `docker-compose ps` showed a grafana container that is listening on port 3000. Try loading a page from this container into your web browser, replace 'x' with your demo number: 
[http://10.10.x.10:3000](http://10.10.x.10:3000)

If you're running this on your own machine, open it here:
[http://localhost:3000](http://localhost:3000)

Grafana's default credentials are `admin/admin`.

You may need to set up an admin password the first time you log in. Set this to whatever you like - it does not have to match the password field from step #2.

Once you're logged in, select the "Telemetry Stack" dashboard. This will show the health and activity of your streaming telemetry containers.

### 5. Start the metrics generator (Own machine only)

(Skip this step if you're using the provided server)

In a new terminal window/session, run the following:
```
cd generator
python3 generator.py
```

This will start a python script that injects streaming telemetry data into Telegraf. Even though it's not a physical network device, the script creates packets that look identical to real IOS-XE GRPC streams.

If successful, the output of the script should look like this:
```
2024/06/12 13:27:41 Connecting to localhost:57500
2024/06/12 13:27:41 Connecting to localhost:57500
2024/06/12 13:27:41 Connecting to localhost:57500
2024/06/12 13:27:41 Connecting to localhost:57500
2024/06/12 13:27:46 sent 264 messages to localhost:57500
2024/06/12 13:27:51 sent 0 messages to localhost:57500
2024/06/12 13:27:56 sent 2 messages to localhost:57500
2024/06/12 13:28:01 sent 0 messages to localhost:57500
2024/06/12 13:28:06 sent 35 messages to localhost:57500
```

After 30 seconds or so, switch to your browser and check Grafana. If you have the "Telemetry Stack" dashboard open from step #4, you should see some metrics gathered & written.

If you need to stop the generator, Ctrl-C will stop it right away.

### 6. Explore metrics

Poke around Grafana and see what kind of metrics you can find! There are some pre-built dashboards that show device health, interface statistics, and metrics recording.
