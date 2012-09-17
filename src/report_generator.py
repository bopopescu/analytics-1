#!/usr/bin/env python
""" A script to wrap all the steps for running regular reports, including
    1. Waiting for data partitions
    2. Kick off EMR jobs and wait for completion
    3. Kick off report importer to load data from Hive to MongoDB
Example: ./report_generator.py -c ../cfg/daily_report.json '<dt>=2012-08-25'
"""

USAGE = """%prog [options] [parameters]

Read the config file, wait for data, submit hive steps,
wait for the completion and then import the result from
hive to mongodb.
The parameters have the format of <key>=<value>. It will replece <key> with
<value> in the config file
"""


import datetime
import json
import optparse
import subprocess
import sys
import time

import boto

import boto_util
import emr
import hive_mysql_connector
import notify
import util


g_logger = util.get_logger()


def parse_command_line_args():
    parser = optparse.OptionParser(USAGE)
    parser.add_option("-c", "--config", help="Config file. REQUIRED")
    parser.add_option("-m", "--hive_masternode", default="ka-hive",
                       help="Hive master node alias")
    parser.add_option("-w", "--max_wait", type="float", default=12.0,
                       help="Max # hours we will wait for the data")
    parser.add_option("-s", '--ssh_keyfile',
        help=('A location of an SSH pem file to use for SSH connections '
              'to the specified Hive machine'))
    parser.add_option("--hive_init", action="store_true",
        dest="hive_init", default=False,
        help=('If True, this script will execute ka_hive_init.q on the '
              'hive_masternode before checking for data.  This is useful '
              'for making sure the metadata on the hive cluster is up to '
              'date, e.g. if data you want to import was create by an '
              'unknown on-demand cluster.'))

    options, args = parser.parse_args()
    if not options.config:
        g_logger.fatal("Please specify the config file")
        print >> sys.stderr, USAGE
        sys.exit(-1)

    return options, args


def partition_available(s3bucket, partition_location):
    """Check if the data partition is available"""
    time_delta = datetime.timedelta(seconds=60)
    path_prefix = partition_location[len('s3://ka-mapreduce/'):]
    if path_prefix[-1] != '/':
        path_prefix += '/'
    now = datetime.datetime.now()
    s3keys = s3bucket.list(prefix=path_prefix)
    empty = True
    for key in s3keys:
        key_modified = datetime.datetime.strptime(key.last_modified,
             "%Y-%m-%dT%H:%M:%S.%fZ")
        if (now - key_modified) < time_delta:
            # Data is still generating
            return False
        empty = False
    if empty:
        # Data is not available yet
        return False
    return True


def wait_for_data(wait_for_config, options):
    """Wait for data before kicking off hive jobs"""
    # Step 1 - read meta data.
    hive_mysql_connector.configure(options.hive_masternode,
        options.ssh_keyfile)

    if options.hive_init:
        hive_mysql_connector.run_hive_init()
    # Step 2 - wait for all the data partitions are available
    boto_util.initialize_creds_from_file()
    s3conn = boto.connect_s3()
    s3bucket = s3conn.get_bucket('ka-mapreduce')
    max_wait = datetime.timedelta(hours=options.max_wait)
    start = datetime.datetime.now()
    for d in wait_for_config:
        table = d['table_name']
        table_location = hive_mysql_connector.get_table_location(table)
        for p in d['partitions']:
            partition_location = table_location + '/' + p
            #TODO(yunfang): abstract the following to wait_for_partition
            #               for boto_util
            while True:
                if partition_available(s3bucket, partition_location):
                    g_logger.info("%s is available" % (partition_location))
                    break
                if (datetime.datetime.now() - start) > max_wait:
                    # Wait for a long time already. Can't wait any more
                    g_logger.fatal("Wait for too long. "
                                   "Data is still not available."
                                   "Exiting...")
                    sys.exit(1)
                # Wait for a minute to check again
                g_logger.info("Waiting for %s to be available... " % (
                              partition_location))
                time.sleep(60)


def run_hive_jobs(jobname, steps):
    """Run hive steps."""
    jobflow = emr.create_hive_cluster(jobname, {})
    for step in steps:
        emr.add_hive_step(jobflow, {},
            hive_script=step["hive_script"],
            script_args=step["hive_args"])
    status = emr.wait_for_completion(jobflow)
    listing = emr.list_steps(jobflow)
    failures = ["FAILED", "CANCELLED", "TERMINATED"]
    if any(s in listing for s in failures):
        subject = "Reporting jobflow FAILED: %s" % jobname
        notify.send_email(subject, listing)
        notify.send_hipchat(subject)
    else:
        subject = "Reporting jobflow SUCCEEDED: %s" % jobname
        notify.send_email(subject, listing)
    if status != "COMPLETED":
        g_logger.fatal("Hive jobs failed")
        g_logger.fatal(emr.list_steps(jobflow))
        sys.exit(1)


def run_report_importer(hive_masternode, steps):
    """Import hive results to mongo"""
    for step in steps:
        if ('hive_table' not in step) or ('mongo_collection' not in step):
            continue

        options = ''
        if step.get('drop', False):
            options += ' --drop'
        if step.get('hive_init', False):
            options += ' --hive_init'
        #TODO(benkomalo): Make the report_importer callable
        command = ('python /home/analytics/analytics/src/report_importer.py'
                   ' %s %s %s report %s %s') % (
                   options, hive_masternode, step['hive_table'],
                   step['mongo_collection'], step['importer_args'])
        g_logger.info("Running command: \n%s" % (command))
        proc = subprocess.Popen(command.split(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print proc.communicate()  # returns a tuple of (stdoutdata, stderrdata)


def main():
    options, params = parse_command_line_args()

    with open(options.config) as f:
        config_str = f.read()
    for param in params:
        name, val = param.split('=')
        g_logger.info("Replace %s with %s" % (name, val))
        config_str = config_str.replace(name, val)
    config = json.loads(config_str)

    g_logger.info("Step 1: Wait for data.")
    wait_for_data(config['wait_for'], options)

    g_logger.info("Step 2: Run hive jobs and wait for completion.")
    run_hive_jobs(config['name'], config['steps'])

    g_logger.info("Step 3: Load data from hive to mongo with report importer.")
    run_report_importer(options.hive_masternode, config['steps'])

    g_logger.info("Report generation finished.")


if __name__ == '__main__':
    main()
