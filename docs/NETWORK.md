# Network Configuration

Network configuration is glossed over in the workshop because of physical constraints (network devices, connection/session limits on IOS-XE, etc.). Fortunately, this document can get you most of the way to enabling streaming telemetry on your hardware.

## Cisco IOS-XE

Prerequisites:
- Cisco Catalyst 9000 series (in production at UEN and UTN: 9200, 9300, 9500, 9600)
- IOS-XE 17.3 or greater - recommended 17.9 or greater for stability reasons
- Some sort of in-band management - a loopback with an IP or SVI is ideal

### Step 1. Set up Streaming Telemetry
Make sure your software stack is up and running before sending metrics from your gear! This way, you'll see a GRPC session establish as soon as the configuration is done on the network side.

### Step 2. Configure the switch/router
Enter config mode
```
R02-9200#conf t
Enter configuration commands, one per line.  End with CNTL/Z.
R02-9200(config)#
```
Enable NETCONF-YANG
```
R02-9200(config)# netconf-yang
```
Configure an access list - make sure your device can't be inadvertently accessed or configured. Make sure you substitute your streaming telemetry server's IP!
```
ip access-list standard netconf_block
 5 permit <Streaming Telemetry IP>
 10 deny any
netconf-yang ssh ipv4 access-list name netconf_block
restconf ipv4 access-list name netconf_block
```

Configure subscriptions - A subscription looks something like this:
```
telemetry ietf subscription 20
 encoding encode-kvgpb
 filter xpath /oc-platform:components/component/cpu/oc-cpu:utilization
 source-address 10.20.30.40
 stream yang-push
 update-policy periodic 30000
 receiver ip address 10.254.253.252 57500 protocol grpc-tcp
```
Step by step:
- `telemetry ietf subscription 20` - sets a subscription up on ID #20.
- `encoding encode-kvgpb` - sets the encoding to self-described key-value pairs.
- `filter xpath /oc-platform:components/component/cpu/oc-cpu:utilization` - sets the path (metric) of what you want to see reported. In this case, it uses the openconfig platform CPU utilization.
- `source-address 10.20.30.40` - send from this IP address. This should match an existing Layer 3 interface (Loopback or SVI preferred, otherwise metrics could stop if an interface goes down).
- `stream yang-push` - push metrics instead of waiting for a client to request them.
- `update-policy periodic 30000` - push metrics on this cadence, in 100s of milliseconds. In this case, `30000` means 300 seconds = once every 5 minutes.
- `receiver ip address 10.254.253.252 57500 protocol grpc-tcp` - determines where metrics should go. In this case, `10.254.253.252` is the streaming telemetry server IP, `57500` is the port to send to, and `protocol grpc-tcp` sets the protocol to GRPC over TCP.

You must set one subscription per metric - even if all the other configurations are identical!

### Step 3. 
Wait - it typically takes 10s of seconds to a minute before an Catalyst 9000 starts sending metrics. Just be patient and watch your graphs.

### Example configuration
These metrics are what the simulated metrics were generated from - if you want to copy what you saw in the workshop, feel free to use this configuration to start:
```
telemetry ietf subscription 20
 encoding encode-kvgpb
 filter xpath /oc-platform:components/component/cpu/oc-cpu:utilization
 source-address <source IP>
 stream yang-push
 update-policy periodic 30000
 receiver ip address <Telemetry IP> 57500 protocol grpc-tcp
telemetry ietf subscription 21
 encoding encode-kvgpb
 filter xpath /oc-if:interfaces/interface/state
 source-address <source IP>
 stream yang-push
 update-policy periodic 6000
 receiver ip address <Telemetry IP> 57500 protocol grpc-tcp
telemetry ietf subscription 22
 encoding encode-kvgpb
 filter xpath /oc-platform:components/component/oc-transceiver:transceiver
 source-address <source IP>
 stream yang-push
 update-policy periodic 6000
 receiver ip address <Telemetry IP> 57500 protocol grpc-tcp
telemetry ietf subscription 23
 encoding encode-kvgpb
 filter xpath /oc-platform:components/component/state
 source-address <source IP>
 stream yang-push
 update-policy periodic 30000
 receiver ip address <Telemetry IP> 57500 protocol grpc-tcp
```

### Where do I find more metric paths?
The hard way: you can find ALL supported metrics, by IOS-XE version, here: [https://github.com/YangModels/yang/tree/main/vendor/cisco/xe](https://github.com/YangModels/yang/tree/main/vendor/cisco/xe)

The easier way: For IOS-XR, there is now a Feature Navigator available that lets you explore the object model: [https://cfnng.cisco.com/ios-xr/yang-explorer/view-data-model](https://cfnng.cisco.com/ios-xr/yang-explorer/view-data-model)

For IOS-XE, browsing the OpenConfig schema docs is a good way to find what you're looking for: [https://openconfig.net/projects/models/schemadocs/](https://openconfig.net/projects/models/schemadocs/)