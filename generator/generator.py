##
# generator.py
#
# Read CSVs containing metric samples, and send them to a GRPC server in the same
# manner that IOS-XE 17+ does.
#
# by Danial Ebling (danial@uen.org)
##
import argparse
import csv
import grpc
import gzip
import logging
import os
import re
import signal
import sys
import threading
import time
import traceback

from collections.abc import Iterator

sys.path.insert(0, os.path.join(sys.path[0], 'cisco_proto'))
import mdt_grpc_dialout_pb2_grpc
import mdt_grpc_dialout_pb2
import telemetry_pb2

TAGS = ["host", "source", "subscription", "path", "name"]
DESTINATIONS = [
    "localhost:57500",
    ]
# number of destinations for range mode
NUM_DESTINATIONS = 20
RETRY_SECONDS = 30

class MetricsGenerator(object):
    start_time = None
    csvreader = None
    csvlines = []
    send_index = 0
    last_index = 0
    filename = None
    destination = None
    thread = None
    stop_thread = threading.Event()
    header = []

    def __init__(self, filename, destination):
        self.filename = filename
        self.destination = destination
        self.csvreader = self.read_csv(filename)

    def read_csv(self, filename) -> Iterator[dict]:
        with (gzip.open(filename, 'rt') if filename.endswith('.gz') else open(filename, 'rt')) as csvf:
            reader = csv.DictReader(csvf)
            while True:
                next(reader) # skip header
                for line in reader:
                    yield line
                csvf.seek(0) # EOF, start over

    @staticmethod
    def _translate_field(name, value):
        field = telemetry_pb2.TelemetryField(name=name)
        if name.endswith('vendor_rev') or name.endswith('version'):
            # version field overrides, they can look like ints sometimes
            field.string_value = value
        elif value.isdigit():
            if any(name.endswith(n) for n in ['min', 'max', 'avg', 'instant']):
                # override for optics values - sometimes they are formatted as integers
                field.double_value = float(value)
            else:
                # regular integer
                field.uint64_value = int(value)
        elif value.replace('-', '').isdigit():
            # negative integer is (almost) always a double
            field.double_value = float(value)
        elif re.match(r'^-?\d+\.\d+$', value):
            # double value
            field.double_value = float(value)
        elif value == 'true' or value == 'false':
            # boolean
            field.bool_value = (value == 'true')
        else:
            # catch-all, string
            field.string_value = value
        return field

    def generate_messages(self) -> Iterator[mdt_grpc_dialout_pb2.MdtDialoutArgs]:
        def _recurse(field, key, value):
            if '/' in key:
                # split and recurse
                split = key.split('/', 1)
                # check to see if field.fields contain this name already
                appended = False
                for _f in field.fields:
                    if _f.name == split[0]:
                        # TelemetryField matches, append to that one
                        _recurse(_f, split[1], value)
                        appended = True
                if not appended:
                    # make a new TelemetryField
                    tf = telemetry_pb2.TelemetryField(name=split[0])
                    _recurse(tf, split[1], value)
                    field.fields.append(tf)
            else:
                # no further fields, make this a field and return
                field.fields.append(self._translate_field(key, value))

        prev_timestamp = None
        while not self.stop_thread.is_set():
            keyedline = next(self.csvreader)
            # Message details
            node = keyedline.get('source', "Unknown")
            subscription = keyedline.get('subscription', "0")
            metric_path = keyedline.get("path")
            collection_id = self.send_index
            # get time inside sample
            timestamp = int(keyedline.get('time'))

            # Additional tags
            tags = {}
            for tag in TAGS:
                if tag in keyedline.keys():
                    tags[tag] = keyedline[tag]

            # wait for next message according to timestamp
            if prev_timestamp and prev_timestamp != timestamp:
                sleep_to_next = (timestamp - prev_timestamp) / 1000000000
                self.stop_thread.wait(sleep_to_next)
            prev_timestamp = timestamp

            # overwrite timestamp so it's not stale data
            timestamp = int(time.time() * 1000)

            segment = telemetry_pb2.Telemetry()
            segment.node_id_str = node
            segment.subscription_id_str = subscription
            segment.encoding_path = metric_path
            segment.collection_id = collection_id
            segment.collection_start_time = timestamp
            segment.msg_timestamp = timestamp

            gpbkv = telemetry_pb2.TelemetryField(timestamp=timestamp)
            # keys (tags)
            keys = telemetry_pb2.TelemetryField(name="keys")
            for tag in tags:
                keys.fields.append(telemetry_pb2.TelemetryField(name=tag, string_value=tags[tag]))
            gpbkv.fields.append(keys)
            # content (values)
            content = telemetry_pb2.TelemetryField(name="content")

            # convert remaining keys into a structured path
            remaining_keys = set(keyedline.keys()) - set(['name', 'time'] + list(tags.keys()))
            for key in remaining_keys:
                _recurse(content, key, keyedline[key])

            gpbkv.fields.append(content)
            segment.data_gpbkv.append(gpbkv)

            # assemble GRPC message
            msg = mdt_grpc_dialout_pb2.MdtDialoutArgs(
                ReqId=self.send_index,
                data=segment.SerializeToString(deterministic=True))

            yield msg
            self.send_index += 1
        
        logging.info(f"Disconnected from {self.destination}")

    def send_grpc(self):
        successful_start = False
        while not successful_start and not self.stop_thread.is_set():
            with grpc.insecure_channel(self.destination) as channel:
                try:
                    stub = mdt_grpc_dialout_pb2_grpc.gRPCMdtDialoutStub(channel)
                    responses = stub.MdtDialout(self.generate_messages())
                    logging.info(f"Connecting to {self.destination}")
                    for r in responses:
                        # at this point we are sending GRPC messages
                        if self.stop_thread.is_set():
                            # this worked until stop was requested
                            successful_start = True
                            break
                except grpc._channel._MultiThreadedRendezvous as e:
                    if e.code() == grpc.StatusCode.UNAVAILABLE:
                        logging.error(
                            f"Failed to connect to {self.destination}, waiting {RETRY_SECONDS} seconds to retry...")
                        self.stop_thread.wait(RETRY_SECONDS)
                    else:
                        traceback.print_exc()
                        self.stop_thread.set()
                        break

    def run(self):
        if self.thread and not self.stop_thread.is_set():
            raise Exception("thread already running")
        self.thread = threading.Thread(target=self.send_grpc)
        self.thread.start()
        self.stop_thread.clear()

    def stop(self):
        logging.info("Shutting down...")
        self.stop_thread.set()

    def get(self):
        return self.send_index

    def get_sent(self):
        sent = self.send_index - self.last_index
        self.last_index = self.send_index
        return sent

