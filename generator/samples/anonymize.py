##
# anonymize.py
#
# Relabel serial numbers in sample data.
#
# by Danial Ebling (danial@uen.org)
##
import csv
import os
import sys
import string
import random

TAGS = ["source", "name"]
# fake serials have "RDM" at the beginning
new_serial = lambda k: 'RDM' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=(k - 3)))

def main():
    files = os.listdir(sys.path[0])
    for file in files:
        
        if not file.endswith('.csv'):
            continue

        serials = {}
        new_entries = []
        fieldnames = None
        with open(os.path.join(sys.path[0], file), 'r') as csvf:
            entries = csv.DictReader(csvf)
            fieldnames = entries.fieldnames
            serial_keys = [k for k in fieldnames if 'serial' in k]
            if not serial_keys:
                # skip if there's no sensitive data to replace
                continue

            print(f"opening {file}")
            for entry in entries:
                entry_id = tuple([entry[i] for i in TAGS])
                for key in serial_keys:
                    if entry[key].lower() == 'null':
                        # skip null entries
                        continue
                    if not serials.get(entry_id):
                        # make a unique hash for the entry based on tags
                        serials[entry_id] = new_serial(len(entry[key]))

                    # rewrite with the randomized serial number
                    entry[key] = serials[entry_id]
                new_entries.append(entry)
        
        with open(os.path.join(sys.path[0], file), 'w') as csvf:
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(new_entries)
            print(f"{file} anonymized")

if __name__ == '__main__':
    main()