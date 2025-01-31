import boto3
import logging

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    # Retrieve active EC2 instances (running and stopped)
    active_instances = ec2_client.describe_instances(Filters=[
        {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
    ])
    
    active_volumes = set()
    for reservation in active_instances['Reservations']:
        for instance in reservation['Instances']:
            for block_device in instance.get('BlockDeviceMappings', []):
                active_volumes.add(block_device['Ebs']['VolumeId'])
    
    # Fetch all snapshots owned by the account
    snapshots = ec2_client.describe_snapshots(OwnerIds=[account_id])['Snapshots']
    
    stale_snapshots = []
    for snapshot in snapshots:
        if 'VolumeId' in snapshot and snapshot['VolumeId'] not in active_volumes:
            stale_snapshots.append(snapshot['SnapshotId'])
    
    # Delete stale snapshots
    for snapshot_id in stale_snapshots:
        try:
            ec2_client.delete_snapshot(SnapshotId=snapshot_id)
            logging.info(f"Deleted stale snapshot: {snapshot_id}")
        except Exception as e:
            logging.error(f"Error deleting snapshot {snapshot_id}: {e}")
    
    return {
        'statusCode': 200,
        'body': f"Deleted {len(stale_snapshots)} stale snapshots"
    }