class GeneratorCollection(object):
    files = [
        "cpu.csv.gz",
        "interfaces.csv.gz",
        "optics.csv.gz",
        "platform.csv.gz"]
    # shutdown is shared for all threads
    shutdown = threading.Event()

    def __init__(self, destination):
        self.generators = []
        
        self.destination = destination
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        for filename in self.files:
            self.generators.append(MetricsGenerator(os.path.join("samples", filename), destination))

    def run(self):
        for generator in self.generators:
            generator.run()

        while not self.shutdown.is_set():
            self.shutdown.wait(15)
            sent = 0
            for generator in self.generators:
                sent += generator.get_sent()
            logging.info(f"sent {sent} messages to {self.destination}")

    def stop(self, signum, frame):
        for generator in self.generators:
            generator.stop()
        self.shutdown.set()

def main(destinations):
    generatorcollections = []
    threads = []
    for destination in destinations:
        generatorcollections.append(GeneratorCollection(destination))
        threads.append(threading.Thread(target=generatorcollections[-1].run))
        threads[-1].start()

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s %(message)s', 
                        datefmt='%Y/%m/%d %H:%M:%S', level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog='generator.py', description='Metrics Generator')
    parser.add_argument('-r', '--range', help='use IP ranges instead of localhost', action='store_true')
    args = parser.parse_args()
    if args.range:
        DESTINATIONS = ["10.10.8.10:57500"]
        for i in range(10, 10+NUM_DESTINATIONS):
            DESTINATIONS.append(f"10.10.{i}.10:57500")
    main(DESTINATIONS)
