#!/usr/bin/env python
"""Utility script to convert a .npz MIRT model to JSON.

Currently the MIRT training outputs data as a npz (NumPy) file.  This
script can convert it to JSON suitable for uploading to App Engine via
mirt_upload.py.

USAGE:

  python mirt_npz_to_json.py NPZFILE >out.json

The program will prompt for input on stderr, to avoid conflicting with
the written JSON on stdout.

TODO(jace): make the MIRT training output JSON and eliminate this script

"""

import json
import numpy
import os
import sys

sys.path.append(os.path.dirname(__file__) + '../../stable')


def mirt_npz_to_json(npz_file, outfile=None, slug=None, title=None,
                     description=None):
    model = numpy.load(npz_file)

    theta = model["theta"][()]
    exercise_ind_dict = model["exercise_ind_dict"][()]

    out_data = {
        "engine_class": "MIRTEngine",

        # MIRT specific data
        "params": {
            "exercise_ind_dict": exercise_ind_dict,
            "theta_flat": theta.flat().tolist(),
            "num_abilities": theta.num_abilities,
            "max_length": 15,
            "max_time_taken": int(model["max_time_taken"]),
        }}

    while not slug:
        print >>sys.stderr, "Enter the slug (required): ",
        slug = raw_input()

    if not title:
        print >>sys.stderr, ("Title can be left blank if you will be updating "
                             "an existing model.")
        print >>sys.stderr, "Enter the title (or hit enter for none): ",
        title = raw_input()

    if not description:
        print >>sys.stderr, ("Description can be left blank if you will be "
                             "updating an existing model.")
        print >>sys.stderr, "Enter the description (or hit enter for none): ",
        description = raw_input()

    if slug:
        out_data["slug"] = slug
    if title:
        out_data["title"] = title
    if description:
        out_data["description"] = description

    json_data = json.dumps(out_data, indent=4)

    if outfile:
        f = open(outfile, 'w')
        f.write(json_data)
    else:
        print json_data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit("Usage: %s input_filename" % sys.argv[0])

    filename = sys.argv[1]

    mirt_npz_to_json(filename)
